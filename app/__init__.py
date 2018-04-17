# -*- coding: utf-8
""" Here is where all the good stuff happens """

import time
import re
import uuid
import socket
import datetime
import bcrypt
from flask import Flask, render_template, session, redirect, url_for, abort, g
from flask import Markup, request, jsonify
from flask_login import LoginManager, login_required, current_user, login_user
from flask_webpack import Webpack
from feedgen.feed import FeedGenerator

from .forms import RegistrationForm, LoginForm, LogOutForm
from .forms import CreateSubForm, EditUserForm
from .forms import CreateSubTextPost, CreateSubLinkPost
from .forms import CreateUserMessageForm, PostComment, EditModForm
from .forms import DeletePost, CreateUserBadgeForm, DummyForm
from .forms import UseBTCdonationForm, BanDomainForm
from .forms import CreateMulti, EditMulti
from .forms import UseInviteCodeForm, LiveChat
from .views import do, api, sub
from .views.api import oauth
from . import misc, forms, caching
from .socketio import socketio
from . import database as db
from .misc import SiteAnon, getSuscriberCount, getDefaultSubs, allowedNames, get_errors, engine
from .models import db as pdb
from .models import Sub, SubPost, User

# /!\ EXPERIMENTAL /!\
import config
from wheezy.html.utils import escape_html

# from werkzeug.contrib.profiler import ProfilerMiddleware

app = Flask(__name__)
webpack = Webpack()
app.jinja_env.cache = {}

# app.wsgi_app = ProfilerMiddleware(app.wsgi_app)
app.config.from_object('config')
app.config['SUB_PREFIX'] = app.config.get('SUB_PREFIX', '/s')

app.register_blueprint(do)
app.register_blueprint(api)
app.register_blueprint(sub, url_prefix=app.config['SUB_PREFIX'])

app.config['WEBPACK_MANIFEST_PATH'] = 'manifest.json'
if app.config['TESTING']:
    import logging
    logging.basicConfig(level=logging.WARNING)


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


@app.template_filter('rnentity')
def rnentity(text):
    """ hacky fixes for escaping new lines on templates """
    return Markup(text.replace('\r\n', '&#10;').replace('\n', '&#10;'))


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
            'getSuscriberCount': getSuscriberCount, 'func': misc, 'time': time,
            'conf': app.config}


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
                                                     'subOfTheDay': misc.getSubOfTheDay(), 'posts': posts,
                                                     'changeLog': misc.getChangelog(), 'ann': misc.getAnnouncement(),
                                                     'kw': {}})


@app.route("/new", defaults={'page': 1})
@app.route("/new/<int:page>")
def home_new(page):
    """ /new for subscriptions """
    posts = misc.getPostList(misc.postListQueryHome(), 'new', page).dicts()
    return engine.get_template('index.html').render({'posts': posts, 'sort_type': 'home_new', 'page': page,
                                                     'subOfTheDay': misc.getSubOfTheDay(), 'posts': posts,
                                                     'changeLog': misc.getChangelog(), 'ann': misc.getAnnouncement(),
                                                     'kw': {}})


@app.route("/top", defaults={'page': 1})
@app.route("/top/<int:page>")
def home_top(page):
    """ /top for subscriptions """
    posts = misc.getPostList(misc.postListQueryHome(), 'top', page).dicts()
    return engine.get_template('index.html').render({'posts': posts, 'sort_type': 'home_top', 'page': page,
                                                     'subOfTheDay': misc.getSubOfTheDay(), 'posts': posts,
                                                     'changeLog': misc.getChangelog(), 'ann': misc.getAnnouncement(),
                                                     'kw': {}})


@app.route("/all/new.rss")
def all_new_rss():
    """ RSS feed for /all/new """
    fg = FeedGenerator()
    fg.title("/all/new")
    fg.subtitle("All new posts feed")
    fg.link(href=url_for('all_new', _external=True))
    fg.generator("Phuks")
    posts = misc.getPostList(misc.postListQueryBase(), 'new', 1).dicts()
    for post in posts:
        fe = fg.add_entry()
        url = url_for('sub.view_post', sub=post['sub'],
                      pid=post['pid'],
                      _external=True)
        fe.id(url)
        fe.link({'href': url, 'rel': 'self'})
        fe.title(post['title'])

    return fg.rss_str(pretty=True)


