# -*- coding: utf-8
""" Here is where all the good stuff happens """

import time
import re
import uuid
import socket
import datetime
import bcrypt
from peewee import SQL
from pyotp import TOTP
from flask import Flask, render_template, session, redirect, url_for, abort, g
from flask import request, jsonify
from flask_login import LoginManager, login_required, current_user, login_user
from flask_webpack import Webpack
from wheezy.html.utils import escape_html
from werkzeug.contrib.atom import AtomFeed

import config
from .forms import RegistrationForm, LoginForm, LogOutForm
from .forms import CreateSubForm, EditUserForm
from .forms import CreateSubTextPost, CreateSubLinkPost
from .forms import CreateUserMessageForm, PostComment, EditModForm
from .forms import DeletePost, CreateUserBadgeForm, DummyForm
from .forms import UseBTCdonationForm, BanDomainForm
from .forms import CreateMulti, EditMulti
from .forms import UseInviteCodeForm
from .views import do, api, subs
from .views.api import oauth
from . import misc, forms, caching
from .socketio import socketio
from . import database as db
from .misc import SiteAnon, getDefaultSubs, allowedNames, get_errors, engine
from .models import db as pdb
from .models import Sub, SubPost, User, SubMetadata, UserMetadata, SubPostComment
from .models import SiteLog, SubLog

# /!\ FOR DEBUGGING ONLY /!\
# from werkzeug.contrib.profiler import ProfilerMiddleware

app = Flask(__name__)
webpack = Webpack()
app.jinja_env.cache = {}

# app.wsgi_app = ProfilerMiddleware(app.wsgi_app)
app.config.from_object('config')
app.config['SUB_PREFIX'] = app.config.get('SUB_PREFIX', '/s')

app.register_blueprint(do)
app.register_blueprint(api)
app.register_blueprint(subs, url_prefix=app.config['SUB_PREFIX'])

app.config['WEBPACK_MANIFEST_PATH'] = 'manifest.json'
if app.config['TESTING']:
    import logging
    logging.basicConfig(level=logging.DEBUG)


webpack.init_app(app)
oauth.init_app(app)
socketio.init_app(app, message_queue=app.config['SOCKETIO_REDIS_URL'])
caching.cache.init_app(app)

login_manager = LoginManager(app)
login_manager.anonymous_user = SiteAnon

engine.global_vars.update({'current_user': current_user, 'request': request, 'config': config, 'conf': app.config,
                           'url_for': url_for, 'asset_url_for': webpack.asset_url_for, 'func': misc,
                           'form': forms, 'hostname': socket.gethostname(), 'datetime': datetime,
                           'e': escape_html})


@app.teardown_request
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'dbmod'):
        g.db.commit()

    if hasattr(g, 'db'):
        g.db.close()

    if not pdb.is_closed():
        pdb.close()


@app.before_request
def do_magic_stuff():
    """ We save the appconfig here because it can change during runtime
    (for unit tests) and we can't import app from some modules """
    g.appconfig = app.config
    if 'usid' not in session:
        session['usid'] = 'us' + str(uuid.uuid4())


@login_manager.user_loader
def load_user(user_id):
    """ This is used by flask_login to reload an user from a previously stored
    unique identifier. Required for the 'remember me' functionality. """
    return misc.load_user(user_id)


@app.before_request
def before_request():
    """ Called before the request is processed. Used to time the request """
    g.start = time.time()


@app.after_request
def after_request(response):
    """ Called after the request is processed. Used to time the request """
    if not app.debug and not current_user.is_admin():
        return response  # We won't do this if we're in production mode
    diff = time.time() - g.start
    diff = int(diff * 1000)
    if app.debug:
        print("Exec time: %s ms" % str(diff))

    if not hasattr(g, 'qc'):
        g.qc = 0
    if not hasattr(g, 'pqc'):
        g.pqc = 0
    if response.response and isinstance(response.response, list):
        etime = str(diff).encode()

        response.response[0] = response.response[0] \
                                       .replace(b'__EXECUTION_TIME__', etime)
        response.response[0] = response.response[0] \
                                       .replace(b'__DB_QUERIES__',
                                                str(g.qc).encode() + b'/' + str(g.pqc).encode())
        response.headers["content-length"] = len(response.response[0])
    return response


@app.context_processor
def utility_processor():
    """ Here we set some useful stuff for templates """
    # TODO: Kill this huge mass of shit
    return {'loginform': LoginForm(), 'regform': RegistrationForm(),
            'logoutform': LogOutForm(), 'sendmsg': CreateUserMessageForm(),
            'csubform': CreateSubForm(), 'markdown': misc.our_markdown,
            'commentform': PostComment(), 'dummyform': DummyForm(),
            'delpostform': DeletePost(), 'hostname': socket.gethostname(),
            'config': app.config, 'form': forms, 'db': db, 'datetime': datetime,
            'func': misc, 'time': time, 'conf': app.config}


@app.route("/")
def index():
    """ The index page, shows /hot of current subscriptions """
    return home_hot(1)


@app.route("/hot", defaults={'page': 1})
@app.route("/hot/<int:page>")
def home_hot(page):
    """ /hot for subscriptions """
    posts = list(misc.getPostList(misc.postListQueryHome(), 'hot', page).dicts())
    return engine.get_template('index.html').render({'posts': posts, 'sort_type': 'home_hot', 'page': page,
                                                     'subOfTheDay': misc.getSubOfTheDay(),
                                                     'changeLog': misc.getChangelog(), 'ann': misc.getAnnouncement(),
                                                     'kw': {}})


