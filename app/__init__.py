# -*- coding: utf-8
""" Here is where all the good stuff happens """

import json
import time
import re
import random
from wsgiref.handlers import format_date_time
import datetime
from urllib.parse import urlparse, urljoin

import bcrypt
import markdown
from flask import Flask, render_template, session, redirect, url_for, abort, g
from flask import make_response, request
from flask_assets import Environment, Bundle
from flask_login import LoginManager, login_required, current_user
from flask_sqlalchemy import get_debug_queries
from tld import get_tld
from werkzeug.contrib.atom import AtomFeed
from feedgen.feed import FeedGenerator

from .models import db, User, Sub, SubPost, Message, SubPostVote
from .models import UserBadge, UserMetadata
from .forms import RegistrationForm, LoginForm, LogOutForm
from .forms import CreateSubForm, EditSubForm, EditUserForm
from .forms import CreateSubTextPost, EditSubTextPostForm, CreateSubLinkPost
from .forms import CreateUserMessageForm, PostComment, EditModForm
from .forms import DummyForm, DeletePost, CreateUserBadgeForm
from .forms import EditSubLinkPostForm
from .views import do, api
from .misc import SiteUser, getVoteCount, hasVoted, getMetadata
from .misc import SiteAnon, hasMail, cache, hasSubscribed
from .sorting import VoteSorting, BasicSorting, HotSorting

app = Flask(__name__)
app.register_blueprint(do)
app.register_blueprint(api)
app.config.from_object('config')

db.init_app(app)
cache.init_app(app)

assets = Environment(app)
login_manager = LoginManager(app)
login_manager.anonymous_user = SiteAnon
origstatic = app.view_functions['static']


def cache_static(*args, **kwargs):
    """ We use this to make a far-expiry cache when we serve the assets
    directly (like we do in Heroku). This makes the browser just use the cached
    resources instead of checking if they changed and getting a 302
    response. """
    response = make_response(origstatic(*args, **kwargs))
    expires_time = time.mktime((datetime.datetime.now() +
                                datetime.timedelta(days=365)).timetuple())

    response.headers['Cache-Control'] = 'public, max-age=31536000'
    response.headers['Expires'] = format_date_time(expires_time)
    return response
app.view_functions['static'] = cache_static

# We use nested bundles here. One of them is for stuff that is already minified
# And the other is for stuff that we have to minify. This makes the
# bundle-making process a bit faster.
js = Bundle(
    Bundle('js/jquery.min.js',
           'js/magnific-popup.min.js',
           'js/CustomElements.min.js'),
    Bundle('js/time-elements.js',
           'js/konami.js',
           'js/site.js', filters='jsmin'),
    output='gen/site.js')
css = Bundle(
    Bundle('css/font-awesome.min.css', 'css/simplemde.min.css'),
    Bundle('css/magnific-popup.css', 'css/style.css',
           filters='cssmin,datauri'), output='gen/site.css')

assets.register('js_all', js)
assets.register('css_all', css)


def our_markdown(text):
    """ Here we create a custom markdown function where we load all the
    extensions we need. """
    return markdown.markdown(text,
                             extensions=['markdown.extensions.tables'])


@login_manager.user_loader
def load_user(user_id):
    """ This is used by flask_login to reload an user from a previously stored
    unique identifier. Required for the 'remember me' functionality. """
    user = User.query.filter_by(uid=user_id).first()
    if not user:
        return None
    else:
        return SiteUser(user)


@app.before_first_request
def initialize_database():
    """ This is executed before any request is processed. We use this to
    create all the tables and database shit we need. """
    db.create_all()


@app.before_request
def before_request():
    """ Called before the request is processed. Used to time the request """
    g.start = time.time()


@app.after_request
def after_request(response):
    """ Called after the request is processed. Used to time the request """
    if not app.debug:
        return  # We won't do this if we're in production mode
    diff = time.time() - g.start
    diff = int(diff * 1000)
    if app.debug:
        print("Exec time: %s ms" % str(diff))

    querytime = 0
    for q in get_debug_queries():
        querytime += q.duration * 1000
    querytime = str(int(querytime)).encode()
    if response.response and isinstance(response.response, list):
        etime = str(diff).encode()
        queries = str(len(get_debug_queries())).encode()

        response.response[0] = response.response[0] \
                                       .replace(b'__EXECUTION_TIME__', etime)
        response.response[0] = response.response[0] \
                                       .replace(b'__DB_QUERIES__', queries)
        response.response[0] = response.response[0] \
                                       .replace(b'__QUERY_TIME__', querytime)
        response.headers["content-length"] = len(response.response[0])
    return response