@app.route("/all/new", defaults={'page': 1})
@app.route("/all/new/<int:page>")
def all_new(page):
    """ The index page, all posts sorted as most recent posted first """
    posts = list(misc.getPostList(misc.postListQueryBase(), 'new', page).dicts())
    return engine.get_template('index.html').render({'posts': posts, 'sort_type': 'all_new', 'page': page,
                                                     'subOfTheDay': misc.getSubOfTheDay(), 'posts': posts,
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
    domain = re.sub('[^A-Za-z0-9.\-_]+', '', domain)
    posts = misc.getPostList(misc.postListQueryBase(noAllFilter=True).where(SubPost.link % ('%://' + domain + '/%')),
                             'new', 1).dicts()
    return engine.get_template('index.html').render({'posts': posts, 'sort_type': 'all_domain_new', 'page': page,
                                                     'subOfTheDay': misc.getSubOfTheDay(), 'posts': posts,
                                                     'changeLog': misc.getChangelog(), 'ann': misc.getAnnouncement(),
                                                     'kw': {'domain': domain}})


@app.route("/search/<term>", defaults={'page': 1})
@app.route("/search/<term>/<int:page>")
def search(page, term):
    """ The index page, with basic title search """
    term = re.sub('[^A-Za-z0-9.,\-_\'" ]+', '', term)
    posts = misc.getPostList(misc.postListQueryBase().where(SubPost.title ** ('%' + term + '%')),
                             'new', 1).dicts()
    return engine.get_template('index.html').render({'posts': posts, 'sort_type': 'search', 'page': page,
                                                     'subOfTheDay': misc.getSubOfTheDay(), 'posts': posts,
                                                     'changeLog': misc.getChangelog(), 'ann': misc.getAnnouncement(),
                                                     'kw': {'term': term}})


@app.route("/all/top", defaults={'page': 1})
@app.route("/all/top/<int:page>")
def all_top(page):
    """ The index page, all posts sorted as most recent posted first """
    posts = misc.getPostList(misc.postListQueryBase(), 'top', page).dicts()
    return engine.get_template('index.html').render({'posts': posts, 'sort_type': 'all_top', 'page': page,
                                                     'subOfTheDay': misc.getSubOfTheDay(), 'posts': posts,
                                                     'changeLog': misc.getChangelog(), 'ann': misc.getAnnouncement(),
                                                     'kw': {}})


@app.route("/all", defaults={'page': 1})
@app.route("/all/hot", defaults={'page': 1})
@app.route("/all/hot/<int:page>")
def all_hot(page):
    """ The index page, all posts sorted as most recent posted first """
    posts = misc.getPostList(misc.postListQueryBase(), 'hot', page).dicts()

    return engine.get_template('index.html').render({'posts': posts, 'sort_type': 'all_hot', 'page': page,
                                                     'subOfTheDay': misc.getSubOfTheDay(), 'posts': posts,
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


@app.route("/subs", defaults={'page': 1})
@app.route("/subs/<int:page>")
def view_subs(page):
    """ Here we can view available subs """
    c = Sub.select()
    c = c.order_by(Sub.name.asc()).paginate(page, 50).dicts()
    return render_template('subs.html', page=page, subs=c,
                           nav='view_subs')


@app.route("/subs/search/<term>", defaults={'page': 1})
@app.route("/subs/search/<term>/<int:page>")
def subs_search(page, term):
    """ The subs index page, with basic title search """
    term = re.sub('[^A-Za-z0-9\-_]+', '', term)
    c = Sub.select().where(Sub.name.contains(term))
    c = c.order_by(Sub.name.asc()).paginate(page, 50).dicts()
    return render_template('subs.html', page=page, subs=c,
                           nav='subs_search', term=term)


@app.route("/subs/subscribersasc", defaults={'page': 1})
@app.route("/subs/subscribersasc/<int:page>")
def subs_subscriber_sort_a(page):
    """ The subs index page, sorted by subscriber count asc """
    c = Sub.select()
    c = c.order_by(Sub.subscribers.asc()).paginate(page, 50).dicts()
    return render_template('subs.html', page=page, subs=c,
                           nav='subs_subscriber_sort_a')


@app.route("/subs/subscribersdesc", defaults={'page': 1})
@app.route("/subs/subscribersdesc/<int:page>")
def subs_subscriber_sort_d(page):
    """ The subs index page, sorted by subscriber count desc """
    c = Sub.select()
    c = c.order_by(Sub.subscribers.desc()).paginate(page, 50).dicts()
    return render_template('subs.html', page=page, subs=c,
                           nav='subs_subscriber_sort_d')


@app.route("/subs/postsasc", defaults={'page': 1})
@app.route("/subs/postsasc/<int:page>")
def subs_posts_sort_a(page):
    """ The subs index page, sorted by post count asc """
    c = Sub.select()
    c = c.order_by(Sub.posts.asc()).paginate(page, 50).dicts()
    return render_template('subs.html', page=page, subs=c,
                           nav='subs_posts_sort_a')


@app.route("/subs/postsdesc", defaults={'page': 1})
@app.route("/subs/postsdesc/<int:page>")
def subs_posts_sort_d(page):
    """ The subs index page, sorted by post count desc """
    c = Sub.select()
    c = c.order_by(Sub.posts.desc()).paginate(page, 50).dicts()
    return render_template('subs.html', page=page, subs=c,
                           nav='subs_posts_sort_d')


@app.route("/welcome")
def welcome():
    """ Welcome page for new users """
    return render_template('welcome.html')


@app.route("/canary")
def canary():
    """ Warrent canary """
    return render_template('canary.html')


@app.route("/miner")
def miner():
    """ miner """
    return render_template('miner.html')


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


@app.route("/live", defaults={'page': 1})
@app.route("/live/<int:page>")
def view_live_sub(page):
    """ God knows what this does """
    sub = db.get_sub_from_name('live')
    if not sub:
        abort(404)

    posts = db.query('SELECT * FROM `sub_post` WHERE `sid`=%s '
                     'ORDER BY `posted` DESC LIMIT %s,20',
                     (sub['sid'], (page - 1) * 20, )).fetchall()
    chats = db.query('SELECT * FROM `live_chat` '
                     'ORDER BY `xid` DESC LIMIT %s',
                     (20, )).fetchall()
    mods = db.get_sub_metadata(sub['sid'], 'mod2', _all=True)
    createtxtpost = CreateSubTextPost(sub='live')
    createlinkpost = CreateSubLinkPost(sub='live')

    return render_template('sublive.html', sub=sub, page=page,
                           sort_type='view_live_sub',
                           posts=posts, mods=mods, chats=chats,
                           txtpostform=createtxtpost, livechat=LiveChat(),
                           lnkpostform=createlinkpost)


@app.route("/createsub")
def create_sub():
    """ Here we can view the create sub form """
    if current_user.is_authenticated:
        createsub = CreateSubForm()
        return render_template('createsub.html', csubform=createsub)
    else:
        abort(403)


@app.route("/m/<subs>", defaults={'page': 1})
@app.route("/m/<subs>/<int:page>")
def view_multisub_new(subs, page=1):
    """ The multi index page, sorted as most recent posted first """
    names = subs.split('+')
    sids = []
    ksubs = []
    for sb in names:
        sb = db.get_sub_from_name(sb)
        if sb:
            sids.append(sb['sid'])
            ksubs.append(sb)

    posts = db.query('SELECT * FROM `sub_post` WHERE `sid` IN %s '
                     'ORDER BY `posted` DESC LIMIT %s,25',
                     (sids, (page - 1) * 20, )).fetchall()

    return render_template('indexmulti.html', page=page,
                           posts=posts, subs=ksubs,
                           sort_type='view_multisub_new', kw={'subs': subs})


@app.route("/modmulti", defaults={'page': 1})
@app.route("/modmulti/<int:page>")
def view_modmulti_new(page):
    """ The multi page for subs the user mods, sorted as new first """
    if current_user.is_authenticated:
        subs = db.get_user_modded_subs(current_user.uid)
        sids = []
        for i in subs:
            sids.append(i['sid'])

        posts = misc.getPostList(misc.postListQueryBase().where(Sub.sid << sids),
                                 'new', page).dicts()
        return render_template('indexmulti.html', page=page,
                               sort_type='view_modmulti_new',
                               posts=posts, subs=subs)
    else:
        abort(403)


@app.route("/multi/<subs>", defaults={'page': 1})
@app.route("/multi/<subs>/<int:page>")
def view_usermultisub_new(subs, page):
    """ The multi index page, sorted as most recent posted first """
    multi = db.get_user_multi(subs)
    sids = str(multi['sids']).split('+')
    names = str(multi['subs']).split('+')

    posts = db.query('SELECT * FROM `sub_post` WHERE `sid` IN %s '
                     'ORDER BY `posted` DESC LIMIT %s,20',
                     (sids, (page - 1) * 20, ))

    return render_template('indexmulti.html', page=page, names=names,
                           posts=posts.fetchall(), subs=subs,
                           sort_type='view_usermultisub_new',
                           kw={'subs': subs})


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
    user = db.get_user_from_name(user)
    if not user:
        abort(404)

    owns = db.get_user_positions(user['uid'], 'mod1')
    mods = db.get_user_positions(user['uid'], 'mod2')
    badges = misc.getUserBadges(user['uid'])
    pcount = db.query('SELECT COUNT(*) AS c FROM `sub_post` WHERE `uid`=%s',
                      (user['uid'], )).fetchone()['c']
    ccount = db.query('SELECT COUNT(*) AS c FROM `sub_post_comment` WHERE '
                      '`uid`=%s', (user['uid'], )).fetchone()['c']
    habit = db.get_user_post_count_habit(user['uid'])
    return render_template('user.html', user=user, badges=badges, habit=habit,
                           msgform=CreateUserMessageForm(), pcount=pcount,
                           ccount=ccount, owns=owns, mods=mods)


@app.route("/u/<user>/posts", defaults={'page': 1})
@app.route("/u/<user>/posts/<int:page>")
@login_required
def view_user_posts(user, page):
    """ WIP: View user's recent posts """
    user = db.get_user_from_name(user)
    if not user or user['status'] == 10:
        abort(404)

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
    caching.cache.delete_memoized(db.user_mail_count, current_user.uid)
    socketio.emit('notification',
                  {'count': db.user_mail_count(current_user.uid)},
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
    caching.cache.delete_memoized(db.user_mail_count, current_user.uid)
    socketio.emit('notification',
                  {'count': db.user_mail_count(current_user.uid)},
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


@app.route("/admin")
@login_required
def admin_area():
    """ WIP: View users. assign badges, etc """
    if current_user.is_admin():
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
    else:
        abort(404)


@app.route("/admin/users", defaults={'page': 1})
@app.route("/admin/users/<int:page>")
@login_required
def admin_users(page):
    """ WIP: View users. """
    if current_user.is_admin():
        users = db.query('SELECT * FROM `user` ORDER BY `joindate` DESC '
                         'LIMIT 50 OFFSET %s', (((page - 1) * 50),)).fetchall()
        return render_template('admin/users.html', users=users, page=page,
                               admin_route='admin_users')
    else:
        abort(404)


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
        term = re.sub('[^A-Za-z0-9.\-_]+', '', term)
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
        term = re.sub('[^A-Za-z0-9.\-_]+', '', term)
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
        term = re.sub('[^A-Za-z0-9.\-_]+', '', term)
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


@app.route("/admin/mining")
@login_required
def admin_mining():
    """ WIP: View Mining Leaderboard """
    if current_user.is_admin():
        return render_template('admin/mining.html',
                               admin_route='admin_mining')
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
    logs = db.query('SELECT * FROM `site_log` ORDER BY `lid` DESC LIMIT 50 '
                    'OFFSET %s ', (((page - 1) * 50),))
    return render_template('sitelog.html', logs=logs.fetchall(), page=page)


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
        if db.get_user_from_name(form.username.data):
            return render_template('register.html', error="Username is not available.")
        x = db.query('SELECT `uid` FROM `user` WHERE `email`=%s',
                     (form.email.data,))
        if x.fetchone() and form.email.data != '':
            return render_template('register.html', error="E-mail address is already in use.")

        if getattr(config, 'ENABLE_SECURITY_QUESTIONS', False):
            if form.securityanswer.data.lower() != session['sa'].lower():
                return render_template('register.html', error="Incorrect answer for security question.")

        y = db.get_site_metadata('useinvitecode')
        y = y['value'] if y else False
        if y == '1':
            z = db.get_site_metadata('invitecode')['value']
            if z != form.invitecode.data:
                return render_template('register.html', error="Invalid invite code.")
        user = db.create_user(form.username.data, form.email.data,
                              form.password.data)
        # defaults
        defaults = getDefaultSubs()
        for d in defaults:
            db.create_subscription(user['uid'], d['sid'], 1)
        g.db.commit()
        theuser = misc.load_user(user['uid'])
        print(theuser)
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
        user = db.get_user_from_name(form.username.data)
        if not user or user['status'] == 10:
            return render_template("login.html", error="Invalid username or password.")

        if user['crypto'] == 1:  # bcrypt
            thash = bcrypt.hashpw(form.password.data.encode('utf-8'),
                                  user['password'].encode('utf-8'))
            if thash == user['password'].encode('utf-8'):
                theuser = misc.load_user(user['uid'])
                login_user(theuser, remember=form.remember.data)
                return form.redirect('index')
            else:
                return render_template("login.html", error="Invalid username or password")
        else:  # Unknown hash
            return render_template("login.html", error="Something is really borked. Please file a bug report.")
    return render_template("login.html", error=get_errors(form))


@app.route("/submit/<ptype>", defaults={'sub': ''})
@app.route("/submit/<ptype>/<sub>")
@login_required
def submit(ptype, sub):
    if ptype not in ['link', 'text']:
        abort(404)
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


@app.route("/recover")
def password_recovery():
    """ Endpoint for the registration form """
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('password_recovery.html')


@app.route('/reset/<uid>/<key>')
def password_reset(uid, key):
    """ The page that actually resets the password """
    user = db.get_user_from_uid(uid)
    if not user:
        abort(403)
    key = db.get_user_metadata(user['uid'], 'recovery-key')
    # keyExp = db.get_user_metadata(user['uid'], 'recovery-key-time')
    if not key:
        abort(404)
    if current_user.is_authenticated:
        db.uquery('DELETE FROM `user_metadata` WHERE `uid`=%s AND `key`=%s',
                  (user['uid'], 'recovery-key'))
        db.uquery('DELETE FROM `user_metadata` WHERE `uid`=%s AND `key`=%s',
                  (user['uid'], 'recovery-key-time'))
        return redirect(url_for('index'))

    form = forms.PasswordResetForm(key=key['value'], user=user['uid'])
    return render_template('password_reset.html', resetpw=form)


@app.route('/edit/<pid>', methods=['GET', 'POST'])
def edit_post(pid):
    pass


@app.route('/stick/<pid>', methods=['GET', 'POST'])
def stick_post(pid):
    pass


@app.route('/miner/stats')
def miner_stats():
    hg = misc.getCurrentHashrate()
    bg = misc.getCurrentUserStats(current_user.name) if current_user.is_authenticated else {}
    lg = misc.getMiningLeaderboardJson()
    return jsonify(**{**hg, **bg, **lg})


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
def Forbidden(error):
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