@app.route("/new", defaults={'page': 1})
@app.route("/new/<int:page>")
def home_new(page):
    """ /new for subscriptions """
    posts = misc.getPostList(misc.postListQueryHome(), 'new', page).dicts()
    return engine.get_template('index.html').render({'posts': posts, 'sort_type': 'home_new', 'page': page,
                                                     'subOfTheDay': misc.getSubOfTheDay(),
                                                     'changeLog': misc.getChangelog(), 'ann': misc.getAnnouncement(),
                                                     'kw': {}})


@app.route("/top", defaults={'page': 1})
@app.route("/top/<int:page>")
def home_top(page):
    """ /top for subscriptions """
    posts = misc.getPostList(misc.postListQueryHome(), 'top', page).dicts()
    return engine.get_template('index.html').render({'posts': posts, 'sort_type': 'home_top', 'page': page,
                                                     'subOfTheDay': misc.getSubOfTheDay(),
                                                     'changeLog': misc.getChangelog(), 'ann': misc.getAnnouncement(),
                                                     'kw': {}})


@app.route("/all/new.rss")
def all_new_rss():
    """ RSS feed for /all/new """
    feed = AtomFeed('All new posts',
                    title_type='text',
                    generator=('Throat', 'https://phuks.co', 1),
                    feed_url=request.url,
                    url=request.url_root)
    posts = misc.getPostList(misc.postListQueryBase(), 'new', 1).dicts()
    
    return misc.populate_feed(feed, posts).get_response()


@app.route("/all/new", defaults={'page': 1})
@app.route("/all/new/<int:page>")
def all_new(page):
    """ The index page, all posts sorted as most recent posted first """
    posts = list(misc.getPostList(misc.postListQueryBase(), 'new', page).dicts())
    return engine.get_template('index.html').render({'posts': posts, 'sort_type': 'all_new', 'page': page,
                                                     'subOfTheDay': misc.getSubOfTheDay(),
                                                     'changeLog': misc.getChangelog(), 'ann': misc.getAnnouncement(),
                                                     'kw': {}})


@app.route("/all/new/more", defaults={'pid': None})
@app.route('/all/new/more/<int:pid>')
def all_new_more(pid=None):
    """ Returns more posts for /all/new (used for infinite scroll) """
    if not pid:
        abort(404)
    posts = misc.getPostList(misc.postListQueryBase().where(SubPost.pid < pid), 'new', 1).dicts()
    return engine.get_template('shared/post.html').render({'posts': posts, 'sub': False})


@app.route("/domain/<domain>", defaults={'page': 1})
@app.route("/domain/<domain>/<int:page>")
def all_domain_new(domain, page):
    """ The index page, all posts sorted as most recent posted first """
    domain = re.sub(r'[^A-Za-z0-9.\-_]+', '', domain)
    posts = misc.getPostList(misc.postListQueryBase(noAllFilter=True).where(SubPost.link % ('%://' + domain + '/%')),
                             'new', page).dicts()
    return engine.get_template('index.html').render({'posts': posts, 'sort_type': 'all_domain_new', 'page': page,
                                                     'subOfTheDay': misc.getSubOfTheDay(),
                                                     'changeLog': misc.getChangelog(), 'ann': misc.getAnnouncement(),
                                                     'kw': {'domain': domain}})


@app.route("/search/<term>", defaults={'page': 1})
@app.route("/search/<term>/<int:page>")
def search(page, term):
    """ The index page, with basic title search """
    term = re.sub(r'[^A-Za-z0-9.,\-_\'" ]+', '', term)
    posts = misc.getPostList(misc.postListQueryBase().where(SubPost.title ** ('%' + term + '%')),
                             'new', page).dicts()
    return engine.get_template('index.html').render({'posts': posts, 'sort_type': 'search', 'page': page,
                                                     'subOfTheDay': misc.getSubOfTheDay(),
                                                     'changeLog': misc.getChangelog(), 'ann': misc.getAnnouncement(),
                                                     'kw': {'term': term}})


@app.route("/all/top", defaults={'page': 1})
@app.route("/all/top/<int:page>")
def all_top(page):
    """ The index page, all posts sorted as most recent posted first """
    posts = misc.getPostList(misc.postListQueryBase(), 'top', page).dicts()
    return engine.get_template('index.html').render({'posts': posts, 'sort_type': 'all_top', 'page': page,
                                                     'subOfTheDay': misc.getSubOfTheDay(),
                                                     'changeLog': misc.getChangelog(), 'ann': misc.getAnnouncement(),
                                                     'kw': {}})


@app.route("/all", defaults={'page': 1})
@app.route("/all/hot", defaults={'page': 1})
@app.route("/all/hot/<int:page>")
def all_hot(page):
    """ The index page, all posts sorted as most recent posted first """
    posts = misc.getPostList(misc.postListQueryBase(), 'hot', page).dicts()

    return engine.get_template('index.html').render({'posts': posts, 'sort_type': 'all_hot', 'page': page,
                                                     'subOfTheDay': misc.getSubOfTheDay(),
                                                     'changeLog': misc.getChangelog(), 'ann': misc.getAnnouncement(),
                                                     'kw': {}})


# Note for future self: I rewrote until this part. You should do the rest.

@app.route("/uploads", defaults={'page': 1})
@app.route("/uploads/<int:page>")
@login_required
def view_user_uploads(page):
    """ View user uploads """
    c = db.query('SELECT * FROM `user_uploads` WHERE `uid`=%s Limit 30 OFFSET %s',
                 (current_user.uid, (page - 1) * 30))
    return render_template('uploads.html', page=page, uploads=c.fetchall())


