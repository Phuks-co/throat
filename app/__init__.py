# -*- coding: utf-8
""" Here is where all the good stuff happens """

import json
import time
import re
from wsgiref.handlers import format_date_time
import datetime

import bcrypt
import markdown
from flask import Flask, render_template, session, redirect, url_for, abort
from flask import make_response
from flask_assets import Environment, Bundle
from flask_login import LoginManager, login_required, current_user

from .models import db, User, Sub, SubPost, Message
from .forms import RegistrationForm, LoginForm, LogOutForm
from .forms import CreateSubForm, EditSubForm
from .forms import CreateSubTextPost, CreateSubLinkPost
from .forms import CreateUserMessageForm, PostComment
from .forms import DummyForm
from .views import do
from .misc import SiteUser, getVoteCount, hasVoted


app = Flask(__name__)
app.register_blueprint(do)
app.config.from_object('config')

db.init_app(app)

assets = Environment(app)
login_manager = LoginManager(app)
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
            'getVoteCount': getVoteCount, 'hasVoted': hasVoted}


@app.route("/")
def index():
    """ The index page, currently sorts like /all/new """
    subposts = SubPost.query.order_by(SubPost.posted.desc()).all()
    return render_template('index.html', posts=subposts)


@app.route("/new")
def index_new():
    """ The index page, currently sorts like /all/new """
    subposts = SubPost.query.order_by(SubPost.posted.desc()).all()
    return render_template('index.html', posts=subposts)


@app.route("/all/new")
def index_all_new():
    """ The index page, all posts sorted as most recent posted first """
    subposts = SubPost.query.order_by(SubPost.posted.desc()).all()
    return render_template('index.html', posts=subposts)


@app.route("/s/<sub>")
def view_sub(sub):
    """ Here we can view subs (currently sorts like /new) """
    sub = Sub.query.filter_by(name=sub).first()
    if not sub:
        abort(404)

    user = session['user_id']
    subposts = SubPost.query.filter_by(sid=sub.sid) \
                            .order_by(SubPost.posted.desc()).all()
    return render_template('sub.html', sub=sub.name, sub_title=sub.title,
                           txtpostform=CreateSubTextPost(),
                           lnkpostform=CreateSubLinkPost(),
                           editsubform=EditSubForm(), posts=subposts)


@app.route("/s/<sub>/new")
def view_sub_new(sub):
    """ Here we can view subs sorted as most recent posted first """
    sub = Sub.query.filter_by(name=sub).first()
    if not sub:
        abort(404)

    user = session['user_id']
    subposts = SubPost.query.filter_by(sid=sub.sid) \
                            .order_by(SubPost.posted.desc()).all()
    return render_template('sub.html', sub=sub.name, sub_title=sub.title,
                           txtpostform=CreateSubTextPost(),
                           lnkpostform=CreateSubLinkPost(),
                           editsubform=EditSubForm(), posts=subposts)


@app.route("/s/<sub>/<pid>")
def view_post(sub, pid):
    """ View post and comments (WIP) """
    post = SubPost.query.filter_by(pid=pid).first()
    if not post or post.sub.name != sub:
        abort(404)
    return render_template('post.html', post=post)


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

    return render_template('user.html', user=user,
                           msgform=CreateUserMessageForm())


@app.route("/u/<user>/edit")
@login_required
def edit_user(user):
    """ WIP: Edit user's profile, slogan, quote, etc """
    return "WIP!"


@app.route("/messages")
@login_required
def view_messages():
    """ WIP: View user's messages """
    user = session['user_id']
    messages = Message.query.filter_by(receivedby=user) \
                            .order_by(Message.posted.desc()).all()

    return render_template('messages.html', user=user, messages=messages,
                           box_name="Inbox")


@app.route("/messages/sent")
@login_required
def view_messages_sent():
    """ WIP: View user's messages """
    user = session['user_id']
    messages = Message.query.filter_by(sentby=user) \
                            .order_by(Message.posted.desc()).all()
    return render_template('messages.html', user=user, messages=messages,
                           box_name="Sent")


@app.route("/messages/posts")
@login_required
def view_messages_posts():
    """ WIP: View user's messages """
    user = session['user_id']
    messages = Message.query.filter_by(receivedby=user) \
                            .order_by(Message.posted.desc()).all()
    return render_template('messages.html', user=user, messages=messages,
                           box_name="Post Replies")


@app.route("/messages/comments")
@login_required
def view_messages_comments():
    """ WIP: View user's messages """
    user = session['user_id']
    messages = Message.query.filter_by(receivedby=user) \
                            .order_by(Message.posted.desc()).all()
    return render_template('messages.html', user=user, messages=messages,
                           box_name="Comment Replies")


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
