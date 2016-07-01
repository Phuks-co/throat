""" /do/ views (AJAX stuff) """

import json
import re
import datetime
import bcrypt
from flask import Blueprint, redirect, url_for, session
from sqlalchemy import func
from ..models import db, User, Sub, SubPost, Message, SubPostComment
from ..models import SubPostVote, SubMetadata, SubPostMetadata, SubStylesheet
from ..models import UserMetadata, UserBadge, SubSubscriber
from ..forms import RegistrationForm, LoginForm, LogOutForm
from ..forms import CreateSubForm, EditSubForm, EditUserForm
from ..forms import CreateUserBadgeForm, EditModForm
from ..forms import CreateSubTextPost, CreateSubLinkPost, EditSubTextPostForm
from ..forms import PostComment, CreateUserMessageForm, DeletePost
from ..forms import EditSubLinkPostForm, SearchForm
from flask_login import login_user, login_required, logout_user, current_user
from ..misc import SiteUser

do = Blueprint('do', __name__)

# Regex to match allowed names in subs and usernames
allowedNames = re.compile("^[a-zA-Z0-9_-]+$")
# allowedCSS = re.compile("\'(^[0-9]{1,5}[a-zA-Z ]+$)|none\'")


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


@do.route("/do/search", methods=['POST'])
def search():
    """ Search endpoint """
    form = SearchForm()
    term = form.term.data
    return redirect(url_for('search', term=term))