@app.route("/subs", defaults={'page': 1, 'sort': 'name_asc'})
@app.route("/subs/<sort>", defaults={'page': 1})
@app.route("/subs/<int:page>", defaults={'sort': 'name_asc'})
@app.route("/subs/<int:page>/<sort>")
def view_subs(page, sort):
    """ Here we can view available subs """
    c = Sub.select(Sub.sid, Sub.name, Sub.title, Sub.nsfw, SubMetadata.value.alias('creation'), Sub.subscribers, Sub.posts)
    c = c.join(SubMetadata, on=((SubMetadata.sid == Sub.sid) & (SubMetadata.key == 'creation'))).switch(Sub)

    # sorts...
    if sort == 'name_desc':
        c = c.order_by(Sub.name.desc())
    elif sort == 'name_asc':
        c = c.order_by(Sub.name.asc())
    elif sort == 'posts_desc':
        c = c.order_by(Sub.posts.desc())
    elif sort == 'posts_asc':
        c = c.order_by(Sub.posts.asc())
    elif sort == 'subs_desc':
        c = c.order_by(Sub.subscribers.desc())
    elif sort == 'subs_asc':
        c = c.order_by(Sub.subscribers.asc())
    else:
        return redirect(url_for('view_subs', page=page, sort='name_asc'))

    c = c.paginate(page, 50).dicts()
    cp_uri = '/subs/' + str(page)
    return render_template('subs.html', page=page, subs=c, nav='view_subs', sort=sort, cp_uri=cp_uri)


@app.route("/subs/search/<term>", defaults={'page': 1, 'sort': 'name_asc'})
@app.route("/subs/search/<term>/<sort>", defaults={'page': 1})
@app.route("/subs/search/<term>/<int:page>", defaults={'sort': 'name_asc'})
@app.route("/subs/search/<term>/<int:page>/<sort>")
def subs_search(page, term, sort):
    """ The subs index page, with basic title search """
    term = re.sub(r'[^A-Za-z0-9\-_]+', '', term)
    c = Sub.select(Sub.sid, Sub.name, Sub.title, Sub.nsfw, SubMetadata.value.alias('creation'), Sub.subscribers, Sub.posts)
    c = c.join(SubMetadata, on=((SubMetadata.sid == Sub.sid) & (SubMetadata.key == 'creation'))).switch(Sub)

    c = c.where(Sub.name.contains(term))

    # sorts...
    if sort == 'name_desc':
        c = c.order_by(Sub.name.desc())
    elif sort == 'name_asc':
        c = c.order_by(Sub.name.asc())
    elif sort == 'posts_desc':
        c = c.order_by(Sub.posts.desc())
    elif sort == 'posts_asc':
        c = c.order_by(Sub.posts.asc())
    elif sort == 'subs_desc':
        c = c.order_by(Sub.subscribers.desc())
    elif sort == 'subs_asc':
        c = c.order_by(Sub.subscribers.asc())
    else:
        return redirect(url_for('view_subs', page=page, sort='name_asc'))
    c = c.paginate(page, 50).dicts()
    cp_uri = '/subs/search/' + term + '/' + str(page)
    return render_template('subs.html', page=page, subs=c, nav='subs_search', term=term, sort=sort, cp_uri=cp_uri)


@app.route("/welcome")
def welcome():
    """ Welcome page for new users """
    return render_template('welcome.html')


@app.route("/canary")
def canary():
    """ Warrent canary """
    return render_template('canary.html')


@app.route("/donate")
def donate():
    """ Donation page """
    return render_template('donate.html')


@app.route("/userguide")
def userguide():
    """ User Guide page """
    return render_template('userguide.html')


@app.route("/mymultis")
def view_my_multis():
    """ Here we can view user multis """
    if current_user.is_authenticated:
        multis = db.get_user_multis(current_user.uid)
        formmultis = []
        for multi in multis:
            formmultis.append(EditMulti(multi=multi['mid'], name=multi['name'],
                                        subs=multi['subs']))
        return render_template('mymultis.html', multis=formmultis,
                               multilist=multis,
                               createmulti=CreateMulti())
    else:
        abort(403)


@app.route("/random")
def random_sub():
    """ Here we get a random sub """
    c = db.query('SELECT `name` FROM `sub` ORDER BY RAND() LIMIT 1')
    return redirect(url_for('sub.view_sub', sub=c.fetchone()['name']))


@app.route("/createsub")
def create_sub():
    """ Here we can view the create sub form """
    if current_user.is_authenticated:
        createsub = CreateSubForm()
        return render_template('createsub.html', csubform=createsub)
    else:
        abort(403)


@app.route("/m/<sublist>", defaults={'page': 1})
@app.route("/m/<sublist>/<int:page>")
def view_multisub_new(sublist, page=1):
    """ The multi index page, sorted as most recent posted first """
    names = sublist.split('+')
    sids = []
    ksubs = []
    for sb in names:
        sb = db.get_sub_from_name(sb)
        if sb:
            sids.append(sb['sid'])
            ksubs.append(sb)

    posts = misc.getPostList(misc.postListQueryBase().where(Sub.sid << sids),
                             'new', page).dicts()
    return render_template('indexmulti.html', page=page,
                           posts=posts, subs=ksubs, sublist=sublist,
                           sort_type='view_multisub_new', kw={'subs': sublist})


@app.route("/modmulti", defaults={'page': 1})
@app.route("/modmulti/<int:page>")
def view_modmulti_new(page):
    """ The multi page for subs the user mods, sorted as new first """
    if current_user.is_authenticated:
        sublist = db.get_user_modded_subs(current_user.uid)
        sids = []
        for i in sublist:
            sids.append(i['sid'])

        posts = misc.getPostList(misc.postListQueryBase().where(Sub.sid << sids),
                                 'new', page).dicts()
        return render_template('indexmulti.html', page=page,
                               sort_type='view_modmulti_new',
                               posts=posts, subs=sublist)
    else:
        abort(403)


