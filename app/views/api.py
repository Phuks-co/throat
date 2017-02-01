""" API endpoint.
Some rules we should follow:
 - Always return JSON
 - Always return a 'status' key ({"status": "ok/error"})
 - If status is "error", return an "errors" _list_
"""

from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, render_template, g
from flask_login import login_required, current_user
from flask_oauthlib.provider import OAuth2Provider
from .. import misc, sorting
from .. import database as db

api = Blueprint('api', __name__)
oauth = OAuth2Provider()


class OAuthClient(object):
    """ Maps DB stuff to something that oauthlib can understand """
    def __init__(self, stuff):
        self.is_confidential = bool(stuff['is_confidential'])
        self._redirect_uris = stuff['_redirect_uris']
        self._default_scopes = stuff['_default_scopes']
        self.client_id = stuff['client_id']

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
        self.redirect_uri = stuff['redirect_uri']

    @property
    def user(self):
        """ Returns user info for this grant """
        return db.get_user_from_uid(self.tuff['user_id'])

    @property
    def scopes(self):
        """ Returns grant's scopes """
        if self.tuff['_scopes']:
            return self.tuff['_scopes'].split()
        return []

    def delete(self):
        """ Deletes this scope """
        db.uquery('DELETE FROM `grant` WHERE `id`=%s', (self.tuff['id'],))


class OAuthToken(object):
    """ Maps DB oauth tokens to oauthlib stuff """
    def __init__(self, stuff):
        self.tuff = stuff
        self.expires = stuff['expires']
        self.scopes = stuff['_scopes'].split()

    @property
    def user(self):
        """ Returns the user this token is attached to """
        return db.get_user_from_uid(self.tuff['user_id'])

    def delete(self):
        """ Deletes this token """
        db.uquery('DELETE FROM `token` WHERE `id`=%s', (self.tuff['id'],))


# OAuth stuff
@oauth.clientgetter
def load_client(client_id):
    """ Loads OAuth clients """
    qr = db.query('SELECT * FROM `client` WHERE `client_id`=%s',
                  (client_id,)).fetchone()
    return OAuthClient(qr) if qr else None


@oauth.grantgetter
def load_grant(client_id, code):
    """ Gets grants.. """
    qr = db.query('SELECT * FROM `grant` WHERE `client_id`=%s AND `code`=%s',
                  (client_id, code)).fetchone()
    return OAuthGrant(qr) if qr else None


@oauth.grantsetter
def save_grant(client_id, code, req, *args, **kwargs):
    """ Creates grants """
    # decide the expires time yourself
    expires = datetime.utcnow() + timedelta(seconds=100)
    qr = db.uquery('INSERT INTO `grant` (`client_id`, `code`, `redirect_uri`, '
                   '`_scopes`, `user_id`, `expires`) VALUES (%s, %s, %s, %s, '
                   '%s, %s)', (client_id, code['code'], req.redirect_uri,
                               ' '.join(req.scopes), current_user.uid,
                               expires))

    g.db.commit()
    f = db.query('SELECT * FROM `grant` WHERE `id`=%s', (qr.lastrowid, ))
    return f.fetchone()


@oauth.tokengetter
def load_token(access_token=None, refresh_token=None):
    """ Loads oauth token """
    if access_token:
        qr = db.query('SELECT * FROM `token` WHERE `access_token`=%s',
                      (access_token,)).fetchone()
    elif refresh_token:
        qr = db.query('SELECT * FROM `token` WHERE `refresh_token`=%s',
                      (refresh_token,)).fetchone()
    return OAuthToken(qr) if qr else None


@oauth.tokensetter
def save_token(token, req, *args, **kwargs):
    """ Creates oauth token """
    db.uquery('DELETE FROM `token` WHERE `client_id`=%s AND `user_id`=%s',
              (req.client.client_id, req.user['uid']))

    expires_in = token.get('expires_in')
    expires = datetime.utcnow() + timedelta(seconds=expires_in)
    qr = db.uquery('INSERT INTO `token` (`access_token`, `refresh_token`, '
                   '`token_type`, `_scopes`, `expires`, `client_id`, `user_id`'
                   ') VALUES (%s, %s, %s, %s, %s, %s, %s)',
                   (token['access_token'], token['refresh_token'],
                    token['token_type'], token['scope'], expires,
                    req.client.client_id, req.user['uid']))
    g.db.commit()
    f = db.query('SELECT * FROM `token` WHERE `id`=%s', (qr.lastrowid, ))
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
    return jsonify(email=user['email'], username=user['name'], uid=user['uid'])


