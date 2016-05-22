#!/usr/bin/env python3
# -*- coding: utf-8
""" Here is where all the good stuff happens """

import json
import time
import re
from wsgiref.handlers import format_date_time
import datetime
import bcrypt
from flask import Flask, render_template, session, redirect, url_for, abort
from flask import make_response
from flask_assets import Environment, Bundle
from models import db, User, Sub, SubPost

import config
from forms import RegistrationForm, LoginForm, LogOutForm, CreateSubForm
from forms import CreateSubTextPost
import forms

allowedNames = re.compile("^[a-zA-Z0-9_-]+$")

app = Flask(__name__)
assets = Environment(app)
origstatic = app.view_functions['static']


def cache_static(*args, **kwargs):
    """ Nasty hack to cache more on heroku """
    response = make_response(origstatic(*args, **kwargs))
    expires_time = time.mktime((datetime.datetime.now() +
                                datetime.timedelta(days=365)).timetuple())

    response.headers['Cache-Control'] = 'public, max-age=31536000'
    response.headers['Expires'] = format_date_time(expires_time)
    return response
app.view_functions['static'] = cache_static

js = Bundle('js/jquery.js', 'js/magnific-popup.js', 'js/CustomElements.js',
            'js/time-elements.js', 'js/site.js', filters='jsmin',
            output='gen/site.js')
css = Bundle('css/magnific-popup.css', 'css/style.css', 'css/font-awesome.css',
             filters='cssmin,datauri', output='gen/site.css')
assets.register('js_all', js)
assets.register('css_all', css)

app.jinja_env.globals.update(forms=forms)
app.config.from_object(config)

db.init_app(app)


@app.before_first_request
def initialize_database():
    """ This is executed before any request is processed. We use this to
    create all the tables and database shit we need. """
    db.create_all()


def checkSession():
    """ Helper function that checks if a session is valid. """
    print(session)
    if 'user' in session:
        # We also store and check the join date to prevent somebody stealing
        # a session of a different user after the user was perma-deleted
        # or if the database was emptied.
        user = User.query.filter_by(uid=session['user']).first()
        jd = user.joindate.replace(microsecond=0)
        if (not user) or session['joindate'] != jd:
            # User does not exist, invalidate session
            session.pop('user', None)
            session.pop('joindate', None)


@app.context_processor
def utility_processor():
    """ Here we set some useful stuff for templates """
    return {'loginform': LoginForm(), 'regform': RegistrationForm(),
            'checkSession': checkSession, 'logoutform': LogOutForm(),
            'csubform': CreateSubForm()}


@app.route("/")
def index():
    """ The index page, makes it /all """
    subposts = SubPost.query.order_by(SubPost.posted.desc()).all()
    return render_template('index.html', posts=subposts)


def get_errors(form):
    """ A simple function that returns a list with all the form errors. """
    ret = []
    for field, errors in form.errors.items():
        for error in errors:
            ret.append(u"Error in the '%s' field - %s" % (
                getattr(form, field).label.text,
                error))
    return ret


@app.route("/do/logout", methods=['POST'])
def do_logout():
    """ Logout endpoint """
    form = LogOutForm()
    if form.validate():
        session.pop('user', None)
        session.pop('joindate', None)
    return redirect(url_for('index'))


@app.route("/do/login", methods=['POST'])
def do_login():
    """ Login endpoint """
    form = LoginForm()
    if form.validate():
        user = User.query.filter_by(name=form.username.data).first()
        if not user:
            return json.dumps({'status': 'error',
                               'error': ['User does not exist.']})

        if user.crypto == 1:  # bcrypt
            thash = bcrypt.hashpw(form.password.data.encode(), user.password)
            if thash == user.password:
                session['user'] = user.uid
                session['joindate'] = user.joindate
                return json.dumps({'status': 'ok'})
            else:
                return json.dumps({'status': 'error',
                                   'error': ['Invalid password.']})
        else:
            return json.dumps({'status': 'error',
                               'error': ['Unknown password hash']})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@app.route("/do/register", methods=['POST'])