@app.route("/multi/<sublist>", defaults={'page': 1})
@app.route("/multi/<sublist>/<int:page>")
def view_usermultisub_new(sublist, page):
    """ The multi index page, sorted as most recent posted first """
    multi = db.get_user_multi(sublist)
    sids = str(multi['sids']).split('+')
    names = str(multi['subs']).split('+')
    ksubs = []
    for sb in names:
        sb = db.get_sub_from_name(sb)
        if sb:
            ksubs.append(sb)
    posts = misc.getPostList(misc.postListQueryBase().where(Sub.sid << sids),
                             'new', page).dicts()

    return render_template('indexmulti.html', page=page, names=names,
                           posts=posts, subs=ksubs, sublist=sublist,
                           sort_type='view_usermultisub_new',
                           kw={'subs': sublist})


@app.route("/p/<pid>")
def view_post_inbox(pid):
    """ Gets route to post from just pid """
    post = db.get_post_from_pid(pid)
    if not post:
        abort(404)
    sub = db.get_sub_from_sid(post['sid'])
    return redirect(url_for('sub.view_post', sub=sub['name'], pid=post['pid']))


@app.route("/c/<cid>")
def view_comment_inbox(cid):
    """ Gets route to post from just cid """
    comm = db.get_comment_from_cid(cid)
    if not comm:
        abort(404)
    post = db.get_post_from_pid(comm['pid'])
    sub = db.get_sub_from_sid(post['sid'])
    return redirect(url_for('sub.view_post', sub=sub['name'], pid=comm['pid']))


@app.route("/u/<user>")
@login_required
def view_user(user):
    """ WIP: View user's profile, posts, comments, badges, etc """
    try:
        user = User.get(User.name == user)
    except User.DoesNotExist:
        abort(404)

    if user.status == 10:
        abort(404)

    owns = db.get_user_positions(user.uid, 'mod1')
    mods = db.get_user_positions(user.uid, 'mod2')
    badges = misc.getUserBadges(user.uid)
    pcount = SubPost.select().where(SubPost.uid == user.uid).count()
    ccount = SubPostComment.select().where(SubPostComment.uid == user.uid).count()
    habit = db.get_user_post_count_habit(user.uid)

    level, xp = misc.get_user_level(user.uid)

    if xp > 0:
        currlv = (level ** 2) * 10
        nextlv = ((level + 1) ** 2) * 10

        required_xp = nextlv - currlv
        progress = ((nextlv - xp) / required_xp) * 100
    else:
        progress = 0

    return render_template('user.html', user=user, badges=badges, habit=habit,
                           msgform=CreateUserMessageForm(), pcount=pcount,
                           ccount=ccount, owns=owns, mods=mods, level=level, progress=progress)


@app.route("/u/<user>/posts", defaults={'page': 1})
@app.route("/u/<user>/posts/<int:page>")
@login_required
def view_user_posts(user, page):
    """ WIP: View user's recent posts """
    user = db.get_user_from_name(user)
    if not user or user['status'] == 10:
        abort(404)

    if current_user.is_admin():
        posts = misc.getPostList(misc.postListQueryBase(adminDetail=True).where(User.uid == user['uid']),
                             'new', page).dicts()
    else:
        posts = misc.getPostList(misc.postListQueryBase(noAllFilter=True).where(User.uid == user['uid']),
                             'new', page).dicts()
    return render_template('userposts.html', page=page, sort_type='view_user_posts',
                           posts=posts, user=user)


@app.route("/u/<user>/savedposts", defaults={'page': 1})
@app.route("/u/<user>/savedposts/<int:page>")
@login_required
def view_user_savedposts(user, page):
    """ WIP: View user's saved posts """
    user = db.get_user_from_name(user)
    if not user or user['status'] == 10:
        abort(404)
    if current_user.uid == user['uid']:
        pids = db.get_all_user_saved(current_user.uid)
        posts = misc.getPostList(misc.postListQueryBase(noAllFilter=True).where(SubPost.pid << pids),
                                 'new', page).dicts()
        return render_template('userposts.html', page=page,
                               sort_type='view_user_savedposts',
                               posts=posts, user=user)
    else:
        abort(403)


@app.route("/u/<user>/comments", defaults={'page': 1})
@app.route("/u/<user>/comments/<int:page>")
@login_required
def view_user_comments(user, page):
    """ WIP: View user's recent comments """
    user = db.get_user_from_name(user)
    if not user or user['status'] == 10:
        abort(404)

    comments = misc.getUserComments(user['uid'], page)
    return render_template('usercomments.html', user=user, page=page,
                           comments=comments)


@app.route('/settings/subs')
@login_required
def edit_subs():
    return engine.get_template('user/topbar.html').render({})

@app.route("/settings")
@login_required
def edit_user():
    """ WIP: Edit user's profile, slogan, quote, etc """

    exlink = 'exlinks' in current_user.prefs
    styles = 'nostyles' in current_user.prefs
    nsfw = 'nsfw' in current_user.prefs
    exp = 'labrat' in current_user.prefs
    noscroll = 'noscroll' in current_user.prefs
    nochat = 'nochat' in current_user.prefs
    form = EditUserForm(external_links=exlink, show_nsfw=nsfw,
                        disable_sub_style=styles, experimental=exp,
                        noscroll=noscroll, nochat=nochat)
    return engine.get_template('user/settings.html').render({'edituserform': form})

    # return render_template('edituser.html', user=user, owns=owns,
    #                        badges=badges, adminbadges=adminbadges,
    #                        pcount=pcount, ccount=ccount, mods=mods,
    #                        edituserform=form)