@do.route("/do/login", methods=['POST'])
def login():
    """ Login endpoint """
    form = LoginForm()
    if form.validate():
        user = User.query.filter(func.lower(User.name) ==
                                 func.lower(form.username.data)).first()
        if not user:
            return json.dumps({'status': 'error',
                               'error': ['User does not exist.']})

        if user.crypto == 1:  # bcrypt
            thash = bcrypt.hashpw(form.password.data.encode('utf-8'),
                                  user.password.encode('utf-8'))
            if thash == user.password.encode('utf-8'):
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
        if User.query.filter(func.lower(User.name) ==
                             func.lower(form.username.data)).first():
            return json.dumps({'status': 'error',
                               'error': ['Username is already registered.']})
        if User.query.filter(func.lower(User.email) ==
                             func.lower(form.email.data)).first() and \
           form.email.data != '':
            return json.dumps({'status': 'error',
                               'error': ['Email is alredy in use.']})
        user = User(form.username.data, form.email.data, form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(SiteUser(user))
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/edit_user/<user>", methods=['POST'])
@login_required
def edit_user(user):
    """ Edit user endpoint """
    user = User.query.filter(func.lower(User.name) == func.lower(user)).first()
    if not user:
        return json.dumps({'status': 'error',
                           'error': ['User does not exist']})
    if current_user or current_user.admin():
        form = EditUserForm()
        if form.validate():
            user.email = form.email.data
            exlinks = UserMetadata.query.filter_by(uid=user.uid) \
                                        .filter_by(key='exlinks').first()
            if exlinks:
                exlinks.value = form.external_links.data
            else:
                exlinksmeta = UserMetadata()
                exlinksmeta.uid = user.uid
                exlinksmeta.key = 'exlinks'
                exlinksmeta.value = form.external_links.data
                db.session.add(exlinksmeta)

            styles = UserMetadata.query.filter_by(uid=user.uid) \
                                        .filter_by(key='styles').first()
            if styles:
                styles.value = form.disable_sub_style.data
            else:
                stylesmeta = UserMetadata()
                stylesmeta.uid = user.uid
                stylesmeta.key = 'styles'
                stylesmeta.value = form.disable_sub_style.data
                db.session.add(stylesmeta)

            nsfw = UserMetadata.query.filter_by(uid=user.uid) \
                                     .filter_by(key='nsfw').first()
            if nsfw:
                nsfw.value = form.show_nsfw.data
            else:
                nsfwmeta = UserMetadata()
                nsfwmeta.uid = user.uid
                nsfwmeta.key = 'nsfw'
                nsfwmeta.value = form.show_nsfw.data
                db.session.add(nsfwmeta)

            db.session.commit()
            return json.dumps({'status': 'ok',
                               'addr': url_for('view_user', user=user.name)})
        return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/delete_post", methods=['POST'])
@login_required
def delete_post():
    """ Post deletion endpoint """
    form = DeletePost()

    if form.validate():
        post = SubPost.query.filter_by(pid=form.post.data).first()
        if not post:
            return json.dumps({'status': 'error',
                               'error': ['Post does not exist.']})

        if not current_user.is_mod(post.sub) and not current_user.is_admin() \
            and not post.user:
            return json.dumps({'status': 'error',
                               'error': ['Not authorized.']})

            md = SubPostMetadata(post.pid, 'moddeleted', '1')
        if post.uid == session['user_id']:
            md = SubPostMetadata(post.pid, 'deleted', '1')
        else:
            md = SubPostMetadata(post.pid, 'moddeleted', '1')
        db.session.add(md)
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

        if Sub.query.filter(func.lower(Sub.name) ==
                            func.lower(form.subname.data)).first():
            return json.dumps({'status': 'error',
                               'error': ['Sub is already registered.']})

        sub = Sub(form.subname.data, form.title.data)
        db.session.add(sub)
        ux = SubMetadata(sub, 'mod', current_user.get_id())
        uy = SubMetadata(sub, 'mod1', current_user.get_id())
        ux2 = SubMetadata(sub, 'creation', datetime.datetime.utcnow())
        ux3 = SubMetadata(sub, 'nsfw', '0')
        ux4 = SubStylesheet(sub, content='/** css here **/')
        db.session.add(ux)
        db.session.add(uy)
        db.session.add(ux2)
        db.session.add(ux3)
        db.session.add(ux4)
        db.session.commit()

        return json.dumps({'status': 'ok',
                           'addr': url_for('view_sub', sub=form.subname.data)})

    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/edit_sub/<sub>", methods=['POST'])
@login_required
def edit_sub(sub):
    """ Edit sub endpoint """
    sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
    if not sub:
        return json.dumps({'status': 'error',
                           'error': ['Sub does not exist']})
    if current_user.is_mod(sub) or current_user.is_admin():
        form = EditSubForm()
        if form.validate():
            sub.title = form.title.data
            nsfw = sub.properties.filter_by(key='nsfw').first()
            if nsfw:
                nsfw.value = form.nsfw.data
            else:
                nsfw = SubMetadata(sub, 'nsfw', form.nsfw.data)
                db.session.add(nsfw)
            if sub.stylesheet.first():
                sub.stylesheet.first().content = form.css.data
            else:
                css = SubStylesheet(sub.sid, form.css.data)
                db.session.add(css)
            db.session.commit()
            return json.dumps({'status': 'ok',
                               'addr': url_for('view_sub', sub=sub.name)})
        return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/edit_mod/<sub>/<user>", methods=['POST'])
@login_required
def edit_mod(sub, user):
    """ Edit sub mod endpoint """
    if current_user.is_admin():
        form = EditModForm()
        sub = Sub.query.filter_by(name=form.sub.data).first()
        if not sub:
            return json.dumps({'status': 'error',
                               'error': ['Sub does not exist']})
        user = User.query.filter_by(name=form.user.data).first()
        if not user:
            return json.dumps({'status': 'error',
                               'error': ['User does not exist']})
        if form.validate():
            topmod = sub.properties.filter_by(key='mod1').first()
            if topmod:
                sub.properties.filter_by(key='mod1').first().value = user.uid
            else:
                x = SubMetadata(sub, 'mod1', current_user.get_id())
                db.session.add(x)
            db.session.commit()
            return json.dumps({'status': 'ok'})
        return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/subscribe/<sid>", methods=['POST'])
@login_required
def subscribe_to_sub(sid):
    """ Subscribe to sub """
    userid = current_user.get_id()
    subscribe = SubSubscriber()
    subscribe.sid = sid
    subscribe.uid = userid
    subscribe.status = '1'
    subscribe.time = datetime.datetime.utcnow()

    blocked = SubSubscriber.query.filter_by(sid=sid) \
                                .filter_by(uid=userid) \
                                .filter_by(status='2').first()
    if blocked:
        db.session.delete(blocked)
    db.session.add(subscribe)
    db.session.commit()
    return json.dumps({'status': 'ok', 'message': 'subscribed'})


@do.route("/do/unsubscribe/<sid>", methods=['POST'])
@login_required
def unsubscribe_from_sub(sid):
    """ Unsubscribe from sub """
    userid = current_user.get_id()
    res = SubSubscriber.query.filter_by(sid=sid) \
                             .filter_by(uid=userid) \
                             .filter_by(status='1').delete()
    db.session.commit()
    return json.dumps({'status': 'ok', 'message': 'unsubscribed'})


@do.route("/do/block/<sid>", methods=['POST'])
@login_required
def block_sub(sid):
    """ Block sub """
    userid = current_user.get_id()
    subscribe = SubSubscriber()
    subscribe.sid = sid
    subscribe.uid = userid
    subscribe.status = '2'
    subscribe.time = datetime.datetime.utcnow()

    subbed = SubSubscriber.query.filter_by(sid=sid) \
                                .filter_by(uid=userid) \
                                .filter_by(status='1').first()
    if subbed:
        db.session.delete(subbed)
    db.session.add(subscribe)
    db.session.commit()
    return json.dumps({'status': 'ok', 'message': 'subscribed'})


@do.route("/do/unblock/<sid>", methods=['POST'])
@login_required
def unblock_sub(sid):
    """ Unblock sub """
    userid = current_user.get_id()
    res = SubSubscriber.query.filter_by(sid=sid) \
                             .filter_by(uid=userid) \
                             .filter_by(status='2').delete()
    db.session.commit()
    return json.dumps({'status': 'ok', 'message': 'unsubscribed'})


@do.route("/do/txtpost/<sub>", methods=['POST'])
@login_required
def create_txtpost(sub):
    """ Sub text post creation endpoint """

    form = CreateSubTextPost()
    if form.validate():
        # Put pre-posting checks here
        sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
        if not sub:
            return json.dumps({'status': 'error',
                               'error': ['Sub does not exist']})

        post = SubPost()
        post.sid = sub.sid
        post.uid = current_user.get_id()
        post.title = form.title.data
        post.content = form.content.data
        post.ptype = "0"
        post.posted = datetime.datetime.utcnow()
        db.session.add(post)
        db.session.commit()
        return json.dumps({'status': 'ok', 'pid': post.pid, 'sub': sub.name})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/get_txtpost/<pid>", methods=['GET'])
def get_txtpost(pid):
    """ Sub text post expando get endpoint """
    post = SubPost.query.filter_by(pid=pid).first()
    if post:
        return json.dumps({'status': 'ok', 'content': post.content})
    else:
        return json.dumps({'status': 'error',
                           'error': ['No longer available']})


@do.route("/do/edit_txtpost/<sub>/<pid>", methods=['POST'])
@login_required
def edit_txtpost(sub, pid):
    """ Sub text post creation endpoint """
    form = EditSubTextPostForm()
    if form.validate():
        post = SubPost()
        post.content = form.content.data
        # post.edited = datetime.datetime.utcnow()
        SubPost.query.filter_by(pid=pid) \
                     .update(dict(content=form.content.data))
        # nsfw metadata
        nsfw = SubPostMetadata.query.filter_by(pid=pid) \
                                    .filter_by(key='nsfw').first()
        if nsfw:
            nsfw.value = form.nsfw.data
        else:
            nsfw = SubPostMetadata(pid, 'nsfw', form.nsfw.data)
            db.session.add(nsfw)
        db.session.commit()
        return json.dumps({'status': 'ok', 'sub': sub, 'pid': pid})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/lnkpost/<sub>", methods=['POST'])
@login_required
def create_lnkpost(sub):
    """ Sub text post creation endpoint """

    form = CreateSubLinkPost()
    if form.validate():
        # Put pre-posting checks here
        sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
        if not sub:
            return json.dumps({'status': 'error',
                               'error': ['Sub does not exist']})

        post = SubPost()
        post.sid = sub.sid
        post.uid = current_user.get_id()
        post.title = form.title.data
        post.link = form.link.data
        post.ptype = "1"
        post.posted = datetime.datetime.utcnow()
        db.session.add(post)
        db.session.commit()
        return json.dumps({'status': 'ok', 'pid': post.pid, 'sub': sub.name})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/edit_linkpost/<sub>/<pid>", methods=['POST'])
@login_required
def edit_linkpost(sub, pid):
    """ Sub text post creation endpoint """
    form = EditSubLinkPostForm()
    if form.validate():
        post = SubPost()
        # nsfw metadata
        nsfw = SubPostMetadata.query.filter_by(pid=pid) \
                                    .filter_by(key='nsfw').first()
        if nsfw:
            nsfw.value = form.nsfw.data
        else:
            nsfw = SubPostMetadata(pid, 'nsfw', form.nsfw.data)
            db.session.add(nsfw)
        db.session.commit()
        return json.dumps({'status': 'ok', 'sub': sub, 'pid': pid})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route('/do/upvote/<pid>', methods=['POST'])
@login_required
def upvote(pid):
    """ Logs an upvote to a post. """
    post = SubPost.query.filter_by(pid=pid).first()
    if not post:
        return json.dumps({'status': 'error',
                           'error': ['Post does not exist']})

    if post.uid == current_user.get_id():
        return json.dumps({'status': 'error',
                           'error': ['You can\'t vote on your own posts']})

    qvote = SubPostVote.query.filter_by(pid=pid) \
                             .filter_by(uid=current_user.get_id()).first()
    vote = SubPostVote()
    vote.pid = pid
    vote.uid = current_user.get_id()
    vote.positive = True

    if qvote:
        if qvote.positive:
            return json.dumps({'status': 'error',
                               'error': ['You already voted.']})
        else:
            qvote.positive = True
            db.session.add(qvote)
            db.session.commit()
            return json.dumps({'status': 'ok',
                               'message': 'Negative vote reverted.'})

    db.session.add(vote)
    db.session.commit()
    return json.dumps({'status': 'ok'})


@do.route('/do/downvote/<pid>', methods=['POST'])
@login_required
def downvote(pid):
    """ Logs a downvote to a post. """
    post = SubPost.query.filter_by(pid=pid).first()
    if not post:
        return json.dumps({'status': 'error',
                           'error': ['Post does not exist']})

    qvote = SubPostVote.query.filter_by(pid=pid) \
                             .filter_by(uid=current_user.get_id()).first()
    vote = SubPostVote()
    vote.pid = pid
    vote.uid = current_user.get_id()
    vote.positive = False

    if qvote:
        if not qvote.positive:
            return json.dumps({'status': 'error',
                               'error': ['You already voted.']})
        else:
            qvote.positive = False
            db.session.add(qvote)
            db.session.commit()
            return json.dumps({'status': 'ok',
                               'message': 'Positive vote reverted.'})

    db.session.add(vote)
    db.session.commit()
    return json.dumps({'status': 'ok'})


@do.route('/do/sendcomment/<sub>/<pid>', methods=['POST'])
@login_required
def create_comment(sub, pid):
    """ Here we send comments. """
    form = PostComment()
    if form.validate():
        # 1 - Check if sub exists.
        sub = Sub.query.filter(func.lower(Sub.name) ==
                               func.lower(sub)).first()
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
        comment.content = form.comment.data.encode()
        comment.time = datetime.datetime.utcnow()
        print(form.parent.data)

        if form.parent.data != "0":
            comment.parentcid = form.parent.data
        # send pm to op
        pm = Message()
        pm.sentby = current_user.get_id()
        pm.receivedby = post.uid
        if form.parent.data != "0":
            pm.subject = 'Comment reply: ' + post.title
        else:
            pm.subject = 'Post reply: ' + post.title
        pm.content = form.comment.data
        pm.mtype = post.pid
        pm.posted = datetime.datetime.utcnow()
        db.session.add(pm)
        db.session.add(comment)
        db.session.commit()
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/create_user_badge", methods=['POST'])
@login_required
def create_user_badge():
    """ User Badge creation endpoint """
    form = CreateUserBadgeForm()
    if form.validate():
        badge = UserBadge(form.badge.data, form.name.data, form.text.data)
        db.session.add(badge)
        db.session.commit()
        return json.dumps({'status': 'ok', 'bid': badge.bid})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/assign_user_badge/<uid>/<bid>", methods=['POST'])
@login_required
def assign_user_badge(uid, bid):
    """ Assign User Badge endpoint """
    if current_user.is_admin():
        badge = UserMetadata()
        badge.uid = uid
        badge.key = 'badge'
        badge.value = bid
        db.session.add(badge)
        db.session.commit()
        return json.dumps({'status': 'ok', 'bid': bid})


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


@do.route("/do/read_pm/<mid>", methods=['POST'])
@login_required
def read_pm(mid):
    """ Mark PM as read """
    message = Message.query.filter_by(mid=mid).first()
    if session['user_id'] == message.receivedby:
        read = datetime.datetime.utcnow()
        message.read = read
        db.session.commit()
        return json.dumps({'status': 'ok', 'mid': mid})
        # return json.dumps({'status': 'error', 'error': 'something broke'})


@do.route("/do/delete_pm/<mid>", methods=['POST'])
@login_required
def delete_pm(mid):
    """ Delete PM """
    message = Message.query.filter_by(mid=mid).first()
    if session['user_id'] == message.receivedby:
        message.mtype = '-1'
        db.session.commit()
        return json.dumps({'status': 'ok', 'mid': mid})
        # return json.dumps({'status': 'error', 'error': 'something broke'})
