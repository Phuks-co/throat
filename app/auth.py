import base64
import logging
import random
import string
import urllib.parse

import bcrypt
from datetime import datetime
import uuid

from email_validator import validate_email
from flask import session, url_for
from flask_login import login_user
from keycloak import KeycloakAdmin as KeycloakAdmin_
from keycloak import KeycloakOpenID
from keycloak.exceptions import KeycloakError
from peewee import fn

from .config import config
from .models import (
    User,
    UserMetadata,
    UserAuthSource,
    UserCrypto,
    UserStatus,
    Sub,
    SubSubscriber,
)

logger = logging.getLogger("throat_auth")


# Fix an unhandled error in python-keycloak.
# See github.com/marcospereirampj/python-keycloak, pull requests 92 and 99.
class KeycloakAdmin(KeycloakAdmin_):
    def refresh_token(self):
        refresh_token = self.token.get("refresh_token")
        try:
            self.token = self.keycloak_openid.refresh_token(refresh_token)
        except KeycloakError as e:
            if e.response_code == 400 and (
                b"Refresh token expired" in e.response_body
                or b"Token is not active" in e.response_body
                or b"Session is not active" in e.response_body
                or b"No refresh token" in e.response_body
            ):
                self.get_token()
            else:
                raise
        self.connection.add_param_headers(
            "Authorization", "Bearer " + self.token.get("access_token")
        )


class AuthError(Exception):
    """Error used to refuse changes to users with Keycloak accounts when a
    Keycloak server is not configured.
    """

    pass


