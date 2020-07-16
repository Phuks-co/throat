import bcrypt
from datetime import datetime
import uuid
from .config import config
from .models import User, UserMetadata, UserAuthSource, UserCrypto, SiteMetadata
import keycloak

class AuthError(Exception):
    pass


class AuthProvider:
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        cfg = app.config['THROAT_CONFIG']
        self.provider = cfg.auth.provider
        self.realm = cfg.auth.keycloak.realm
        if self.provider == 'KEYCLOAK':
            self.keycloak_admin = keycloak.KeycloakAdmin(
                server_url=cfg.auth.keycloak.server,
                realm_name="master",
		client_secret_key=cfg.auth.keycloak.secret,
		verify=True,
                auto_refresh_token=['get', 'put', 'post', 'delete'])

    def get_user_by_email(self, email):
        # This may raise an error if the Keycloak server is unavailable or
        # misconfigured.
        try:
            return User.get(User.email == email)
        except User.DoesNotExist:
            pass
        if self.provider == 'KEYCLOAK':
            try:
                users = self.keycloak_admin.get_users({"email": email}, self.realm)
            except keycloak.exceptions.KeycloakError as err:
                raise AuthError(str(err))
            for userdict in users:
                try:
                    return User.get(User.name == userdict['username'])
                except User.DoesNotExist:
                    return user
        return None


    def create_user(self, name, password, email):
        auth_source = getattr(UserAuthSource, self.provider)

        if self.provider == 'LOCAL':
            uid = str(uuid.uuid4())
            crypto = UserCrypto.BCRYPT
            password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        else:
            user = self.keycloak_admin.create_user({'email': email,
                                                    'username': name,
                                                    'enabled': True,
                                                    'credentials': [{'value': 'secret','type': 'password'}]},
                                                   realm_name = self.realm)
            uid = user['id']
            email = ''
            password = ''
            crypto = UserCrypto.REMOTE
        user = User.create(uid=uid, name=name, crypto=crypto, password=password,
                           email=email, joindate=datetime.utcnow())
        self.set_user_auth_source(user, auth_source)
        return user

    def set_user_auth_source(self, user, value):
        value = '1' if value else '0'
        try:
            umd = UserMetadata.get((UserMetadata.uid == user.uid) &
                                   (UserMetadata.key == "auth_source"))
            umd.value = value
            umd.save()
        except UserMetadata.DoesNotExist:
            UserMetadata.create(uid=user.uid, key="auth_source", value=value)




auth_provider = AuthProvider()


def registration_is_enabled():
    try:
        enable_registration = SiteMetadata.get(SiteMetadata.key == 'enable_registration')
        if enable_registration.value in ('False', '0'):
            return False
    except SiteMetadata.DoesNotExist:
        pass
    return True