@app.route("/messages")
@login_required
def inbox_sort():
    """ Go to inbox with the new message """
    if current_user.new_pm_count() == 0 \
       and current_user.new_mentions_count() > 0:
        return redirect(url_for('view_mentions'))
    if current_user.new_pm_count() == 0 \
       and current_user.new_postreply_count() > 0:
        return redirect(url_for('view_messages_postreplies'))
    if current_user.new_pm_count() == 0 \
       and current_user.new_comreply_count() > 0:
        return redirect(url_for('view_messages_comreplies'))
    if current_user.new_pm_count() == 0 \
       and current_user.new_modmail_count() > 0:
        return redirect(url_for('view_messages_modmail'))
    else:
        return redirect(url_for('view_messages'))


@app.route("/messages/inbox", defaults={'page': 1})
@app.route("/messages/inbox/<int:page>")
@login_required
def view_messages(page):
    """ View user's messages """
    msgs = misc.getMessagesIndex(page)
    return render_template('messages/messages.html', page=page,
                           messages=msgs, box_name="Inbox", boxID="1",
                           box_route='view_messages')


@app.route("/messages/mentions", defaults={'page': 1})
@app.route("/messages/mentions/<int:page>")
@login_required
def view_mentions(page):
    """ View user name mentions """
    db.uquery('UPDATE `message` SET `read`=%s WHERE `read` IS NULL AND '
              '`receivedby`=%s AND `mtype`=8', (datetime.datetime.utcnow(), current_user.uid))
    msgs = misc.getMentionsIndex(page)
    return render_template('messages/messages.html', page=page,
                           messages=msgs, box_name="Mentions", boxID="8",
                           box_route='view_mentions')


@app.route("/messages/sent", defaults={'page': 1})
@app.route("/messages/sent/<int:page>")
@login_required
def view_messages_sent(page):
    """ View user's messages sent """
    msgs = misc.getMessagesSent(page)
    return render_template('messages/sent.html', messages=msgs,
                           page=page, box_route='view_messages_sent')


@app.route("/messages/ignore")
@login_required
def view_ignores():
    """ View user's messages sent """
    igns = misc.get_ignores(current_user.uid)
    return render_template('messages/ignores.html', igns=igns)


@app.route("/messages/postreplies", defaults={'page': 1})
@app.route("/messages/postreplies/<int:page>")
@login_required
def view_messages_postreplies(page):
    """ WIP: View user's post replies """
    now = datetime.datetime.utcnow()
    db.uquery('UPDATE `message` SET `read`=%s WHERE `read` IS NULL AND '
              '`receivedby`=%s AND `mtype`=4', (now, current_user.uid))
    socketio.emit('notification',
                  {'count': current_user.notifications},
                  namespace='/snt',
                  room='user' + current_user.uid)
    msgs = misc.getMsgPostReplies(page)
    return render_template('messages/postreply.html', messages=msgs,
                           page=page, box_name="Replies", boxID="2",
                           box_route='view_messages_postreplies')


@app.route("/messages/commentreplies", defaults={'page': 1})
@app.route("/messages/commentreplies/<int:page>")
@login_required
def view_messages_comreplies(page):
    """ WIP: View user's comments replies """
    now = datetime.datetime.utcnow()
    db.uquery('UPDATE `message` SET `read`=%s WHERE `read` IS NULL AND '
              '`receivedby`=%s AND `mtype`=5', (now, current_user.uid))
    socketio.emit('notification',
                  {'count': current_user.notifications},
                  namespace='/snt',
                  room='user' + current_user.uid)
    msgs = misc.getMsgCommReplies(page)
    return render_template('messages/commreply.html',
                           page=page, box_name="Replies", messages=msgs,
                           box_route='view_messages_comreplies')


@app.route("/messages/modmail", defaults={'page': 1})
@app.route("/messages/modmail/<int:page>")
@login_required
def view_messages_modmail(page):
    """ WIP: View user's modmail """
    msgs = misc.getMessagesModmail(page)
    return render_template('messages/modmail.html', messages=msgs,
                           page=page, box_route='view_messages_modmail')


@app.route("/messages/saved", defaults={'page': 1})
@app.route("/messages/saved/<int:page>")
@login_required
def view_saved_messages(page):
    """ WIP: View user's saved messages """
    msgs = misc.getMessagesSaved(page)
    return render_template('messages/saved.html', messages=msgs,
                           page=page, box_route='view_saved_messages')


@app.route('/admin/auth', methods=['GET', 'POST'])
@login_required
def admin_auth():
    if not current_user.can_admin:
        abort(404)
    form = forms.TOTPForm()
    try:
        user_secret = UserMetadata.get((UserMetadata.uid == current_user.uid) & (UserMetadata.key == 'totp_secret'))
    except UserMetadata.DoesNotExist:
        return engine.get_template('admin/totp.html').render({'authform': form, 'error': 'No TOTP secret found.'})
    if form.validate_on_submit():
        totp = TOTP(user_secret.value)
        if totp.verify(form.totp.data):
            session['apriv'] = time.time()
            return redirect(url_for('admin_area'))
        else:
            return engine.get_template('admin/totp.html').render({'authform': form, 'error': 'Invalid or expired password.'})
    return engine.get_template('admin/totp.html').render({'authform': form, 'error': None})

