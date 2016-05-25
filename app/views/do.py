""" /do/ views (AJAX stuff) """

import json
import re
import datetime
import bcrypt
from flask import Blueprint, redirect, url_for
from ..models import db, User, Sub, SubPost, Message, SubPostComment
from ..forms import RegistrationForm, LoginForm, LogOutForm, CreateSubForm
from ..forms import CreateSubTextPost, PostComment, CreateUserMessageForm
from flask_login import login_user, login_required, logout_user, current_user
from ..misc import SiteUser

do = Blueprint('do', __name__)

# Regex to match allowed names in subs and usernames
allowedNames = re.compile("^[a-zA-Z0-9_-]+$")


def get_errors(form):
    """ A simple function that returns a list with all the form errors. """
    ret = []
    for field, errors in form.errors.items():
        for error in errors:
            ret.append(u"Error in the '%s' field - %s" % (
                getattr(form, field).label.text,
                error))
    return ret


@do.route("/do/logout", methods=['POST'])
@login_required
def logout():
    """ Logout endpoint """
    form = LogOutForm()
    if form.validate():
        logout_user()
    return redirect(url_for('index'))


@do.route("/do/login", methods=['POST'])
def login():
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
                theuser = SiteUser(user)
                login_user(theuser, remember=form.remember.data)
                return json.dumps({'status': 'ok'})
            else:
                return json.dumps({'status': 'error',
                                   'error': ['Invalid password.']})
        else:
            return json.dumps({'status': 'error',
                               'error': ['Unknown password hash']})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/register", methods=['POST'])
def register():
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
        if User.query.filter_by(email=form.email.data).first() and \
           form.email.data != '':
            return json.dumps({'status': 'error',
                               'error': ['Email is alredy in use.']})
        user = User(form.username.data, form.email.data, form.password.data)
        db.session.add(user)
        db.session.commit()
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/create_sub", methods=['POST'])
@login_required
def create_sub():
    """ Sub creation endpoint """
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


@do.route("/do/txtpost/<sub>", methods=['POST'])
@login_required
def create_txtpost(sub):
    """ Sub text post creation endpoint """

    form = CreateSubTextPost()
    if form.validate():
        # Put pre-posting checks here
        sub = Sub.query.filter_by(name=sub).first()
        if not sub:
            return json.dumps({'status': 'error',
                               'error': ['Sub does not exist']})

        post = SubPost()
        post.sid = sub.sid
        post.uid = current_user.get_id()
        post.title = form.title.data
        post.content = form.content.data
        post.posted = datetime.datetime.utcnow()
        db.session.add(post)
        db.session.commit()
        return json.dumps({'status': 'ok', 'pid': post.pid, 'sub': sub.name})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route('/do/sendcomment/<sub>/<pid>', methods=['POST'])
@login_required
def create_comment(sub, pid):
    """ Here we send comments. """
    form = PostComment()
    if form.validate():
        # 1 - Check if sub exists.
        sub = Sub.query.filter_by(name=sub).first()
        if not sub:
            return json.dumps({'status': 'error',
                               'error': ['Sub does not exist']})
        # 2 - Check if post exists.
        post = SubPost.query.filter_by(pid=pid).first()
        if not post:
            return json.dumps({'status': 'error',
                               'error': ['Post does not exist']})
        # 3 - Check if the post is in that sub.
        if not post.sub.name == sub.name:
            return json.dumps({'status': 'error',
                               'error': ['Post does not exist']})

        # 4 - All OK, post dem comment.
        comment = SubPostComment()
        comment.uid = current_user.get_id()
        comment.pid = pid
        comment.content = form.comment.data
        comment.time = datetime.datetime.utcnow()
        print(form.parent.data)

        if form.parent.data != "0":
            comment.parentcid = form.parent.data
        db.session.add(comment)
        db.session.commit()
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/sendmsg/<user>", methods=['POST'])
@login_required
def create_sendmsg(user):
    """ User PM message creation endpoint """

    form = CreateUserMessageForm()
    if form.validate():
        # Put pre-posting checks here
        # user = User.query.filter_by(name=user).first()
        # if not user:
        #    return json.dumps({'status': 'error',
        #                       'error': ['User does not exist']})

        msg = Message()
        msg.receivedby = user
        msg.sentby = current_user.get_id()
        msg.subject = form.subject.data
        msg.content = form.content.data
        msg.posted = datetime.datetime.utcnow()
        db.session.add(msg)
        db.session.commit()
        return json.dumps({'status': 'ok', 'mid': msg.mid,
                           'sentby': current_user.get_id()})
    return json.dumps({'status': 'error', 'error': get_errors(form)})
