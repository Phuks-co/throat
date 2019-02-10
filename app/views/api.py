""" API endpoint.
Some rules we should follow:
 - Always return JSON
 - Always return a 'status' key ({"status": "ok/error"})
 - If status is "error", return an "errors" _list_
"""

from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, render_template, g, current_app
from flask.sessions import SecureCookieSessionInterface
from flask_login import login_required, current_user
from flask_oauthlib.provider import OAuth2Provider
from .. import misc
from ..models import Sub, User, Grant, Token, Client

api = Blueprint('api', __name__)
oauth = OAuth2Provider()


class OAuthClient(object):
    """ Maps DB stuff to something that oauthlib can understand """
    def __init__(self, stuff):
        self.is_confidential = bool(stuff.is_confidential)
        self._redirect_uris = stuff._redirect_uris
        self._default_scopes = stuff._default_scopes
        self.client_id = stuff.client_id

    @property
    def client_type(self):
        """ Returns the client type """
        if self.is_confidential:
            return 'confidential'
        return 'public'

    @property
    def redirect_uris(self):
        """ Returns all the redirect uris """
        if self._redirect_uris:
            return self._redirect_uris.split()
        return []

    @property
    def default_redirect_uri(self):
        """ returns the default redirect uri """
        return self.redirect_uris[0]

    @property
    def default_scopes(self):
        """ Returns the default scopes for the client """
        if self._default_scopes:
            return self._default_scopes.split()
        return []


class OAuthGrant(object):
    """ Maps grants in DB to stuff oauthlib can use """
    def __init__(self, stuff):
        self.tuff = stuff
        self.redirect_uri = stuff.redirect_uri

    @property
    def user(self):
        """ Returns user info for this grant """
        return User.get(self.tuff.user_id)

    @property
    def scopes(self):
        """ Returns grant's scopes """
        if self.tuff['_scopes']:
            return self.tuff._scopes.split()
        return []

    def delete(self):
        """ Deletes this scope """
        Grant.delete().where(Grant.id == self.tuff.id).execute()


class OAuthToken(object):
    """ Maps DB oauth tokens to oauthlib stuff """
    def __init__(self, stuff):
        self.tuff = stuff
        self.expires = stuff.expires
        self.scopes = stuff._scopes.split()

    @property
    def user(self):
        """ Returns the user this token is attached to """
        return User.get(self.tuff.user_id)

    def delete(self):
        """ Deletes this token """
        Token.delete().where(Token.id == self.tuff.id).execute()


# OAuth stuff
@oauth.clientgetter
def load_client(client_id):
    """ Loads OAuth clients """
    try:
        qr = Client.get(Client.id == client_id)
        return OAuthClient(qr)
    except Client.DoesNotExist:
        return None


@oauth.grantgetter
def load_grant(client_id, code):
    """ Gets grants.. """
    try:
        qr = Grant.get((Grant.client_id == client_id) & (Grant.code == code))
        return OAuthClient(qr)
    except Grant.DoesNotExist:
        return None


@oauth.grantsetter
def save_grant(client_id, code, req, *args, **kwargs):
    """ Creates grants """
    # decide the expires time yourself
    expires = datetime.utcnow() + timedelta(seconds=100)
    qr = Grant.create(client_id=client_id, code=code, redirect_uri=req.redirect_uri,
                      _scopes=' '.join(req.scopes), user_id=current_user.uid, expires=expires)
    qr.save()
    return qr


@oauth.tokengetter
def load_token(access_token=None, refresh_token=None):
    """ Loads oauth token """
    try:
        if access_token:
            qr = Token.get(Token.access_token == access_token)
        elif refresh_token:
            qr = Token.get(Token.refresh_token == refresh_token)
        return OAuthToken(qr)
    except Token.DoesNotExist:
        return None


@oauth.tokensetter
def save_token(token, req, *args, **kwargs):
    """ Creates oauth token """
    Token.delete().where((Token.client_id == req.client.client_id) & (Token.user_id == req.user['uid'])).execute()

    expires_in = token.get('expires_in')
    expires = datetime.utcnow() + timedelta(seconds=expires_in)
    qr = Token.create(access_token=token['access_token'], refresh_token=token['refresh_token'], token_type=token['token_type'],
                      _scopes=token['scope'], expires=expires, client_id=req.client.client_id, user_id=req.user['uid'])
    qr.save()
    return qr


@api.route('/oauth/authorize', methods=['GET', 'POST'])
@login_required
@oauth.authorize_handler
def authorize(*args, **kwargs):
    """ The page that authorizes oauth stuff """
    if request.method == 'GET':
        client_id = kwargs.get('client_id')
        client = load_client(client_id)
        kwargs['client'] = client
        kwargs['request'] = request
        # TODO: Make this handle more grants!
        return render_template('oauthorize.html', **kwargs)

    confirm = request.form.get('confirm', 'no')
    return confirm == 'yes'


@api.route('/api/me')
@oauth.require_oauth('account_info')
def me():
    """ Returns basic user info """
    user = request.oauth.user
    return jsonify(email=user['email'], username=user['name'], uid=user['uid'])


@api.route('/api/getToken')
@oauth.require_oauth('interact')
def get_socket_session():
    """ Returns basic user info """
    user = request.oauth.user
    session_serializer = SecureCookieSessionInterface().get_signing_serializer(current_app)

    return jsonify(token=session_serializer.dumps({'uid': user['uid']}))


@api.route('/oauth/token', methods=['GET', 'POST'])
@oauth.token_handler
def token_thingy():
    """ Does nothing. """
    return None


# /api/v2

@api.route('/api/v2/getPostList/<target>/<sort>', defaults={'page': 1}, methods=['GET'])
@api.route('/api/v2/getPostList/<target>/<sort>/<int:page>', methods=['GET'])
def getPostList(target, sort, page):
    if sort not in ('hot', 'top', 'new'):
        return jsonify(status="error", error="Invalid sort")
    if page < 1:
        return jsonify(status="error", error="Invalid page number")

    if target == 'home':
        posts = misc.getPostList(misc.postListQueryHome(noDetail=True, nofilter=True), sort, page).dicts()
    elif target == 'all':
        posts = misc.getPostList(misc.postListQueryBase(noDetail=True, nofilter=True), sort, page).dicts()
    else:
        try:
            sub = Sub.get(Sub.name == target)
        except Sub.DoesNotExist:
            return jsonify(status="error", error="Target does not exist")
        posts = misc.getPostList(misc.postListQueryBase(noAllFilter=True, nofilter=True, noDetail=True).where(Sub.sid == sub.sid),
                                 sort, page).dicts()
                                 
    return jsonify(status='ok', posts=list(posts))