@app.route('/admin/logout', methods=['POST'])
@login_required
def admin_logout():
    if not current_user.can_admin:
        abort(404)
    form = LogOutForm()
    if form.validate():
        del session['apriv']
    return redirect(url_for('admin_area'))

@app.route("/admin")
@login_required
def admin_area():
    """ WIP: View users. assign badges, etc """
    if not current_user.can_admin:
        abort(404)

    if not current_user.admin:
        return redirect(url_for('admin_auth'))

    users = db.query('SELECT COUNT(*) AS c FROM `user`').fetchone()['c']
    subs = db.query('SELECT COUNT(*) AS c FROM `sub`').fetchone()['c']
    posts = db.query('SELECT COUNT(*) AS c FROM `sub_post`') \
              .fetchone()['c']
    comms = db.query('SELECT COUNT(*) AS c FROM `sub_post_comment`') \
              .fetchone()['c']
    ups = db.query('SELECT COUNT(*) AS c FROM `sub_post_vote` WHERE '
                   '`positive`=1').fetchone()['c']
    ups += db.query('SELECT COUNT(*) AS c FROM `sub_post_comment_vote` '
                    'WHERE `positive`=1').fetchone()['c']
    downs = db.query('SELECT COUNT(*) AS c FROM `sub_post_vote` WHERE '
                     '`positive`=0').fetchone()['c']
    downs += db.query('SELECT COUNT(*) AS c FROM `sub_post_comment_vote` '
                      'WHERE `positive`=0').fetchone()['c']
    badges = db.query('SELECT * FROM `user_badge`').fetchall()
    btc = db.get_site_metadata('usebtc')
    if btc:
        x = db.get_site_metadata('btcmsg')['value']
        y = db.get_site_metadata('btcaddr')['value']
        btc = UseBTCdonationForm(message=x, btcaddress=y)
    else:
        btc = UseBTCdonationForm()
    invite = db.get_site_metadata('useinvitecode')
    if invite and invite['value'] == '1':
        a = db.get_site_metadata('invitecode')['value']
        invite = UseInviteCodeForm(invitecode=a)
    else:
        invite = UseInviteCodeForm()
    ep = db.query('SELECT * FROM `site_metadata` WHERE `key`=%s', ('enable_posting',)).fetchone()
    if ep:
        ep = ep['value']
    else:
        db.create_site_metadata('enable_posting', 'True')
        ep = 'True'
    return render_template('admin/admin.html', badges=badges, subs=subs,
                           posts=posts, ups=ups, downs=downs, users=users,
                           createuserbadgeform=CreateUserBadgeForm(),
                           comms=comms, usebtcdonationform=btc,
                           useinvitecodeform=invite, enable_posting=ep)


@app.route("/admin/users", defaults={'page': 1})
@app.route("/admin/users/<int:page>")
@login_required
def admin_users(page):
    """ WIP: View users. """
    if not current_user.is_admin():
        abort(404)
    users = db.query('SELECT * FROM `user` ORDER BY `joindate` DESC '
                        'LIMIT 50 OFFSET %s', (((page - 1) * 50),)).fetchall()
    return render_template('admin/users.html', users=users, page=page,
                            admin_route='admin_users')



@app.route("/admin/admins")
@login_required
def view_admins():
    """ WIP: View admins. """
    if current_user.is_admin():
        uids = db.query('SELECT * FROM `user_metadata` WHERE `key`=%s',
                        ('admin', )).fetchall()
        users = []
        for u in uids:
            user = db.get_user_from_uid(u['uid'])
            users.append(user)
        return render_template('admin/users.html', users=users,
                               admin_route='view_admins')
    else:
        abort(404)


@app.route("/admin/usersearch/<term>")
@login_required
def admin_users_search(term):
    """ WIP: Search users. """
    if current_user.is_admin():
        term = re.sub(r'[^A-Za-z0-9.\-_]+', '', term)
        users = db.query('SELECT * FROM `user` WHERE `name` LIKE %s'
                         'ORDER BY `name` ASC', ('%' + term + '%',)).fetchall()
        return render_template('admin/users.html', users=users, term=term,
                               admin_route='admin_users_search')
    else:
        abort(404)


@app.route("/admin/subs", defaults={'page': 1})
@app.route("/admin/subs/<int:page>")
@login_required
def admin_subs(page):
    """ WIP: View subs. Assign new owners """
    if current_user.is_admin():
        subs = db.query('SELECT * FROM `sub` '
                        'LIMIT 50 OFFSET %s', (((page - 1) * 50),)).fetchall()
        return render_template('admin/subs.html', subs=subs, page=page,
                               admin_route='admin_subs',
                               editmodform=EditModForm())
    else:
        abort(404)


@app.route("/admin/subsearch/<term>")
@login_required
def admin_subs_search(term):
    """ WIP: Search for a sub. """
    if current_user.is_admin():
        term = re.sub(r'[^A-Za-z0-9.\-_]+', '', term)
        subs = db.query('SELECT * FROM `sub` WHERE `name` LIKE %s'
                        'ORDER BY `name` ASC', ('%' + term + '%',))
        return render_template('admin/subs.html', subs=subs, term=term,
                               admin_route='admin_subs_search',
                               editmodform=EditModForm())
    else:
        abort(404)


@app.route("/admin/posts/all/", defaults={'page': 1})
@app.route("/admin/posts/all/<int:page>")
@login_required
def admin_posts(page):
    """ WIP: View posts. """
    if current_user.is_admin():
        posts = misc.getPostList(misc.postListQueryBase(adminDetail=True), 'new', page).paginate(page, 50).dicts()
        return render_template('admin/posts.html', page=page,
                               admin_route='admin_posts', posts=posts)
    else:
        abort(404)