def do_register():
    """ Registration endpoint """
    form = RegistrationForm()
    if form.validate():
        if not allowedNames.match(form.username.data):
            return json.dumps({'status': 'error',
                               'error': ['Username has invalid characters']})
        # check if user or email are in use
        if User.query.filter_by(name=form.username.data).first():
            return json.dumps({'status': 'error',
                               'error': ['Username is already registered.']})
        if User.query.filter_by(email=form.email.data).first():
            return json.dumps({'status': 'error',
                               'error': ['Email is alredy in use.']})
        user = User(form.username.data, form.email.data, form.password.data)
        db.session.add(user)
        db.session.commit()
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@app.route("/do/create_sub", methods=['POST'])
def create_sub():
    """ Sub creation endpoint """
    if 'user' not in session:
        return json.dumps({'status': 'error',
                           'error': ['You\'re not logged in.']})
    form = CreateSubForm()
    if form.validate():
        if not allowedNames.match(form.subname.data):
            return json.dumps({'status': 'error',
                               'error': ['Sub name has invalid characters']})

        if Sub.query.filter_by(name=form.subname.data).first():
            return json.dumps({'status': 'error',
                               'error': ['Sub is already registered.']})

        sub = Sub(form.subname.data, form.title.data)
        db.session.add(sub)
        db.session.commit()
        return json.dumps({'status': 'ok',
                           'addr': url_for('view_sub', sub=form.subname.data)})

    return json.dumps({'status': 'error', 'error': get_errors(form)})


@app.route("/do/txtpost/<sub>", methods=['POST'])
def create_txtpost(sub):
    """ Sub text post creation endpoint """
    if 'user' not in session:
        return json.dumps({'status': 'error',
                           'error': ['You\'re not logged in.']})

    form = CreateSubTextPost()
    if form.validate():
        # Put pre-posting checks here
        sub = Sub.query.filter_by(name=sub).first()
        if not sub:
            return json.dumps({'status': 'error',
                               'error': ['Sub does not exist']})

        post = SubPost()
        post.sid = sub.sid
        post.uid = session['user']
        post.title = form.title.data
        post.content = form.content.data
        post.posted = datetime.datetime.utcnow()
        db.session.add(post)
        db.session.commit()
        return json.dumps({'status': 'ok', 'pid': post.pid, 'sub': sub.name})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@app.route("/s/<sub>")
def view_sub(sub):
    """ Here we can view subs """
    sub = Sub.query.filter_by(name=sub).first()
    if not sub:
        abort(404)

    subposts = SubPost.query.filter_by(sid=sub.sid) \
                            .order_by(SubPost.posted.desc()).all()
    return render_template('sub.html', sub=sub.name, sub_title=sub.title,
                           txtpostform=CreateSubTextPost(), posts=subposts)


@app.route("/s/<sub>/edit")
def edit_sub(sub):
    """ edit sub config """
    return "WIP!"


@app.route("/s/<sub>/<pid>")
def view_post(sub, pid):
    """ View post and comments (WIP) """
    post = SubPost.query.filter_by(pid=pid).first()
    if not post or post.sub.name != sub:
        abort(404)
    return render_template('post.html', post=post)


@app.route("/s/<sub>/<pid>/edit")
def edit_post(sub, pid):
    """ WIP: Edit a post content """
    return "WIP!"


@app.route("/s/<sub>/<pid>/<cid>")
def view_perm(sub, pid, cid):
    """ WIP: Permalink to comment """
    return "WIP!"


@app.route("/u/<user>")
def view_user(user):
    """ WIP: View user's profile, posts, comments, badges, etc """
    user = User.query.filter_by(name=user).first()
    if not user:
        abort(404)

    return render_template('user.html', user=user)


@app.route("/u/<user>/edit")
def edit_user(user):
    """ WIP: Edit user's profile, slogan, quote, etc """
    return "WIP!"


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

if __name__ == "__main__":
    app.run()