def checkSession():
    """ Helper function that checks if a session is valid. """
    if 'user' in session:
        # We also store and check the join date to prevent somebody stealing
        # a session of a different user after the user was perma-deleted
        # or if the database was emptied.
        user = User.query.filter_by(uid=session['user']).first()
        try:
            # This line is here because for some reason, when storing the
            # joindate in a session, the microsecond part is lost, and if we
            # don't do this, the next 'if' statement will always wipe all the
            # sessions.
            jd = user.joindate.replace(microsecond=0)
        except AttributeError:  # This is to migrate old session cookies.
            session.pop('user', None)  # Remove before going to production
            session.pop('joindate', None)
            return
        if (not user) or session['joindate'] != jd:
            # User does not exist, invalidate session
            session.pop('user', None)
            session.pop('joindate', None)


@app.context_processor
def utility_processor():
    """ Here we set some useful stuff for templates """
    return {'loginform': LoginForm(), 'regform': RegistrationForm(),
            'logoutform': LogOutForm(), 'sendmsg': CreateUserMessageForm(),
            'csubform': CreateSubForm(), 'markdown': our_markdown,
            'commentform': PostComment(), 'dummyform': DummyForm(),
            'getVoteCount': getVoteCount, 'hasVoted': hasVoted,
            'delpostform': DeletePost(), 'getMetadata': getMetadata,
            'txtpostform': CreateSubTextPost(), 'editsubform': EditSubForm(),
            'lnkpostform': CreateSubLinkPost()}


@app.route("/")
def index():
    """ The index page, currently sorts like /all/new """
    return all_hot(1)


@app.route("/new")
def index_new():
    """ The index page, currently sorts like /all/new """
    return all_new(1)


@app.route("/all/new.rss")
def all_new_rss():
    """ RSS feed for /all/new """
    fg = FeedGenerator()
    fg.title("/all/new")
    fg.subtitle("All new posts feed")
    fg.link(href=url_for('all_new', _external=True))
    fg.generator("Throat")
    posts = SubPost.query.order_by(SubPost.posted.desc())
    sorter = BasicSorting(posts)
    for post in sorter.getPosts():
        fe = fg.add_entry()
        url = url_for('view_post', sub=post.sub.name, pid=post.pid,
                      _external=True)
        fe.id(url)
        fe.link({'href': url, 'rel': 'self'})
        fe.title(post.title)

    return fg.rss_str(pretty=True)


@app.route("/all/new", defaults={'page': 1})
@app.route("/all/new/<int:page>")
def all_new(page):
    """ The index page, all posts sorted as most recent posted first """
    posts = SubPost.query.order_by(SubPost.posted.desc())
    sorter = BasicSorting(posts)
    return render_template('index.html', page=page, sort_type='all_new',
                           posts=sorter.getPosts(page))


@app.route("/domain/<domain>", defaults={'page': 1})
@app.route("/domain/<domain>/<int:page>")
def all_domain_new(page, domain):
    """ The index page, all posts sorted as most recent posted first """
    posts = SubPost.query.filter_by(ptype=1) \
                         .filter(SubPost.link.contains(domain))

    sorter = BasicSorting(posts)
    return render_template('index.html', page=page, sort_type='all_new',
                           posts=sorter.getPosts(page))


@app.route("/all/top", defaults={'page': 1})
@app.route("/all/top/<int:page>")
def all_top(page):
    """ The index page, all posts sorted as most recent posted first """
    posts = SubPost.query.order_by(SubPost.posted.desc())
    sorter = VoteSorting(posts)
    return render_template('index.html', page=page, sort_type='all_top',
                           posts=sorter.getPosts(page))


@app.route("/all/hot", defaults={'page': 1})
@app.route("/all/hot/<int:page>")
def all_hot(page):
    """ The index page, all posts sorted as most recent posted first """
    posts = SubPost.query.order_by(SubPost.posted.desc())
    sorter = HotSorting(posts)
    return render_template('index.html', page=page, sort_type='all_hot',
                           posts=sorter.getPosts(page))


@app.route("/subs")
def view_subs():
    """ Here we can view available subs """
    subs = Sub.query.order_by(Sub.name.desc()).all()
    return render_template('subs.html', subs=subs)


