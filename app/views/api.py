""" API endpoint.
Some rules we should follow:
 - Always return JSON
 - Always return a 'status' key ({"status": "ok/error"})
 - If status is "error", return an "errors" _list_
"""

from datetime import datetime, timedelta
from flask import Blueprint, jsonify, abort, request, render_template, g
from flask_login import login_required, current_user
from flask_oauthlib.provider import OAuth2Provider
# from ..models import User, Sub, SubPost, Client, Grant, Token, db
from ..misc import getSubUsers, getSubCreation, getSuscriberCount
from ..misc import getSubPostCount, isNSFW
from .. import database as db

api = Blueprint('api', __name__)
oauth = OAuth2Provider()


# OAuth stuff
@oauth.clientgetter
def load_client(client_id):
    """ Loads OAuth clients """
    return db.query('SELECT * FROM `client` WHERE `client_id`=%s',
                    (client_id,)).fetchone()


@oauth.grantgetter
def load_grant(client_id, code):
    """ Gets grants.. """
    return db.query('SELECT * FROM `grant` WHERE `client_id`=%s AND `code`=%s',
                    (client_id, code)).fetchone()


@oauth.grantsetter
def save_grant(client_id, code, req, *args, **kwargs):
    """ Creates grants """
    # decide the expires time yourself
    expires = datetime.utcnow() + timedelta(seconds=100)
    l = db.uquery('INSERT INTO `grant` (`client_id`, `code`, `redirect_uri`, '
                  '`_scopes`, `user_id`, `expires`) VALUES (%s, %s, %s, %s, %s'
                  ', %s)', (client_id, code['code'], req.redirect_uri,
                            ' '.join(req.scopes), current_user.uid, expires))

    g.db.commit()
    f = db.query('SELECT * FROM `grant` WHERE `id`=%s', (l.lastrowid, ))
    return f.fetchone()


@oauth.tokengetter
def load_token(access_token=None, refresh_token=None):
    """ Loads oauth token """
    if access_token:
        return db.query('SELECT * FROM `token` WHERE `access_token`=%s',
                        (access_token,))
    elif refresh_token:
        return db.query('SELECT * FROM `token` WHERE `refresh_token`=%s',
                        (refresh_token,))


@oauth.tokensetter
def save_token(token, req, *args, **kwargs):
    """ Creates oauth token """
    db.uquery('DELETE FROM `token` WHERE `client_id`=%s AND `user_id`=%s',
              (req.client.client_id, req.user.uid))

    expires_in = token.get('expires_in')
    expires = datetime.utcnow() + timedelta(seconds=expires_in)
    l = db.uquery('INSERT INTO `token` (`access_token`, `refresh_token`, '
                  '`token_type`, `_scopes`, `expires`, `client_id`, `user_id`'
                  ') VALUES (%s, %s, %s, %s, %s, %s, %s)',
                  (token['access_token'], token['refresh_token'],
                   token['token_type'], token['scope'], expires,
                   req.client.client_id, req.user.uid))
    g.db.commit()
    f = db.query('SELECT * FROM `token` WHERE `id`=%s', (l.lastrowid, ))
    return f.fetchone()


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
@oauth.require_oauth('email')
def me():
    """ Returns basic user info """
    user = request.oauth.user
    return jsonify(email=user.email, username=user.name, uid=user.uid)


@api.route('/oauth/token', methods=['GET', 'POST'])
@oauth.token_handler
def access_token():
    """ Does nothing. """
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