@app.route("/admin/postvoting/<term>", defaults={'page': 1})
@app.route("/admin/postvoting/<term>/<int:page>")
@login_required
def admin_post_voting(page, term):
    """ WIP: View post voting habits """
    if current_user.is_admin():
        user = db.get_user_from_name(term)
        if user:
            msg = []
            votes = db.query('SELECT * FROM `sub_post_vote` WHERE `uid`=%s '
                             'ORDER BY `xid` DESC LIMIT 50 OFFSET %s',
                             (user['uid'], ((page - 1) * 50))).fetchall()
            # pids = []
            # for p in votes:
            #     pids.append(p['pid'])
            # posts = misc.getPostList(misc.postListQueryBase().where(SubPost.pid << pids),
            #                          'new', page).dicts()
        else:
            votes = []
            msg = 'user not found'
        return render_template('admin/postvoting.html', page=page, msg=msg,
                               admin_route='admin_post_voting',
                               votes=votes, term=term)
    else:
        abort(404)


@app.route("/admin/commentvoting/<term>", defaults={'page': 1})
@app.route("/admin/commentvoting/<term>/<int:page>")
@login_required
def admin_comment_voting(page, term):
    """ WIP: View comment voting habits """
    if current_user.is_admin():
        user = db.get_user_from_name(term)
        if user:
            msg = []
            votes = db.query('SELECT * FROM `sub_post_comment_vote` WHERE `uid`=%s '
                             'ORDER BY `xid` DESC LIMIT 50 OFFSET %s',
                             (user['uid'], ((page - 1) * 50))).fetchall()
        else:
            votes = []
            msg = 'user not found'
        return render_template('admin/commentvoting.html', page=page, msg=msg,
                               admin_route='admin_comment_voting',
                               votes=votes, term=term)
    else:
        abort(404)


@app.route("/admin/post/search/<term>")
@login_required
def admin_post_search(term):
    """ WIP: Post search result. """
    if current_user.is_admin():
        term = re.sub(r'[^A-Za-z0-9.\-_]+', '', term)
        post = db.get_post_from_pid(term)
        user = db.get_user_from_uid(post['uid'])
        sub = db.get_sub_from_sid(post['sid'])
        comms = db.query('SELECT * FROM `sub_post_comment` WHERE `pid`=%s',
                         (post['pid'],)).fetchall()
        votes = db.query('SELECT * FROM `sub_post_vote` WHERE `pid`=%s',
                         (post['pid'],)).fetchall()
        upcount = db.query('SELECT COUNT(*) AS c FROM `sub_post_vote` WHERE '
                           '`pid`=%s AND `positive`=1', (post['pid'], )) \
                    .fetchone()['c']
        downcount = db.query('SELECT COUNT(*) AS c FROM `sub_post_vote` WHERE '
                             '`pid`=%s AND `positive`=0', (post['pid'], )) \
                      .fetchone()['c']

        pcount = db.query('SELECT COUNT(*) AS c FROM `sub_post` WHERE '
                          '`uid`=%s', (user['uid'],)).fetchone()['c']
        ccount = db.query('SELECT COUNT(*) AS c FROM `sub_post_comment` WHERE '
                          '`uid`=%s', (user['uid'],)).fetchone()['c']

        return render_template('admin/post.html', sub=sub, post=post,
                               votes=votes, ccount=ccount, pcount=pcount,
                               upcount=upcount, downcount=downcount,
                               comms=comms, user=user)
    else:
        abort(404)


@app.route("/admin/domains", defaults={'page': 1})
@app.route("/admin/domains/<int:page>")
@login_required
def admin_domains(page):
    """ WIP: View Banned Domains """
    if current_user.is_admin():
        domains = db.get_site_metadata('banned_domain', _all=True)
        return render_template('admin/domains.html', domains=domains,
                               page=page, admin_route='admin_domains',
                               bandomainform=BanDomainForm())
    else:
        abort(404)


@app.route("/admin/uploads", defaults={'page': 1})
@app.route("/admin/uploads/<int:page>")
@login_required
def admin_user_uploads(page):
    """ View user uploads """
    c = db.query('SELECT * FROM `user_uploads` ORDER BY `pid` DESC Limit 30 OFFSET %s',
                 ((page - 1) * 30, )).fetchall()
    return render_template('admin/uploads.html', page=page, uploads=c)


@app.route("/sitelog", defaults={'page': 1})
@app.route("/sitelog/<int:page>")
@login_required
def view_sitelog(page):
    """ Here we can see a log of admin activity on the site """
    s1 = SiteLog.select(SiteLog.time, SiteLog.action, SiteLog.desc, SiteLog.link, SiteLog.uid, SQL("'' as `sub`"), SiteLog.target)
    s2 = SubLog.select(SubLog.time, SubLog.action, SubLog.desc, SubLog.link, SubLog.uid, Sub.name.alias('sud'), SubLog.target)
    s2 = s2.join(Sub).where(SubLog.admin == True)
    logs = (s1 | s2)
    # XXX: SQL() is a hack. Remove it when peewee updates (ref: peewee #1854)
    logs = logs.order_by(SQL('`time` DESC')).paginate(page, 50)
    
    return engine.get_template('site/log.html').render({'logs': logs, 'page': page})