# noinspection PyAttributeOutsideInit
class AuthProvider:
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.provider = app.config["THROAT_CONFIG"].auth.provider
        if self.provider == "KEYCLOAK":
            cfg = app.config["THROAT_CONFIG"].auth.keycloak
            self.keycloak_admin = KeycloakAdmin(
                server_url=cfg.server,
                realm_name=cfg.user_realm,
                user_realm_name=cfg.admin_realm,
                client_id=cfg.admin_client,
                client_secret_key=cfg.admin_secret,
                verify=True,
                auto_refresh_token=["get", "put", "post", "delete"],
            )

            self.keycloak_openid = KeycloakOpenID(
                server_url=cfg.server,
                client_id=cfg.auth_client,
                client_secret_key=cfg.auth_secret,
                realm_name=cfg.user_realm,
                verify=True,
            )

    def get_login_url(self, acr: str = "aal1"):
        session["state"] = "".join(
            [random.choice(string.ascii_letters + string.digits) for _ in range(16)]
        )
        session["_acr"] = acr
        endpoint = self.keycloak_openid.well_known()["authorization_endpoint"]
        params = {
            "client_id": self.keycloak_openid.client_id,
            "response_type": "code",
            "redirect_uri": url_for("auth.login_redirect", _external=True),
            "scope": "openid",
            "state": session["state"],
            "acr_values": acr,
        }
        # Maybe someday: loginHint (auto-complete username), prompt (re-login)

        return f"{endpoint}?{urllib.parse.urlencode(params)}"

    def introspect(self):
        return self.keycloak_openid.introspect(
            token=base64.b64encode(
                f"{self.keycloak_openid.client_id}:{self.keycloak_openid.client_secret_key}".encode()
            ).decode(),
            rpt=session["refresh_token"],
            token_type_hint="requesting_party_token",
        )

    def logout(self):
        session.pop("exp_time", None)
        session.pop("is_admin", None)
        refresh_token = session.pop("refresh_token", None)
        if refresh_token:
            auth_provider.keycloak_openid.logout(refresh_token)

    def get_user_by_email(self, email):
        try:
            return User.get(fn.Lower(User.email) == email.lower())
        except User.DoesNotExist:
            try:
                um = UserMetadata.get(
                    (UserMetadata.key == "pending_email")
                    & (fn.Lower(UserMetadata.value) == email.lower())
                )
                return User.get(User.uid == um.uid)
            except UserMetadata.DoesNotExist:
                pass
        if self.provider == "KEYCLOAK":
            users = self.keycloak_admin.get_users({"email": email})
            for userdict in users:
                try:
                    return User.get(User.name == userdict["username"])
                except User.DoesNotExist:
                    return None
        return None

    def create_user(
        self, name, password, email, status=UserStatus.OK, verified_email=False
    ):
        auth_source = getattr(UserAuthSource, self.provider)

        if self.provider == "LOCAL":
            uid = str(uuid.uuid4())
            crypto = UserCrypto.BCRYPT
            password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        else:
            uid = self.keycloak_admin.create_user(
                {
                    "email": email,
                    "username": name,
                    "enabled": True,
                    "emailVerified": verified_email,
                    "credentials": [{"value": password, "type": "password"}],
                }
            )
            password = ""
            crypto = UserCrypto.REMOTE
        user = User.create(
            uid=uid,
            name=name,
            crypto=crypto,
            password=password,
            status=status,
            email=email,
            joindate=datetime.utcnow(),
        )
        self.set_user_auth_source(user, auth_source)
        self._set_email_verified(user, verified_email)
        return user

    @staticmethod
    def get_user_auth_source(user):
        try:
            umd = UserMetadata.get(
                (UserMetadata.uid == user.uid) & (UserMetadata.key == "auth_source")
            )
            return UserAuthSource(int(umd.value))
        except UserMetadata.DoesNotExist:
            return UserAuthSource.LOCAL

    @staticmethod
    def set_user_auth_source(user, value):
        value = str(int(value))
        try:
            umd = UserMetadata.get(
                (UserMetadata.uid == user.uid) & (UserMetadata.key == "auth_source")
            )
            umd.value = value
            umd.save()
        except UserMetadata.DoesNotExist:
            UserMetadata.create(uid=user.uid, key="auth_source", value=value)

    @staticmethod
    def get_user_remote_uid(user):
        try:
            umd = UserMetadata.get(
                (UserMetadata.uid == user.uid) & (UserMetadata.key == "remote_uid")
            )
            return umd.value
        except UserMetadata.DoesNotExist:
            return user.uid

    @staticmethod
    def set_user_remote_uid(user, remote_uid):
        try:
            umd = UserMetadata.get(
                (UserMetadata.uid == user.uid) & (UserMetadata.key == "remote_uid")
            )
            umd.value = remote_uid
            umd.save()
        except UserMetadata.DoesNotExist:
            UserMetadata.create(uid=user.uid, key="remote_uid", value=remote_uid)
        pass

    def change_password(self, user, old_password, new_password):
        if self.validate_password(user, old_password):
            auth_source = self.get_user_auth_source(user)
            if self.provider == "LOCAL" and auth_source == UserAuthSource.LOCAL:
                user.crypto = UserCrypto.BCRYPT
                user.password = bcrypt.hashpw(
                    new_password.encode("utf-8"), bcrypt.gensalt()
                )
                user.save()
            elif self.provider == "KEYCLOAK" and auth_source == UserAuthSource.KEYCLOAK:
                self.keycloak_admin.update_user(
                    user_id=self.get_user_remote_uid(user),
                    payload={
                        "credentials": [{"value": new_password, "type": "password"}]
                    },
                )
            else:
                raise AuthError
            # Invalidate other existing login sessions.
            User.update(resets=User.resets + 1).where(User.uid == user.uid).execute()

            # XXX: Remove this import from here. temporally changed to avoid circular import
            from .misc import load_user

            theuser = load_user(user.uid)
            login_user(theuser, remember=session.get("remember_me", False))

    def reset_password(self, user, new_password):
        auth_source = self.get_user_auth_source(user)
        if self.provider == "LOCAL":
            if auth_source == UserAuthSource.LOCAL:
                user.crypto = UserCrypto.BCRYPT
                user.password = bcrypt.hashpw(
                    new_password.encode("utf-8"), bcrypt.gensalt()
                )
            else:
                raise AuthError
        elif self.provider == "KEYCLOAK":
            if auth_source == UserAuthSource.LOCAL:
                kuid = self.keycloak_admin.create_user(
                    {
                        "email": user.email,
                        "username": user.name,
                        "enabled": True,
                        "emailVerified": self.is_email_verified(user),
                        "credentials": [{"value": new_password, "type": "password"}],
                    }
                )
                self.set_user_remote_uid(user, kuid)
                self.set_user_auth_source(user, UserAuthSource.KEYCLOAK)
                user.crypto = UserCrypto.REMOTE
                user.password = ""
            elif auth_source == UserAuthSource.KEYCLOAK:
                self.keycloak_admin.update_user(
                    user_id=self.get_user_remote_uid(user),
                    payload={
                        "credentials": [{"value": new_password, "type": "password"}]
                    },
                )
            else:
                raise AuthError
        user.save()
        User.update(resets=User.resets + 1).where(User.uid == user.uid).execute()

    def change_unconfirmed_user_email(self, user, new_email):
        """Use this to change the email before the user confirms it.  To
        change the email of a user with a confirmed email address, use
        the pending email change functions below.
        """
        user.email = new_email
        if self.provider == "KEYCLOAK":
            self.keycloak_admin.update_user(
                user_id=self.get_user_remote_uid(user),
                payload={"email": new_email, "emailVerified": False},
            )
        user.save()
        User.update(resets=User.resets + 1).where(User.uid == user.uid).execute()

    @staticmethod
    def get_pending_email(user):
        try:
            umd = UserMetadata.get(
                (UserMetadata.uid == user.uid) & (UserMetadata.key == "pending_email")
            )
            return umd.value
        except UserMetadata.DoesNotExist:
            return None

    @staticmethod
    def clear_pending_email(user):
        try:
            umd = UserMetadata.get(
                (UserMetadata.uid == user.uid) & (UserMetadata.key == "pending_email")
            )
            umd.delete_instance()
        except UserMetadata.DoesNotExist:
            return None

    @staticmethod
    def set_pending_email(user, email):
        try:
            umd = UserMetadata.get(
                (UserMetadata.uid == user.uid) & (UserMetadata.key == "pending_email")
            )
            umd.value = email
            umd.save()
        except UserMetadata.DoesNotExist:
            UserMetadata.create(uid=user.uid, key="pending_email", value=email)

    def confirm_pending_email(self, user, email):
        umd = None
        try:
            umd = UserMetadata.get(
                (UserMetadata.uid == user.uid) & (UserMetadata.key == "pending_email")
            )
        except UserMetadata.DoesNotExist:
            pass
        auth_source = self.get_user_auth_source(user)
        if self.provider == "LOCAL":
            if auth_source != UserAuthSource.LOCAL:
                raise AuthError
        elif self.provider == "KEYCLOAK":
            if auth_source == UserAuthSource.KEYCLOAK:
                self.keycloak_admin.update_user(
                    user_id=self.get_user_remote_uid(user),
                    payload={"email": email, "emailVerified": True},
                )
            else:
                raise AuthError

        if umd is not None:
            umd.delete_instance()
        user.email = email
        user.save()
        self._set_email_verified(user)

    @staticmethod
    def is_email_verified(user):
        try:
            umd = UserMetadata.get(
                (UserMetadata.uid == user.uid) & (UserMetadata.key == "email_verified")
            )
            return umd.value == "1"
        except UserMetadata.DoesNotExist:
            return False

    def set_email_verified(self, user, value=True):
        """Set both the UserMetadata and remote (if any) email_verified flags."""
        auth_source = self.get_user_auth_source(user)
        if self.provider == "LOCAL":
            if auth_source != UserAuthSource.LOCAL:
                raise AuthError
        elif self.provider == "KEYCLOAK":
            if auth_source == UserAuthSource.KEYCLOAK:
                self.keycloak_admin.update_user(
                    user_id=self.get_user_remote_uid(user),
                    payload={"email": user.email, "emailVerified": value},
                )
            else:
                raise AuthError
        self._set_email_verified(user, value)

    @staticmethod
    def _set_email_verified(user, value=True):
        """Set the UserMetadata email_verified flag."""
        value = "1" if value else "0"
        try:
            umd = UserMetadata.get(
                (UserMetadata.uid == user.uid) & (UserMetadata.key == "email_verified")
            )
            umd.value = value
            umd.save()
        except UserMetadata.DoesNotExist:
            UserMetadata.create(uid=user.uid, key="email_verified", value=value)

    def validate_password(self, user, password):
        if user.crypto == UserCrypto.BCRYPT:
            thash = bcrypt.hashpw(
                password.encode("utf-8"), user.password.encode("utf-8")
            )
            if thash == user.password.encode("utf-8"):
                if self.provider == "KEYCLOAK":
                    kuid = self.keycloak_admin.create_user(
                        {
                            "email": user.email,
                            "username": user.name,
                            "enabled": True,
                            "emailVerified": self.is_email_verified(user),
                            "credentials": [{"value": password, "type": "password"}],
                        }
                    )
                    self.set_user_remote_uid(user, kuid)
                    self.set_user_auth_source(user, UserAuthSource.KEYCLOAK)
                    user.crypto = UserCrypto.REMOTE
                    user.password = ""
                    user.save()
                return True
        elif (
            user.crypto == UserCrypto.REMOTE
            and self.get_user_auth_source(user) == UserAuthSource.KEYCLOAK
            and self.provider == "KEYCLOAK"
        ):
            try:
                # TODO do something with the token
                self.keycloak_openid.token(username=user.name, password=password)
                return True
            except KeycloakError:
                return False
        return False

    def change_user_status(self, user, new_status):
        if new_status == 10:
            payload = {"email": "", "emailVerified": False, "enabled": False}
            user.email = ""
            user.email_verified = False
            self.clear_pending_email(user)
        elif user.status != 10 and new_status == 5:
            if user.email and self.is_email_verified(user):
                domain = user.email.split("@")[1]
                logger.info("Banned %s; confirmed email on %s", user.name, domain)

            payload = {"enabled": False}
        elif user.status != 10 and new_status == 0:
            payload = {"enabled": True}
        else:
            raise RuntimeError("Invalid user status")

        if (
            new_status == 0
            and email_validation_is_required()
            and not self.is_email_verified(user)
        ):
            new_status = 1

        if user.crypto == UserCrypto.REMOTE:
            if (
                self.get_user_auth_source(user) == UserAuthSource.KEYCLOAK
                and self.provider == "KEYCLOAK"
            ):
                self.keycloak_admin.realm_name = config.auth.keycloak.user_realm
                self.keycloak_admin.update_user(
                    user_id=self.get_user_remote_uid(user), payload=payload
                )

        user.status = new_status
        user.save()
        User.update(resets=User.resets + 1).where(User.uid == user.uid).execute()

    def actually_delete_user(self, user):
        # Used by automatic tests to clean up test realm on server.
        # You should probably be using change_user_status.
        if user.crypto == UserCrypto.REMOTE:
            self.keycloak_admin.delete_user(self.get_user_remote_uid(user))