@api.route('/oauth/token', methods=['GET', 'POST'])
@oauth.token_handler
def token_thingy():
    """ Does nothing. """
    return None


# /api/v1

@api.route('/api/v1/listPosts/<scope>/<sort>/<int:page>')
def get_posts(scope, sort, page):
    """ Returns the post listing for something """
    # TODO: NSFW checks
    subinfo = True
    if scope == 'home':
        subs = misc.getSubscriptions(current_user.get_id())
        if sort == 'new':
            posts = misc.getPostsFromSubs(subs, (page - 1), 'posted', 20)
        elif sort == 'top':
            posts = misc.getPostsFromSubs(subs, (page - 1), 'score', 20)
        elif sort == 'hot':
            posts = misc.getPostsFromSubs(subs, 200, 'score', False,
                                          'AND `posted` > NOW() - INTERVAL '
                                          '7 DAY')
            posts = sorting.HotSorting(posts).getPosts(page)
        else:
            return jsonify(status='error', error=['wut'])
    else:
        q = 'SELECT `pid`,`sid`,`uid`,`title`,`score`,`ptype`,`posted`,'\
            '`thumbnail`,`link`,`content` FROM `sub_post` WHERE `deleted`=0 '
        s = []
        if scope != 'all':
            subinfo = False
            sub = db.get_sub_from_name(scope)
            if not sub:
                return jsonify(status='error', error=['Sub not found'])
            q += 'AND `sid`=%s '
            s.append(sub['sid'])
        if sort == 'new':
            q += 'ORDER BY `posted` DESC LIMIT %s,20'
            s.append((page - 1) * 20)
        elif sort == 'top':
            q += 'ORDER BY `score` DESC LIMIT %s,20'
            s.append((page - 1) * 20)
        elif sort == 'hot':
            q += 'AND `posted` > NOW() - INTERVAL 7 DAY ORDER BY `score` DESC'\
                 ' LIMIT 200'
        else:
            return jsonify(status='error', error=['Bad sort'])

        c = db.query(q, s)
        if sort == 'hot':
            posts = sorting.HotSorting(c.fetchall()).getPosts(page)
        else:
            posts = c.fetchall()

    fposts = []
    for post in posts:
        post['content'] = False if post['content'] == '' else True
        post['comments'] = db.get_post_comment_count(post['pid'])
        post['username'] = db.get_user_from_uid(post['uid'])['name']
        post['posted'] = post['posted'].isoformat() + 'Z'  # silly hack
        if subinfo:
            post['sub'] = db.get_sub_from_sid(post['sid'], '`name`, `nsfw`')
        if current_user.is_authenticated:
            post['vote'] = misc.getVoteStatus(current_user.get_id(),
                                              post['pid'])
        else:
            post['vote'] = -1
        del post['sid']
        del post['uid']
        fposts.append(post)
    return jsonify(status='ok', posts=fposts)


@api.route('/api/v1/listUserPosts/<username>/<int:page>')
def get_userposts(username, page):
    """ Returns the users posts """
    user = db.get_user_from_name(username)
    if not user:
        return jsonify(status='error', error=['User not found'])
    c = db.query('SELECT `pid`,`sid`,`uid`,`title`,`score`,`ptype`,`posted`, '
                 '`thumbnail`,`link`,`content` FROM `sub_post` WHERE '
                 '`deleted`=0 AND `uid`=%s ORDER BY `posted` DESC LIMIT %s,20',
                 (user['uid'], (page - 1) * 20))
    posts = c.fetchall()

    fposts = []
    for post in posts:
        post['content'] = False if post['content'] == '' else True
        post['comments'] = db.get_post_comment_count(post['pid'])
        post['username'] = db.get_user_from_uid(post['uid'])['name']
        post['posted'] = post['posted'].isoformat() + 'Z'  # silly hack
        post['sub'] = db.get_sub_from_sid(post['sid'], '`name`, `nsfw`')
        if current_user.is_authenticated:
            post['vote'] = misc.getVoteStatus(current_user.get_id(),
                                              post['pid'])
        else:
            post['vote'] = -1
        del post['sid']
        del post['uid']
        fposts.append(post)
    return jsonify(status='ok', posts=fposts)