@app.route("/register", methods=['GET', 'POST'])
def register():
    """ Endpoint for the registration form """
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate():
        if not allowedNames.match(form.username.data):
            return render_template('register.html', error="Username has invalid characters.")
        # check if user or email are in use
        try:
            User.get(User.name == form.username.data)
            return render_template('register.html', error="Username is not available.")
        except User.DoesNotExist:
            pass

        if form.email.data:
            try:
                User.get(User.email == form.email.data)
                return render_template('register.html', error="E-mail address is already in use.")
            except User.DoesNotExist:
                pass

        if getattr(config, 'ENABLE_SECURITY_QUESTIONS', False):
            if form.securityanswer.data.lower() != session['sa'].lower():
                return render_template('register.html', error="Incorrect answer for security question.")

        # TODO: Rewrite invite code code
        y = db.get_site_metadata('useinvitecode')
        y = y['value'] if y else False
        if y == '1':
            z = db.get_site_metadata('invitecode')['value']
            if z != form.invitecode.data:
                return render_template('register.html', error="Invalid invite code.")

        password = bcrypt.hashpw(form.password.data.encode('utf-8'), bcrypt.gensalt())

        user = User.create(uid=str(uuid.uuid4()), name=form.username.data, crypto=1, password=password,
                           email=form.email.data, joindate=datetime.datetime.utcnow())
        # defaults
        defaults = getDefaultSubs()
        for d in defaults:
            db.create_subscription(user.uid, d['sid'], 1)
        g.db.commit()
        theuser = misc.load_user(user.uid)
        login_user(theuser, remember=True)
        return redirect(url_for('welcome'))

    return render_template('register.html', error=get_errors(form))


@app.route("/login", methods=['GET', 'POST'])
def login():
    """ Endpoint for the login form """
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = User.get(User.name == form.username.data)
        except User.DoesNotExist:
            return engine.get_template('user/login.html').render({'error': "Invalid username or password.", 'loginform': form})

        if user.status == 10:
            return engine.get_template('user/login.html').render({'error': "Invalid username or password.", 'loginform': form})

        if user.crypto == 1:  # bcrypt
            thash = bcrypt.hashpw(form.password.data.encode('utf-8'),
                                  user.password.encode('utf-8'))
            if thash == user.password.encode('utf-8'):
                theuser = misc.load_user(user.uid)
                login_user(theuser, remember=form.remember.data)
                return form.redirect('index')
            else:
                return engine.get_template('user/login.html').render({'error': "Invalid username or password.", 'loginform': form})
        else:  # Unknown hash
            return engine.get_template('user/login.html').render({'error': "Something went really really wrong here.", 'loginform': form})
    return engine.get_template('user/login.html').render({'error': '', 'loginform': form})


@app.route("/submit/<ptype>", defaults={'sub': ''})
@app.route("/submit/<ptype>/<sub>")
@login_required
def submit(ptype, sub):
    if ptype not in ['link', 'text', 'poll']:
        abort(404)

    if ptype == 'poll' and not current_user.is_admin:
        abort(403)  # TODO: Remove restriction.

    txtpostform = CreateSubTextPost()
    txtpostform.ptype.data = ptype
    txtpostform.sub.data = sub
    if request.args.get('title'):
        txtpostform.title.data = request.args.get('title')
    if request.args.get('url'):
        txtpostform.link.data = request.args.get('url')
    if sub:
        try:
            dsub = Sub.get(Sub.name == sub)
            return render_template('createpost.html', txtpostform=txtpostform, sub=dsub)
        except Sub.DoesNotExist:
            abort(404)
    else:
        return render_template('createpost.html', txtpostform=txtpostform)


@app.route('/chat')
@login_required
def chat():
    return engine.get_template('chat.html').render({'subOfTheDay': misc.getSubOfTheDay(), 'changeLog': misc.getChangelog()})


@app.route("/recover")
def password_recovery():
    """ Endpoint for the registration form """
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return engine.get_template('user/password_recovery.html').render({'lpform': forms.PasswordRecoveryForm()})


@app.route('/reset/<uid>/<key>')
def password_reset(uid, key):
    """ The page that actually resets the password """
    try:
        user = User.get(User.uid == uid)
    except User.DoesNotExist:
        abort(404)

    try:
        key = UserMetadata.get((UserMetadata.uid == user.uid) & (UserMetadata.key == 'recovery-key'))
        keyExp = UserMetadata.get((UserMetadata.uid == user.uid) & (UserMetadata.key == 'recovery-key-time'))
        expiration = float(keyExp.value)
        if (time.time() - expiration) > 86400:  # 1 day
            # Key is old. remove it and proceed
            key.delete_instance()
            keyExp.delete_instance()
            abort(404)
    except UserMetadata.DoesNotExist:
        abort(404)

    if current_user.is_authenticated:
        key.delete_instance()
        keyExp.delete_instance()
        return redirect(url_for('index'))

    form = forms.PasswordResetForm(key=key.value, user=user.uid)
    return engine.get_template('user/password_reset.html').render({'lpform': form})


@app.route("/api")
def view_api():
    """ View API help page """
    return render_template('api.html')


@app.route("/tos")
def tos():
    """ Shows the site's TOS. """
    return render_template('tos.html')


@app.route("/privacy")
def privacy():
    """ Shows the site's privacy policy. """
    return render_template('privacy.html')


@app.route("/assets")
def assets():
    """ Shows the site's assets. """
    return render_template('assets.html')


@app.errorhandler(401)
def unauthorized(error):
    """ 401 Unauthorized """
    return redirect(url_for('login'))


@app.errorhandler(403)
def forbidden_error(error):
    """ 403 Forbidden """
    return render_template('errors/403.html'), 403


@app.errorhandler(404)
def not_found(error):
    """ 404 Not found error """
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    """ 500 Internal server error """
    return render_template('errors/500.html'), 500