auth_provider = AuthProvider()


# Someday config.auth.require_valid_emails may move to site metadata.
def email_validation_is_required():
    return config.auth.require_valid_emails


def normalize_email(email):
    return validate_email(email, check_deliverability=False)["email"]


def create_user(username, password, email, invite_code, existing_user):
    status = UserStatus.PROBATION if email_validation_is_required() else UserStatus.OK
    if existing_user is not None:
        user = existing_user
        user.email = email
        auth_provider.set_email_verified(user, False)
        user.status = status
        user.joindate = datetime.utcnow()
        auth_provider.reset_password(user, password)
        user = User.get(User.uid == user.uid)
        try:
            umd = UserMetadata.get(
                (UserMetadata.uid == user.uid) & (UserMetadata.key == "invitecode")
            )
            umd.key = "previous_invitecode"
            umd.save()
        except UserMetadata.DoesNotExist:
            pass
    else:
        user = auth_provider.create_user(
            name=username,
            password=password,
            email=email,
            verified_email=False,
            status=status,
        )

    prefs = []
    if config.site.require_invite_code:
        prefs.append(dict(uid=user.uid, key="invitecode", value=invite_code))
    if config.site.nsfw.new_user_default.show:
        prefs.append(dict(uid=user.uid, key="nsfw", value="1"))
    if config.site.nsfw.new_user_default.blur:
        prefs.append(dict(uid=user.uid, key="nsfw_blur", value="1"))
    if prefs:
        UserMetadata.insert(prefs).execute()

    from .misc import getDefaultSubs

    defaults = getDefaultSubs()
    subs = [
        {"uid": user.uid, "sid": x["sid"], "status": 1, "time": datetime.utcnow()}
        for x in defaults
    ]
    SubSubscriber.insert_many(subs).execute()
    Sub.update(subscribers=Sub.subscribers + 1).where(
        Sub.sid << [x["sid"] for x in defaults]
    ).execute()
    return user