@api.route('/api/v1/getPostContent/<int:pid>')
def get_post_content(pid):
    """ Returns the raw post contents """
    c = db.get_post_from_pid(pid)
    if not c:
        return jsonify(status='error', error=['Post not found'])
    post = c['content']

    return jsonify(status='ok', content=post)


@api.route('/api/v1/getSubscriptions')
def get_subscriptions():
    """ Returns subscriptions for current user """
    subsc = misc.getSubscriptions(current_user.get_id())
    subs = []
    for sub in subsc:
        subs.append(db.get_sub_from_sid(sub['sid'])['name'])
    return jsonify(status='ok', subscriptions=subs)


@api.route('/api/v1/getSub/<name>')
def get_sub(name):
    """ Returns basic sub information """
    sub = db.get_sub_from_name(name, '`sid`,`name`,`sidebar`,`title`,`nsfw`')
    if not sub:
        return jsonify(status='error', error=['Sub not found'])
    x = db.get_sub_metadata(sub['sid'], 'sort')
    if not x or x['value'] == 'v':
        sub['sort'] = 'hot'
    elif x['value'] == 'v_two':
        sub['sort'] = 'new'
    elif x['value'] == 'v_three':
        sub['sort'] = 'top'
    sub['subscribercount'] = misc.getSuscriberCount(sub)
    sub['owner'] = misc.getSubUsers(sub, 'mod1')
    del sub['sid']
    return jsonify(status='ok', sub=sub)


@api.route('/api/v1/getPost/<int:pid>')
def get_post(pid):
    """ Returns a post """
    post = db.get_post_from_pid(pid)
    if not post:
        return jsonify(status='error', error=['Post not found'])
    if post['deleted'] == 0:
        post['user'] = db.get_user_from_uid(post['uid'])['name']
    post['sub'] = db.get_sub_from_sid(post['sid'])['name']
    del post['uid']
    del post['sid']
    return jsonify(status='ok', post=post)


@api.route('/api/v1/getUser/<username>')
def get_user(username):
    """ Returns user information """
    user = db.get_api_user_from_name(username)
    if not user:
        return jsonify(status='error', error=['User not found'])

    user['owns'] = db.get_user_positions(user['uid'], 'mod1')
    user['mods'] = db.get_user_positions(user['uid'], 'mod2')
    user['badges'] = db.get_user_badges(user['uid'])
    user['postcount'] = db.query('SELECT COUNT(*) AS c FROM `sub_post` WHERE '
                                 '`uid`=%s', (user['uid'], )).fetchone()['c']
    user['commentcount'] = db.query('SELECT COUNT(*) AS c FROM '
                                    '`sub_post_comment` WHERE  `uid`=%s',
                                    (user['uid'], )).fetchone()['c']
    user['level'] = misc.get_user_level(user['uid'])[0]
    user['xp'] = misc.get_user_level(user['uid'])[1]
    del user['uid']

    return jsonify(status='ok', user=user)


@api.route('/api/v1/getTopPosts/day')
def get_todays_top_posts():
    """ Returns the top 5 posts for the day """
    # TODO: NSFW checks
    posts = misc.getTodaysTopPosts()

    fposts = []
    for post in posts:
        post['posted'] = post['posted'].isoformat() + 'Z'  # silly hack
        post['sub'] = db.get_sub_from_sid(post['sid'], '`name`, `nsfw`')

        del post['sid']
        del post['uid']
        del post['thumbnail']
        del post['content']
        fposts.append(post)
    return jsonify(status='ok', posts=fposts)
