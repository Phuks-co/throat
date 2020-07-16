import bcrypt
from datetime import datetime
import uuid

from flask import current_app, render_template
from flask_babel import _
from keycloak import KeycloakAdmin, KeycloakOpenID
from keycloak.exceptions import KeycloakError

from .config import config
from .models import User, UserMetadata, UserAuthSource, UserCrypto, SiteMetadata

class AuthError(Exception):
    pass


class AuthProvider:
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.provider = app.config['THROAT_CONFIG'].auth.provider
        if self.provider == 'KEYCLOAK':
            cfg = app.config['THROAT_CONFIG'].auth.keycloak
            self.keycloak_admin = KeycloakAdmin(server_url=cfg.server,
                                                realm_name=cfg.user_realm,
                                                user_realm_name=cfg.admin_realm,
                                                client_id=cfg.admin_client,
		                                client_secret_key=cfg.admin_secret,
		                                verify=True,
                                                auto_refresh_token=['get', 'put', 'post', 'delete'])

            self.keycloak_openid = KeycloakOpenID(server_url=cfg.server,
                                                  client_id=cfg.auth_client,
                                                  client_secret_key=cfg.auth_secret,
                                                  realm_name=cfg.user_realm,
                                                  verify=True)


    def get_user_by_email(self, email):
        # TODO when there are pending change emails, check those too.
        try:
            return User.get(User.email == email)
        except User.DoesNotExist:
            try:
                um = UserMetadata.get((UserMetadata.key == 'pending_email') &
                                      (UserMetadata.value == email))
                return User.get(User.uid == uim.uid)
            except UserMetadata.DoesNotExist:
                pass
        if self.provider == 'KEYCLOAK':
            try:
                users = self.keycloak_admin.get_users({"email": email})
            except KeycloakError as err:
                raise AuthError(str(err))
            for userdict in users:
                try:
                    return User.get(User.name == userdict['username'])
                except User.DoesNotExist:
                    return None
        return None

    def create_user(self, name, password, email, verified_email=False):
        auth_source = getattr(UserAuthSource, self.provider)

        if self.provider == 'LOCAL':
            uid = str(uuid.uuid4())
            crypto = UserCrypto.BCRYPT
            password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        else:
            uid = self.keycloak_admin.create_user({'email': email,
                                                   'username': name,
                                                   'enabled': True,
                                                   'emailVerified': verified_email,
                                                   'credentials': [{'value': password,
                                                                    'type': 'password'}]})
            # email = ''  # Store emails in local db, or not?
            password = ''
            crypto = UserCrypto.REMOTE
        user = User.create(uid=uid, name=name, crypto=crypto, password=password,
                           email=email, joindate=datetime.utcnow())
        self.set_user_auth_source(user, auth_source)
        self.set_email_verified(user, verified_email)
        return user

    def get_user_auth_source(self, user):
        try:
            umd = UserMetadata.get((UserMetadata.uid == user.uid) &
                                   (UserMetadata.key == "auth_source"))
            return UserAuthSource(int(umd.value))
        except UserMetadata.DoesNotExist:
            return UserAuthSource.LOCAL

    def set_user_auth_source(self, user, value):
        value = str(int(value))
        try:
            umd = UserMetadata.get((UserMetadata.uid == user.uid) &
                                   (UserMetadata.key == "auth_source"))
            umd.value = value
            umd.save()
        except UserMetadata.DoesNotExist:
            UserMetadata.create(uid=user.uid, key="auth_source", value=value)

    def change_password(self, user, old_password, new_password):
        if not self.validate_password(user, old_password):
            return False
        if self.provider == 'LOCAL':
            user.crypto = UserCrypto.BCRYPT
            user.password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        elif self.provider == 'KEYCLOAK':
            if self.get_user_auth_source(user) == UserAuthSource.LOCAL:
                self.keycloak_admin.create_user({'id': user.uid,
                                                 'email': user.email,
                                                 'username': user.name,
                                                 'enabled': True,
                                                 'emailVerified': user.verified_email,
                                                 'credentials': [{'value': new_password,
                                                                  'type': 'password'}]})
                self.set_user_auth_source(user, UserAuthSource.KEYCLOAK)
                user.crypto = UserCrypto.REMOTE
                user.password = ''
            else:
                self.keycloak_admin.update_user(user_id=user.uid,
                                                payload={'credentials':
                                                         [{'value': new_password,
                                                           'type': 'password'}]})
        user.save()

    def get_pending_email(self, user):
        try:
            umd = UserMetadata.get((UserMetadata.uid == user.uid) &
                                   (UserMetadata.key == "pending_email"))
            return umd.value
        except UserMetadata.DoesNotExist:
            return None

    def clear_pending_email(self, user):
        try:
            umd = UserMetadata.get((UserMetadata.uid == user.uid) &
                                   (UserMetadata.key == "pending_email"))
            umd.delete_instance()
        except UserMetadata.DoesNotExist:
            return None

    def set_pending_email(self, user, email):
        try:
            umd = UserMetadata.get((UserMetadata.uid == user.uid) &
                                   (UserMetadata.key == "pending_email"))
            umd.value = email
            umd.save()
        except UserMetadata.DoesNotExist:
            UserMetadata.create(uid=user.uid, key="pending_email", value=email)

    def confirm_pending_email(self, user, email):
        try:
            umd = UserMetadata.get((UserMetadata.uid == user.uid) &
                                   (UserMetadata.key == "pending_email"))
            umd.delete_instance()
        except UserMetadata.DoesNotExist:
            pass
        if self.get_user_auth_source(user) == UserAuthSource.KEYCLOAK:
            self.keycloak_admin.update_user(user_id=user.uid,
                                            payload={'email': email})
        user.email = email
        self.set_email_verified(user)

    def set_email_verified(self, user, value=True):
        if self.get_user_auth_source(user) == UserAuthSource.KEYCLOAK:
            self.keycloak_admin.update_user(user_id=user.uid,
                                            payload={'emailVerified': value})
        value = '1' if value else '0'
        try:
            umd = UserMetadata.get((UserMetadata.uid == user.uid) &
                                   (UserMetadata.key == "email_verified"))
            umd.value = value
            umd.save()
        except UserMetadata.DoesNotExist:
            UserMetadata.create(uid=user.uid, key="email_verified", value=value)

    def validate_password(self, user, password):
        if user.crypto == UserCrypto.BCRYPT:
            thash = bcrypt.hashpw(password.encode('utf-8'), user.password.encode('utf-8'))
            return thash == user.password.encode('utf-8')
        elif (user.crypto == UserCrypto.REMOTE and
              self.get_user_auth_source(user) == UserAuthSource.KEYCLOAK and
              self.provider == 'KEYCLOAK'):
            try:
                # TODO do something with the token
                self.keycloak_openid.token(username=user.name,
                                           password=password)
                return True
            except KeycloakError as err:
                return False
        return False

    def change_user_status(self, user, new_status):
        if new_status == 10:
            payload = {'email': '',
                       'emailVerified': False,
                       'enabled': False}
            user.email = ''
            user.email_verified = False
        elif user.status != 10 and new_status == 5:
            payload = {'enabled': False}
        elif user.status != 10 and new_status == 0:
            payload = {'enabled': True}
        else:
            raise RuntimeError("Invalid user status")

        if user.crypto == UserCrypto.REMOTE:
            if (self.get_user_auth_source(user) == UserAuthSource.KEYCLOAK and
                    self.provider == 'KEYCLOAK'):
                self.keycloak_admin.update_user(user_id=user.uid, payload=payload)

        user.status = new_status
        user.save()

    def actually_delete_user(self, user):
        # Used by automatic tests to clean up test realm on server.
        # You should probably be using mark_user_deleted.
        if user.crypto == UserCrypto.REMOTE:
            self.keycloak_admin.delete_user(user.uid)


auth_provider = AuthProvider()


def registration_is_enabled():
    try:
        enable_registration = SiteMetadata.get(SiteMetadata.key == 'enable_registration')
        if enable_registration.value in ('False', '0'):
            return False
    except SiteMetadata.DoesNotExist:
        pass
    return True


# Someday config.auth.validate_emails may move to site metadata.
def email_validation_is_required():
    return config.auth.validate_emails