@app.route("/random")
def random_sub():
    """ Here we get a random sub """
    subcount = Sub.query.count()
    offset = random.randrange(0, subcount)
    sub = Sub.query.offset(offset).first()
    return redirect(url_for('view_sub', sub=sub.name))


@app.route("/s/<sub>")
def view_sub(sub):
    """ Here we can view subs (currently sorts like /new) """
    return view_sub_hot(sub, 1)


@app.route("/s/<sub>/edit")
@login_required
def edit_sub(sub):
    """ Here we can edit sub info and settings """
    sub = Sub.query.filter_by(name=sub).first()
    if not sub:
        abort(404)
    form = EditSubForm()
    form.css.data = sub.stylesheet.first().content
    if current_user.is_mod(sub) or current_user.is_admin():
        return render_template('editsub.html', sub=sub,
                               editsubform=form)
    else:
        abort(403)


@app.route("/s/<sub>/new.rss")
def sub_new_rss(sub):
    """ RSS feed for /s/sub/new """
    sub = Sub.query.filter_by(name=sub).first()
    if not sub:
        abort(404)

    fg = FeedGenerator()
    fg.title("/s/{}".format(sub))
    fg.subtitle("All new posts for {} feed".format(sub))
    fg.link(href=url_for('view_sub_new', sub=sub, _external=True))
    fg.generator("Throat")
    posts = sub.posts.order_by(SubPost.posted.desc())
    sorter = BasicSorting(posts)
    for post in sorter.getPosts():
        fe = fg.add_entry()
        url = url_for('view_post', sub=post.sub.name, pid=post.pid,
                      _external=True)
        fe.id(url)
        fe.link({'href': url, 'rel': 'self'})
        fe.title(post.title)

    return fg.rss_str(pretty=True)


@app.route("/s/<sub>/new", defaults={'page': 1})
@app.route("/s/<sub>/new/<int:page>")
def view_sub_new(sub, page):
    """ The index page, all posts sorted as most recent posted first """
    sub = Sub.query.filter_by(name=sub).first()
    if not sub:
        abort(404)

    posts = sub.posts.order_by(SubPost.posted.desc())
    sorter = BasicSorting(posts)
    return render_template('sub.html', sub=sub, page=page, sort_type='new',
                           posts=sorter.getPosts(page))


@app.route("/s/<sub>/postmodlog", defaults={'page': 1})
@app.route("/s/<sub>/postmodlog/<int:page>")
def view_sub_postmodlog(sub, page):
    """ The mod/admin deleted posts page, sorted as most recent posted first """
    sub = Sub.query.filter_by(name=sub).first()
    if not sub:
        abort(404)

    posts = sub.posts.order_by(SubPost.posted.desc())
    sorter = BasicSorting(posts)
    return render_template('subpostmodlog.html', sub=sub, page=page, sort_type='new',
                           posts=sorter.getPosts(page))


@app.route("/s/<sub>/top", defaults={'page': 1})
@app.route("/s/<sub>/top/<int:page>")
def view_sub_top(sub, page):
    """ The index page, /top sorting """
    sub = Sub.query.filter_by(name=sub).first()
    if not sub:
        abort(404)

    posts = sub.posts.order_by(SubPost.posted.desc())
    sorter = VoteSorting(posts)
    return render_template('sub.html', sub=sub, page=page, sort_type='top',
                           posts=sorter.getPosts(page))


@app.route("/s/<sub>/hot", defaults={'page': 1})
@app.route("/s/<sub>/hot/<int:page>")
def view_sub_hot(sub, page):
    """ The index page, /hot sorting """
    sub = Sub.query.filter_by(name=sub).first()
    if not sub:
        abort(404)

    posts = sub.posts.order_by(SubPost.posted.desc())
    sorter = HotSorting(posts)
    return render_template('sub.html', sub=sub, page=page, sort_type='top',
                           posts=sorter.getPosts(page))


@app.route("/s/<sub>/<pid>")
def view_post(sub, pid):
    """ View post and comments (WIP) """
    post = SubPost.query.filter_by(pid=pid).first()
    if not post or post.sub.name != sub:
        abort(404)
    if post.ptype == 1:
        return render_template('post.html', post=post,
                               edittxtpostform=EditSubTextPostForm(),
                               editlinkpostform=EditSubLinkPostForm())
    else:
        return render_template('post.html', post=post,
                               edittxtpostform=EditSubTextPostForm(),
                               editlinkpostform=EditSubLinkPostForm())


