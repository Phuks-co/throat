""" API endpoint.
Some rules we should follow:
 - Always return JSON
 - Always return a 'status' key ({"status": "ok/error"})
 - If status is "error", return an "errors" _list_
"""

from datetime import datetime, timedelta
from flask import Blueprint, jsonify, abort, request, render_template
from flask_login import login_required, current_user
from flask_oauthlib.provider import OAuth2Provider
from ..models import User, Sub, SubPost, Client, Grant, Token, db
from ..misc import getSubUsers, getSubCreation, getSuscriberCount
from ..misc import getSubPostCount, isNSFW

api = Blueprint('api', __name__)
oauth = OAuth2Provider()


# OAuth stuff
@oauth.clientgetter
def load_client(client_id):
    return Client.query.filter_by(client_id=client_id).first()


@oauth.grantgetter
def load_grant(client_id, code):
    return Grant.query.filter_by(client_id=client_id, code=code).first()


@oauth.grantsetter
def save_grant(client_id, code, req, *args, **kwargs):
    # decide the expires time yourself
    expires = datetime.utcnow() + timedelta(seconds=100)
    grant = Grant(
        client_id=client_id,
        code=code['code'],
        redirect_uri=req.redirect_uri,
        _scopes=' '.join(req.scopes),
        user_id=current_user.get_id(),
        expires=expires
    )
    print(grant)
    db.session.add(grant)
    db.session.commit()
    return grant


@oauth.tokengetter
def load_token(access_token=None, refresh_token=None):
    if access_token:
        return Token.query.filter_by(access_token=access_token).first()
    elif refresh_token:
        return Token.query.filter_by(refresh_token=refresh_token).first()


@oauth.tokensetter
def save_token(token, req, *args, **kwargs):
    toks = Token.query.filter_by(client_id=req.client.client_id,
                                 user_id=req.user.uid)
    # make sure that every client has only one token connected to a user
    for t in toks:
        db.session.delete(t)

    expires_in = token.get('expires_in')
    expires = datetime.utcnow() + timedelta(seconds=expires_in)

    tok = Token(
        access_token=token['access_token'],
        refresh_token=token['refresh_token'],
        token_type=token['token_type'],
        _scopes=token['scope'],
        expires=expires,
        client_id=req.client.client_id,
        user_id=req.user.uid,
    )
    db.session.add(tok)
    db.session.commit()
    return tok


@api.route('/oauth/authorize', methods=['GET', 'POST'])
@login_required
@oauth.authorize_handler
def authorize(*args, **kwargs):
    if request.method == 'GET':
        client_id = kwargs.get('client_id')
        client = Client.query.filter_by(client_id=client_id).first()
        kwargs['client'] = client
        kwargs['request'] = request
        # TODO: Make this handle more grants!
        return render_template('oauthorize.html', **kwargs)

    confirm = request.form.get('confirm', 'no')
    return confirm == 'yes'


@api.route('/api/me')
@oauth.require_oauth('email')
def me():
    user = request.oauth.user
    return jsonify(email=user.email, username=user.name)


@api.route('/oauth/token', methods=['GET', 'POST'])
@oauth.token_handler
def access_token():
    return None


# /api/v1
@api.route("/api/v1/status", methods=['GET'])
def status():
    """ status endpoint """
    data = {'status': 'active', 'version': '1.0'}
    resp = jsonify(data)
    resp.status_code = 200
    return resp


@api.route("/api/v1/u/<user>", methods=['GET'])
@login_required
def view_user(user):
    """ Get user info """
    user = User.query.filter_by(name=user).first()
    if not user:
        abort(404)
    else:
        data = {'name': user.name,
                'joindate': user.joindate,
                'status': user.status}
        resp = jsonify(data)
        resp.status_code = 200
        return resp


@api.route("/api/v1/s/<sub>", methods=['GET'])
def view_sub(sub):
    """ Get sub """
    sub = Sub.query.filter_by(name=sub).first()
    if not sub:
        abort(404)
    else:
        data = {'name': sub.name,
                'title': sub.title,
                'created': getSubCreation(sub),
                'posts': getSubPostCount(sub),
                'owner': getSubUsers(sub, 'mod1'),
                'subscribers': getSuscriberCount(sub),
                'status': sub.status,
                'nsfw': isNSFW(sub)
                }
        resp = jsonify(data)
        resp.status_code = 200
        return resp


@api.route("/api/v1/s/<sub>/<pid>", methods=['GET'])
def view_post(sub, pid):
    """ Get post """
    post = SubPost.query.filter_by(pid=pid).first()
    if not post or post.sub.name != sub:
        abort(404)
    else:
        data = {
            'id': post.pid,
            'title': post.title,
            'link': post.link,
            'content': post.content,
            'user': post.user.name,
            'posted': post.posted,
            'ptype': post.ptype,
            'votes': post.voteCount()
        }
        resp = jsonify(data)
        resp.status_code = 200
        return resp


@api.errorhandler(404)
def not_found(error):
    """ Handler for missing api functions """
    data = {'status': 'error', 'errors': ['not found']}
    resp = jsonify(data)
    resp.status_code = 404
    return resp