@app.route("/p/<pid>")
def view_post_inbox(pid):
    """ Gets route to post from just pid """
    post = SubPost.query.filter_by(pid=pid).first()
    sub = Sub.query.filter_by(sid=post.sid).first()
    return redirect(url_for('view_post', sub=sub.name, pid=post.pid))


@app.route("/s/<sub>/<pid>/edit")
@login_required
def edit_post(sub, pid):
    """ WIP: Edit a post content """
    return "WIP!"


@app.route("/s/<sub>/<pid>/<cid>")
def view_perm(sub, pid, cid):
    """ WIP: Permalink to comment """
    return "WIP!"


@app.route("/u/<user>")
@login_required
def view_user(user):
    """ WIP: View user's profile, posts, comments, badges, etc """
    user = User.query.filter_by(name=user).first()
    if not user:
        abort(404)

    subs = Sub.query.order_by(Sub.name.asc()).all()
    badges = UserMetadata.query.filter_by(uid=user.uid) \
                               .filter_by(key='badge').all()
    return render_template('user.html', user=user, badges=badges, subs=subs,
                           msgform=CreateUserMessageForm())


@app.route("/u/<user>/edit")
@login_required
def edit_user(user):
    """ WIP: Edit user's profile, slogan, quote, etc """
    user = User.query.filter_by(name=user).first()
    if not user:
        abort(404)

    subs = Sub.query.order_by(Sub.name.asc()).all()
    badges = UserMetadata.query.filter_by(uid=user.uid) \
                               .filter_by(key='badge').all()
    adminbadges = UserBadge.query.all()
    if current_user.get_username() == user.name or current_user.is_admin():
        return render_template('edituser.html', user=user, subs=subs,
                               badges=badges, adminbadges=adminbadges,
                               edituserform=EditUserForm())
    else:
        abort(403)


@app.route("/messages")
@login_required
def view_messages():
    """ WIP: View user's messages """
    user = session['user_id']
    messages = Message.query.filter_by(receivedby=user) \
                            .filter_by(mtype=None) \
                            .order_by(Message.posted.desc()).all()
    newcount = Message.query.filter_by(read=None) \
                            .filter(Message.mtype!='-1') \
                            .filter_by(mtype=None).count()
    return render_template('messages.html', user=user, messages=messages,
                           box_name="Inbox", newcount=newcount)


@app.route("/messages/sent")
@login_required
def view_messages_sent():
    """ WIP: View user's messages """
    user = session['user_id']
    messages = Message.query.filter_by(sentby=user) \
                            .filter((Message.mtype==None) | (Message.mtype=='-1')) \
                            .order_by(Message.posted.desc()).all()
    return render_template('messages.html', user=user, messages=messages,
                           box_name="Sent")


@app.route("/messages/replies")
@login_required
def view_messages_replies():
    """ WIP: View user's post replies """
    user = session['user_id']
    messages = Message.query.filter_by(receivedby=user) \
                            .filter(Message.mtype.isnot(None)) \
                            .filter(Message.mtype!='-1') \
                            .order_by(Message.posted.desc()).all()
    newcount = Message.query.filter_by(read=None) \
                            .filter(Message.mtype!='-1') \
                            .filter(Message.mtype.isnot(None)).count()
    return render_template('messages.html', user=user, messages=messages,
                           box_name="Replies", newcount=newcount)


@app.route("/admin")
@login_required
def admin_area():
    """ WIP: View users. assign badges, etc """
    users = User.query.all()
    subs = Sub.query.all()
    posts = SubPost.query.count()
    ups = SubPostVote.query.filter_by(positive=True).count()
    downs = SubPostVote.query.filter_by(positive=False).count()
    badges = UserBadge.query.all()
    if current_user.is_admin():
        return render_template('admin.html', users=users, badges=badges,
                               subs=subs, posts=posts, ups=ups, downs=downs,
                               createuserbadgeform=CreateUserBadgeForm(),
                               editmodform=EditModForm())
    else:
        return render_template('errors/404.html'), 404


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


@app.errorhandler(403)
def Forbidden(error):
    """ 403 Forbidden """
    return render_template('errors/403.html'), 403


@app.errorhandler(404)
def not_found(error):
    """ 404 Not found error """
    return render_template('errors/404.html'), 404


@app.errorhandler(418)
def teapot(error):
    """ 404 I'm a teapot """
    return render_template('errors/418.html'), 404


@app.errorhandler(500)
def server_error(error):
    """ 500 Internal server error """
    return render_template('errors/500.html'), 500
