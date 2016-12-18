""" /do/ views (AJAX stuff) """

import json
import re
import time
import datetime
import uuid
from io import BytesIO
import bcrypt
from bs4 import BeautifulSoup
import requests
from PIL import Image
from flask import Blueprint, redirect, url_for, session, abort
from sqlalchemy import func
from flask_login import login_user, login_required, logout_user, current_user
from flask_cache import make_template_fragment_key
import config
from .. import forms, misc
from ..models import db, User, Sub, SubPost, Message, SubPostComment
from ..models import SubPostVote, SubMetadata, SubPostMetadata, SubStylesheet
from ..models import UserMetadata, UserBadge, SubSubscriber, SiteMetadata
from ..models import SubFlair, SubLog, SiteLog, SubPostCommentVote
from ..forms import RegistrationForm, LoginForm, LogOutForm, CreateSubFlair
from ..forms import CreateSubForm, EditSubForm, EditUserForm, EditSubCSSForm
from ..forms import CreateUserBadgeForm, EditModForm, BanUserSubForm
from ..forms import CreateSubTextPost, CreateSubLinkPost, EditSubTextPostForm
from ..forms import PostComment, CreateUserMessageForm, DeletePost
from ..forms import EditSubLinkPostForm, SearchForm, EditMod2Form, EditSubFlair
from ..forms import DeleteSubFlair, UseBTCdonationForm
from ..misc import SiteUser, cache, getMetadata, sendMail, getDefaultSubs

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


@do.route("/do/title_search", methods=['POST'])
def title_search():
    """ Search endpoint """
    form = SearchForm()
    term = form.term.data
    return redirect(url_for('search', term=term))


@do.route("/do/admin_users_search", methods=['POST'])
def admin_users_search():
    """ Search endpoint """
    form = SearchForm()
    term = form.term.data
    return redirect(url_for('admin_users_search', term=term))


@do.route("/do/admin_subs_search", methods=['POST'])
def admin_subs_search():
    """ Search endpoint """
    form = SearchForm()
    term = form.term.data
    return redirect(url_for('admin_subs_search', term=term))


@do.route("/do/admin_post_search", methods=['POST'])
def admin_post_search():
    """ Search endpoint """
    form = SearchForm()
    term = form.term.data
    return redirect(url_for('admin_post_search', term=term))


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
        # defaults
        defaults = getDefaultSubs()
        for d in defaults:
            x = SubSubscriber(d.sid, user.uid, 1)
            db.session.add(x)
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
    if current_user.get_id() != user.uid and not current_user.is_admin():
        abort(403)

    form = EditUserForm()
    if form.validate():
        if not user.isPasswordCorrect(form.oldpassword.data):
            return json.dumps({'status': 'error', 'error': ['Wrong password']})

        user.email = form.email.data
        if form.password.data:
            user.setPassword(form.password.data)
        exlinks = UserMetadata.query.filter_by(uid=user.uid) \
                                    .filter_by(key='exlinks').first()
        if exlinks:
            exlinks.value = form.external_links.data
        else:
            exlinksmeta = UserMetadata(user.uid, 'exlinks',
                                       form.external_links.data)
            db.session.add(exlinksmeta)

        styles = UserMetadata.query.filter_by(uid=user.uid) \
                                   .filter_by(key='styles').first()
        if styles:
            styles.value = form.disable_sub_style.data
        else:
            stylesmeta = UserMetadata(user.uid, 'styles',
                                      form.disable_sub_style.data)
            db.session.add(stylesmeta)

        nsfw = UserMetadata.query.filter_by(uid=user.uid) \
                                 .filter_by(key='nsfw').first()
        if nsfw:
            nsfw.value = form.show_nsfw.data
        else:
            nsfwmeta = UserMetadata(user.uid, 'nsfw', form.show_nsfw.data)
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

        if post.uid == session['user_id']:
            md = SubPostMetadata(post.pid, 'deleted', '1')
            cache.delete_memoized(getMetadata, post, 'deleted')
            SubPostMetadata.cache.uncache(key='deleted', pid=post.pid)
        else:
            md = SubPostMetadata(post.pid, 'moddeleted', '1')
            cache.delete_memoized(getMetadata, post, 'moddeleted')
            SubPostMetadata.cache.uncache(key='moddeleted', pid=post.pid)

        # :(
        cache.delete(make_template_fragment_key('subposts',
                                                vary_on=[post.sub.sid, 'new']))
        cache.delete(make_template_fragment_key('subposts',
                                                vary_on=[post.sub.sid, 'hot']))
        cache.delete(make_template_fragment_key('subposts',
                                                vary_on=[post.sub.sid, 'top']))
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

        if misc.moddedSubCount(current_user.get_id()) >= 15:
            return json.dumps({'status': 'error',
                               'error': ["You can't mod more than 15 subs."]})

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
        # admin/site log
        alog = SiteLog()
        alog.action = 4  # subs
        alog.time = datetime.datetime.utcnow()
        alog.desc = current_user.get_username() + ' created a new sub'
        alog.link = url_for('view_sub', sub=sub.name)
        db.session.add(alog)
        x = SubSubscriber(sub.sid, current_user.get_id(), 1)
        db.session.add(x)

        db.session.commit()

        return json.dumps({'status': 'ok',
                           'addr': url_for('view_sub', sub=form.subname.data)})

    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/edit_sub_css/<sub>", methods=['POST'])
@login_required
def edit_sub_css(sub):
    """ Edit sub endpoint """
    sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
    if not sub:
        return json.dumps({'status': 'error',
                           'error': ['Sub does not exist']})
    if not current_user.is_mod(sub) and not current_user.is_admin():
        abort(403)

    stylesheet = SubStylesheet.query.filter_by(sid=sub.sid).first()
    form = EditSubCSSForm()
    if form.validate():
        if stylesheet:
            stylesheet.content = form.css.data
            log = SubLog(sub.sid)
            log.action = 4  # action modedit of sub
            log.desc = 'CSS edited by ' + current_user.get_username()
            # log.link = url_for('view_sub', sub=sub.name)
            db.session.add(log)
        else:
            css = SubStylesheet(sub.sid, form.css.data)
            db.session.add(css)
        db.session.commit()
        return json.dumps({'status': 'ok',
                           'addr': url_for('view_sub', sub=sub.name)})
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
            sub.sidebar = form.sidebar.data

            nsfw = getMetadata(sub, 'nsfw', record=True)
            if nsfw:
                nsfw.value = form.nsfw.data
            else:
                nsfw = SubMetadata(sub, 'nsfw', form.nsfw.data)
                db.session.add(nsfw)
            cache.delete_memoized(getMetadata, sub, 'nsfw')
            SubMetadata.cache.uncache(key='nsfw', sid=sub.sid)
            restricted = getMetadata(sub, 'restricted', record=True)
            if restricted:
                restricted.value = form.restricted.data
            else:
                restricted = SubMetadata(sub, 'restricted',
                                         form.restricted.data)
                db.session.add(restricted)
            cache.delete_memoized(getMetadata, sub, 'restricted')
            SubMetadata.cache.uncache(key='restricted', sid=sub.sid)
            usercanflair = getMetadata(sub, 'ucf', record=True)
            if usercanflair:
                usercanflair.value = form.usercanflair.data
            else:
                usercanflair = SubMetadata(sub, 'ucf', form.usercanflair.data)
                db.session.add(usercanflair)
            video = getMetadata(sub, 'videomode', record=True)
            if video:
                video.value = form.videomode.data
            else:
                video = SubMetadata(sub, 'videomode', form.videomode.data)
                db.session.add(video)
            # Cache inv. for videomode
            cache.delete_memoized(getMetadata, sub, 'videomode')
            SubMetadata.cache.uncache(key='videomode', sid=sub.sid)

            if form.subsort.data != "None":
                subsort = getMetadata(sub, 'sort', record=True)
                if subsort:
                    subsort.value = form.subsort.data
                else:
                    subsort = SubMetadata(sub, 'sort', form.subsort.data)
                    db.session.add(subsort)
                cache.delete_memoized(getMetadata, sub, 'sort')
                SubMetadata.cache.uncache(key='sort', sid=sub.sid)

            log = SubLog(sub.sid)
            log.action = 4  # action modedit of sub
            log.desc = 'Sub settings edited by ' + current_user.get_username()
            # log.link = url_for('view_sub', sub=sub.name)

            if not current_user.is_mod(sub) and current_user.is_admin():
                alog = SiteLog()
                alog.action = 4  # subs
                alog.time = datetime.datetime.utcnow()
                alog.desc = 'Sub settings edited by ' + \
                            current_user.get_username()
                alog.link = url_for('view_sub', sub=sub.name)
                db.session.add(alog)

            db.session.add(log)
            db.session.commit()
            return json.dumps({'status': 'ok',
                               'addr': url_for('view_sub', sub=sub.name)})
        return json.dumps({'status': 'error', 'error': get_errors(form)})
    else:
        abort(403)


@do.route("/do/assign_post_flair/<sub>/<pid>/<fl>", methods=['POST'])
def assign_post_flair(sub, pid, fl):
    """ Assign a post's flair """
    sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
    if not sub:
        return json.dumps({'status': 'error',
                           'error': ['Sub does not exist']})
    post = SubPost.query.filter_by(pid=pid).first()
    if not post:
        return json.dumps({'status': 'error',
                           'error': ['Post does not exist']})
    if current_user.is_mod(sub) or post.user.uid == current_user.get_id() \
       or current_user.is_admin():
        flair = SubFlair.query.filter_by(xid=fl, sid=sub.sid).first()
        if not flair:
            return json.dumps({'status': 'error',
                               'error': ['Flair does not exist']})

        postfl = getMetadata(post, 'flair', record=True)
        if postfl:
            postfl.value = flair.text
        else:
            x = SubPostMetadata(pid, 'flair', flair.text)
            db.session.add(x)

        log = SubLog(sub.sid)
        log.action = 3  # action postflair
        log.desc = current_user.get_username() + ' assigned post flair'
        log.link = url_for('view_post', sub=post.sub.name, pid=post.pid)
        db.session.add(log)

        if not current_user.is_mod(sub) and current_user.is_admin():
            alog = SiteLog()
            alog.action = 4  # subs
            alog.time = datetime.datetime.utcnow()
            alog.desc = current_user.get_username() + ' assigned post flair'
            alog.link = url_for('view_post', sub=post.sub.name, pid=post.pid)
            db.session.add(alog)

        db.session.commit()
        SubPostMetadata.cache.uncache(key='flair', pid=post.pid)
        return json.dumps({'status': 'ok'})
    else:
        abort(403)


@do.route("/do/remove_post_flair/<sub>/<pid>", methods=['POST'])
def remove_post_flair(sub, pid):
    """ Deletes a post's flair """
    sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
    if not sub:
        return json.dumps({'status': 'error',
                           'error': ['Sub does not exist']})
    post = SubPost.query.filter_by(pid=pid).first()
    if not post:
        return json.dumps({'status': 'error',
                           'error': ['Post does not exist']})
    if current_user.is_mod(sub) or post.user.uid == current_user.get_id() \
       or current_user.is_admin():
        postfl = SubPostMetadata.query.filter_by(key='flair',
                                                 pid=post.pid).first()
        if not postfl:
            return json.dumps({'status': 'error',
                               'error': ['Flair does not exist']})
        else:
            db.session.delete(postfl)
            log = SubLog(sub.sid)
            log.action = 3  # action postflair
            log.desc = current_user.get_username() + ' removed post flair'
            log.link = url_for('view_post', sub=post.sub.name, pid=post.pid)
            db.session.add(log)

            if not current_user.is_mod(sub) and current_user.is_admin():
                alog = SiteLog()
                alog.action = 4  # subs
                alog.time = datetime.datetime.utcnow()
                alog.desc = current_user.get_username() + ' removed post flair'
                alog.link = url_for('view_post', sub=post.sub.name,
                                    pid=post.pid)
                db.session.add(alog)

        db.session.commit()
        SubPostMetadata.cache.uncache(key='flair', pid=post.pid)
        return json.dumps({'status': 'ok'})
    else:
        abort(403)


@do.route("/do/edit_mod", methods=['POST'])
@login_required
def edit_mod():
    """ Edit sub mod endpoint """
    if not current_user.is_admin():
        abort(403)
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
        topmod = SubMetadata.query.filter_by(sid=sub.sid) \
                                  .filter_by(key='mod1').first()

        if topmod:
            topmod.value = user.uid
        else:
            x = SubMetadata(sub, 'mod1', user.uid)
            db.session.add(x)

        log = SubLog(sub.sid)
        log.action = 6  # mod action
        log.desc = current_user.get_username() + ' transferred sub ' + \
            'ownership to ' + user.name
        log.link = url_for('view_sub', sub=sub.name)
        db.session.add(log)
        db.session.commit()
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/subscribe/<sid>", methods=['POST'])
@login_required
def subscribe_to_sub(sid):
    """ Subscribe to sub """
    userid = current_user.get_id()
    su = SubSubscriber.query.filter_by(sid=sid, uid=userid, status=1).first()
    if su:
        return json.dumps({'status': 'ok', 'message': 'already subscribed'})
    subscribe = SubSubscriber(sid, userid, 1)

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
    SubSubscriber.query.filter_by(sid=sid) \
                       .filter_by(uid=userid) \
                       .filter_by(status='1').delete()
    db.session.commit()
    return json.dumps({'status': 'ok', 'message': 'unsubscribed'})


@do.route("/do/block/<sid>", methods=['POST'])
@login_required
def block_sub(sid):
    """ Block sub """
    userid = current_user.get_id()
    su = SubSubscriber.query.filter_by(sid=sid, uid=userid, status=2).first()
    if su:
        return json.dumps({'status': 'ok', 'message': 'already blocked'})
    subscribe = SubSubscriber(sid, userid, 2)
    subscribe.time = datetime.datetime.utcnow()

    subbed = SubSubscriber.query.filter_by(sid=sid) \
                                .filter_by(uid=userid) \
                                .filter_by(status='1').first()
    if subbed:
        db.session.delete(subbed)
    db.session.add(subscribe)
    db.session.commit()
    return json.dumps({'status': 'ok', 'message': 'blocked'})


@do.route("/do/unblock/<sid>", methods=['POST'])
@login_required
def unblock_sub(sid):
    """ Unblock sub """
    userid = current_user.get_id()
    SubSubscriber.query.filter_by(sid=sid) \
                       .filter_by(uid=userid) \
                       .filter_by(status='2').delete()
    db.session.commit()
    return json.dumps({'status': 'ok', 'message': 'unsubscribed'})


@do.route("/do/txtpost", methods=['POST'])
@login_required
def create_txtpost():
    """ Sub text post creation endpoint """

    form = CreateSubTextPost()
    if form.validate():
        # Put pre-posting checks here
        sub = Sub.query.filter(func.lower(Sub.name) ==
                               func.lower(form.sub.data)).first()
        if not sub:
            return json.dumps({'status': 'error',
                               'error': ['Sub does not exist']})

        post = SubPost(sub.sid)
        post.title = form.title.data
        post.content = form.content.data
        post.ptype = "0"
        db.session.add(post)
        l = SubPostMetadata(post.pid, 'score', 1)
        db.session.add(l)
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


@do.route("/do/lnkpost", methods=['POST'])
@login_required
def create_lnkpost():
    """ Sub text post creation endpoint """

    form = CreateSubLinkPost()
    if form.validate():
        # Put pre-posting checks here
        sub = Sub.query.filter(func.lower(Sub.name) ==
                               func.lower(form.sub.data)).first()
        if not sub:
            return json.dumps({'status': 'error',
                               'error': ['Sub does not exist']})

        post = SubPost(sub.sid)
        post.title = form.title.data
        post.link = form.link.data
        post.ptype = "1"
        db.session.add(post)
        l = SubPostMetadata(post.pid, 'score', 1)
        db.session.add(l)
        nsfw = SubPostMetadata(post.pid, 'nsfw', form.nsfw.data)
        db.session.add(nsfw)
        db.session.commit()
        ckey = make_template_fragment_key('subposts', vary_on=[post.sub.sid])
        cache.delete(ckey)

        # Try to get thumbnail.
        # 1 - Check if it's an image
        try:
            req = requests.get(form.link.data, timeout=0.5)
        except requests.exceptions.RequestException:
            return json.dumps({'status': 'ok', 'pid': post.pid,
                               'sub': sub.name})
        ctype = req.headers['content-type'].split(";")[0].lower()
        filename = str(uuid.uuid4()) + '.jpg'
        good_types = ['image/gif', 'image/jpeg', 'image/png']
        if ctype in good_types:
            # yay, it's an image!!1
            # Resize
            im = Image.open(BytesIO(req.content)).convert('RGB')
        elif ctype == 'text/html':
            # Not an image!! Let's try with OpenGraph
            og = BeautifulSoup(req.text, 'lxml')
            try:
                img = og('meta', {'property': 'og:image'})[0].get('content')
            except IndexError:
                # no image
                return json.dumps({'status': 'ok', 'pid': post.pid,
                                   'sub': sub.name})
            try:
                req = requests.get(img, timeout=0.5)
            except requests.exceptions.RequestException:
                return json.dumps({'status': 'ok', 'pid': post.pid,
                                   'sub': sub.name})
            im = Image.open(BytesIO(req.content)).convert('RGB')
        else:
            return json.dumps({'status': 'ok', 'pid': post.pid,
                               'sub': sub.name})
        background = Image.new('RGB', (70, 70), (0, 0, 0))

        im.thumbnail((70, 70), Image.ANTIALIAS)

        bg_w, bg_h = background.size
        img_w, img_h = im.size
        offset = (int((bg_w - img_w) / 2), int((bg_h - img_h) / 2))
        background.paste(im, offset)
        background.save(config.THUMBNAILS + '/' + filename, "JPEG")
        tn = SubPostMetadata(post.pid, 'thumbnail', filename)
        im.close()
        background.close()
        db.session.add(tn)
        db.session.commit()
        return json.dumps({'status': 'ok', 'pid': post.pid, 'sub': sub.name})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/edit_linkpost/<sub>/<pid>", methods=['POST'])
@login_required
def edit_linkpost(sub, pid):
    """ Sub text post creation endpoint """
    form = EditSubLinkPostForm()
    if form.validate():
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


@do.route('/do/vote/<pid>/<value>', methods=['POST'])
@login_required
def upvote(pid, value):
    """ Logs an upvote to a post. """
    if value == "up":
        voteValue = 1
    elif value == "down":
        voteValue = -1
    else:
        abort(403)
    post = SubPost.query.filter_by(pid=pid).first()
    if not post:
        return json.dumps({'status': 'error',
                           'error': ['Post does not exist']})

    if post.uid == current_user.get_id():
        return json.dumps({'status': 'error',
                           'error': ['You can\'t vote on your own posts']})

    qvote = SubPostVote.query.filter_by(pid=pid) \
                             .filter_by(uid=current_user.get_id()).first()

    xvotes = getMetadata(post, 'score', record=True, cache=False)
    if not xvotes:
        xvotes = SubPostMetadata(post.pid, 'score', 1)
        db.session.add(xvotes)
        cache.delete_memoized(getMetadata, post, 'score', record=True)
        SubPostMetadata.cache.uncache(key='score', pid=post.pid)

    if qvote:
        if qvote.positive == (True if voteValue == 1 else False):
            return json.dumps({'status': 'error',
                               'error': ['You already voted.']})
        else:

            qvote.positive = True if voteValue == 1 else False
            xvotes.value = int(xvotes.value) + (voteValue*2)
            db.session.commit()
            cache.delete_memoized(misc.hasVoted, current_user.get_id(),
                                  qvote.positive)
            SubPostMetadata.cache.uncache(key='score', pid=post.pid)
            return json.dumps({'status': 'ok',
                               'message': 'Vote flipped.'})
    else:
        vote = SubPostVote()
        vote.pid = pid
        vote.uid = current_user.get_id()
        vote.positive = True if voteValue == 1 else False
        db.session.add(vote)
    cache.delete_memoized(misc.hasVoted, current_user.get_id(),
                          vote.positive)
    SubPostMetadata.cache.uncache(key='score', pid=post.pid)
    xvotes.value = int(xvotes.value) + voteValue
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

        if form.parent.data != "0":
            comment.parentcid = form.parent.data

        # send pm to parent
        pm = Message()
        pm.sentby = current_user.get_id()
        if form.parent.data != "0":
            pm.receivedby = misc.getCommentParentUID(form.parent.data)
            pm.subject = 'Comment reply: ' + post.title
            pm.mtype = 5  # comment reply
        else:
            pm.receivedby = post.uid
            pm.subject = 'Post reply: ' + post.title
            pm.mtype = 4  # Post reply
        pm.content = form.comment.data
        pm.mlink = comment.cid
        pm.posted = datetime.datetime.utcnow()
        if pm.receivedby != pm.sentby:  # This is a waste but meh
            db.session.add(pm)

        db.session.add(comment)
        db.session.commit()

        SubPostComment.cache.uncache(pid=pid, parentcid=None)
        SubPostComment.cache.uncache(pid=pid, parentcid=form.parent.data)
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/create_user_badge", methods=['POST'])
@login_required
def create_user_badge():
    """ User Badge creation endpoint """
    if current_user.is_admin():
        form = CreateUserBadgeForm()
        if form.validate():
            badge = UserBadge(form.badge.data, form.name.data, form.text.data)

            alog = SiteLog()
            alog.action = 2  # users
            alog.time = datetime.datetime.utcnow()
            alog.desc = current_user.get_username() + ' created a new badge'
            alog.link = url_for('admin_area')
            db.session.add(alog)
            db.session.add(badge)
            db.session.commit()
            return json.dumps({'status': 'ok', 'bid': badge.bid})
        return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/assign_user_badge/<uid>/<bid>", methods=['POST'])
@login_required
def assign_user_badge(uid, bid):
    """ Assign User Badge endpoint """
    if current_user.is_admin():
        bq = UserMetadata.query.filter_by(uid=uid, key='badge', value=bid)
        if bq.first():
            return json.dumps({'status': 'error',
                               'error': ['Badge is already assigned']})

        badge = UserMetadata(uid, 'badge', bid)
        db.session.add(badge)
        user = User.query.filter_by(uid=uid).first()
        alog = SiteLog()
        alog.action = 2  # users
        alog.time = datetime.datetime.utcnow()
        alog.desc = current_user.get_username() + ' assigned a user badge ' + \
            ' to ' + user.name
        alog.link = url_for('view_user', user=user.name)
        db.session.add(alog)
        db.session.commit()
        return json.dumps({'status': 'ok', 'bid': bid})
    else:
        abort(403)


@do.route("/do/remove_user_badge/<uid>/<bid>", methods=['POST'])
@login_required
def remove_user_badge(uid, bid):
    """ Remove User Badge endpoint """
    if current_user.is_admin():
        bq = UserMetadata.query.filter_by(uid=uid,) \
                               .filter_by(key='badge') \
                               .filter_by(value=bid).first()
        if not bq:
            return json.dumps({'status': 'error',
                               'error': ['Badge has already been removed']})

        bq.key = 'xbadge'
        user = User.query.filter_by(uid=uid).first()
        alog = SiteLog()
        alog.action = 2  # users
        alog.time = datetime.datetime.utcnow()
        alog.desc = current_user.get_username() + ' removed a user badge' + \
            ' from ' + user.name
        alog.link = url_for('view_user', user=user.name)
        db.session.add(alog)
        db.session.commit()
        return json.dumps({'status': 'ok', 'message': 'Badge deleted'})
    else:
        abort(403)


@do.route("/do/sendmsg", methods=['POST'])
@login_required
def create_sendmsg():
    """ User PM message creation endpoint """
    form = CreateUserMessageForm()
    if form.validate():
        msg = Message()
        msg.receivedby = form.to.data
        msg.sentby = current_user.get_id()
        msg.subject = form.subject.data
        msg.content = form.content.data
        msg.posted = datetime.datetime.utcnow()
        msg.mtype = 1  # PM
        db.session.add(msg)
        db.session.commit()
        return json.dumps({'status': 'ok', 'mid': msg.mid,
                           'sentby': current_user.get_id()})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/ban_user_sub/<sub>", methods=['POST'])
@login_required
def ban_user_sub(sub):
    """ Ban user from sub endpoint """
    sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
    if not sub:
        return json.dumps({'status': 'error',
                           'error': ['Sub does not exist']})
    if current_user.is_topmod(sub) or current_user.is_admin() \
       or current_user.is_mod(sub):
        form = BanUserSubForm()
        if form.validate():
            user = User.query.filter(func.lower(User.name) ==
                                     func.lower(form.user.data)).first()
            if not user:
                return json.dumps({'status': 'error',
                                   'error': ['User does not exist.']})
            msg = Message()
            msg.receivedby = user.uid
            msg.sentby = current_user.get_id()
            msg.subject = 'You have been banned from /s/' + sub.name
            msg.content = ':p'
            msg.posted = datetime.datetime.utcnow()
            msg.mtype = 2  # sub related
            msg.mlink = '/s/' + sub.name
            meta = SubMetadata(sub, 'ban', user.uid)

            log = SubLog(sub.sid)
            log.action = 2  # action modedit of sub
            log.desc = current_user.get_username() + ' banned ' + user.name + \
                ' from the sub'
            log.link = url_for('view_sub_bans', sub=sub.name)
            db.session.add(log)

            db.session.add(msg)
            db.session.add(meta)
            db.session.commit()

            SubMetadata.cache.uncache(key='ban', sid=sub.sid)
            cache.delete_memoized(getMetadata, sub, 'ban', all=True)
            return json.dumps({'status': 'ok', 'mid': msg.mid,
                               'sentby': current_user.get_id()})
        return json.dumps({'status': 'error', 'error': get_errors(form)})
    else:
        abort(403)


@do.route("/do/inv_mod2/<sub>", methods=['POST'])
@login_required
def inv_mod2(sub):
    """ User PM for Mod2 invite endpoint """
    sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
    if not sub:
        return json.dumps({'status': 'error',
                           'error': ['Sub does not exist']})
    if current_user.is_topmod(sub) or current_user.is_admin():
        form = EditMod2Form()
        if form.validate():
            user = User.query.filter(func.lower(User.name) ==
                                     func.lower(form.user.data)).first()
            if not user:
                return json.dumps({'status': 'error',
                                   'error': ['User does not exist.']})

            mod = SubMetadata.query.filter_by(sid=sub.sid, key='mod2',
                                              value=user.uid).first()
            mod1 = SubMetadata.query.filter_by(sid=sub.sid, key='mod1',
                                               value=user.uid).first()
            if mod or mod1:
                return json.dumps({'status': 'error',
                                   'error': ['User is already a mod.']})
            modinv = SubMetadata.query.filter_by(sid=sub.sid, key='mod2i',
                                                 value=user.uid).first()
            if modinv:
                return json.dumps({'status': 'error',
                                   'error': ['User has a pending invite.']})

            if misc.moddedSubCount(user.uid) >= 15:
                return json.dumps({'status': 'error',
                                   'error': [
                                       "User can't mod more than 15 subs"
                                   ]})
            msg = Message()
            msg.receivedby = user.uid
            msg.sentby = current_user.get_id()
            msg.subject = 'You have been invited to mod a sub.'
            msg.content = current_user.get_username() + \
                ' has invited you to help moderate ' + sub.name
            msg.posted = datetime.datetime.utcnow()
            msg.mtype = 2  # sub related
            msg.mlink = sub.name
            meta = SubMetadata(sub, 'mod2i', user.uid)

            log = SubLog(sub.sid)
            log.action = 6  # 6 mod action
            log.desc = current_user.get_username() + ' invited ' + \
                user.name + ' to the mod team'
            log.link = url_for('edit_sub_mods', sub=sub.name)
            db.session.add(log)

            db.session.add(msg)
            db.session.add(meta)
            db.session.commit()

            SubMetadata.cache.uncache(key='mod2i', sid=sub.sid)
            cache.delete_memoized(getMetadata, sub, 'mod2i', all=True)
            return json.dumps({'status': 'ok', 'mid': msg.mid,
                               'sentby': current_user.get_id()})
        return json.dumps({'status': 'error', 'error': get_errors(form)})
    else:
        abort(403)


@do.route("/do/remove_sub_ban/<sub>/<user>", methods=['POST'])
@login_required
def remove_sub_ban(sub, user):
    """ Remove Mod2 """
    user = User.query.filter(func.lower(User.name) == func.lower(user)).first()
    sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
    if current_user.is_topmod(sub) or current_user.is_admin() \
       or current_user.is_mod(sub):
        inv = SubMetadata.query.filter_by(key='ban') \
                            .filter_by(value=user.uid).first()
        inv.key = 'xban'
        log = SubLog(sub.sid)
        log.action = 2  # ban action
        log.desc = current_user.get_username() + ' removed ban on ' + user.name
        log.link = url_for('view_sub_bans', sub=sub.name)
        db.session.add(log)
        db.session.commit()

        SubMetadata.cache.uncache(key='xban', sid=sub.sid)
        cache.delete_memoized(getMetadata, sub, 'xban', all=True)
        SubMetadata.cache.uncache(key='ban', sid=sub.sid)
        cache.delete_memoized(getMetadata, sub, 'ban', all=True)
        return json.dumps({'status': 'ok', 'msg': 'user ban removed'})
    else:
        abort(403)


@do.route("/do/remove_mod2/<sub>/<user>", methods=['POST'])
@login_required
def remove_mod2(sub, user):
    """ Remove Mod2 """
    user = User.query.filter(func.lower(User.name) == func.lower(user)).first()
    sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
    if current_user.is_topmod(sub) or current_user.is_admin():
        inv = SubMetadata.query.filter_by(key='mod2') \
                            .filter_by(value=user.uid).first()
        inv.key = 'xmod2'
        log = SubLog(sub.sid)
        log.action = 6  # 6 mod action
        log.desc = current_user.get_username() + ' removed ' + user.name + \
            ' from the mod team'
        log.link = url_for('edit_sub_mods', sub=sub.name)
        db.session.add(log)
        db.session.commit()

        SubMetadata.cache.uncache(key='mod2', sid=sub.sid)
        cache.delete_memoized(getMetadata, sub, 'mod2', all=True)
        SubMetadata.cache.uncache(key='xmod2', sid=sub.sid)
        cache.delete_memoized(getMetadata, sub, 'xmod2', all=True)
        return json.dumps({'status': 'ok', 'msg': 'user demodded'})
    else:
        abort(403)


@do.route("/do/revoke_mod2inv/<sub>/<user>", methods=['POST'])
@login_required
def revoke_mod2inv(sub, user):
    """ revoke Mod2 inv """
    user = User.query.filter(func.lower(User.name) == func.lower(user)).first()
    sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
    if current_user.is_topmod(sub) or current_user.is_admin():
        inv = SubMetadata.query.filter_by(key='mod2i') \
                               .filter_by(value=user.uid).first()
        inv.key = 'xmod2i'
        log = SubLog(sub.sid)
        log.action = 6  # 6 mod action
        log.desc = current_user.get_username() + ' canceled ' + user.name + \
            ' mod invite'
        log.link = url_for('edit_sub_mods', sub=sub.name)
        db.session.add(log)
        db.session.commit()

        SubMetadata.cache.uncache(key='mod2i', sid=sub.sid)
        cache.delete_memoized(getMetadata, sub, 'mod2i', all=True)
        SubMetadata.cache.uncache(key='xmod2i', sid=sub.sid)
        cache.delete_memoized(getMetadata, sub, 'xmod2i', all=True)
        return json.dumps({'status': 'ok', 'msg': 'user invite revoked'})
    else:
        abort(403)


@do.route("/do/accept_mod2inv/<sub>/<user>", methods=['POST'])
@login_required
def accept_mod2inv(sub, user):
    """ Accept mod invite """
    user = User.query.filter(func.lower(User.name) == func.lower(user)).first()
    if user.uid != current_user.get_id():
        abort(403)
    sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
    inv = SubMetadata.query.filter_by(key='mod2i') \
                           .filter_by(value=user.uid).first()
    if inv:
        if misc.moddedSubCount(user.uid) >= 15:
            return json.dumps({'status': 'error',
                               'error': ["You can't mod more than 15 subs"]})
        inv.key = 'mod2'
        log = SubLog(sub.sid)
        log.action = 6  # 6 mod action
        log.desc = user.name + ' accepted mod invite'
        log.link = url_for('edit_sub_mods', sub=sub.name)
        db.session.add(log)

        su = SubSubscriber.query.filter_by(sid=sub.sid, uid=user.uid, status=1)
        if not su.first():
            x = SubSubscriber(sub.sid, user.uid, 1)
            db.session.add(x)
        db.session.commit()

        SubMetadata.cache.uncache(key='mod2i', sid=sub.sid)
        cache.delete_memoized(getMetadata, sub, 'mod2i', all=True)
        SubMetadata.cache.uncache(key='mod2', sid=sub.sid)
        cache.delete_memoized(getMetadata, sub, 'mod2', all=True)
        return json.dumps({'status': 'ok', 'msg': 'user modded'})
    else:
        abort(404)


@do.route("/do/refuse_mod2inv/<sub>/<user>", methods=['POST'])
@login_required
def refuse_mod2inv(sub, user):
    """ refuse Mod2 """
    user = User.query.filter(func.lower(User.name) == func.lower(user)).first()
    sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
    inv = SubMetadata.query.filter_by(key='mod2i') \
                           .filter_by(value=user.uid).first()
    if inv:
        inv.key = 'xmod2i'
        log = SubLog(sub.sid)
        log.action = 6  # 6 mod action
        log.desc = user.name + ' rejected mod invite'
        log.link = url_for('edit_sub_mods', sub=sub.name)
        db.session.add(log)
        db.session.commit()

        SubMetadata.cache.uncache(key='mod2i', sid=sub.sid)
        cache.delete_memoized(getMetadata, sub, 'mod2i', all=True)
        SubMetadata.cache.uncache(key='xmod2i', sid=sub.sid)
        cache.delete_memoized(getMetadata, sub, 'xmod2i', all=True)
        return json.dumps({'status': 'ok', 'msg': 'invite refused'})
    else:
        abort(404)


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
    else:
        abort(403)


@do.route("/do/delete_pm/<mid>", methods=['POST'])
@login_required
def delete_pm(mid):
    """ Delete PM """
    message = Message.query.filter_by(mid=mid).first()
    if session['user_id'] == message.receivedby:
        message.mtype = 6  # deleted
        db.session.commit()
        return json.dumps({'status': 'ok', 'mid': mid})
    else:
        abort(403)


@do.route("/do/admin/deleteannouncement")
def deleteannouncement():
    """ Removes the current announcement """
    if not current_user.is_admin():
        abort(404)

    ann = SiteMetadata.query.filter_by(key='announcement').first()
    db.session.delete(ann)
    db.session.commit()
    return redirect(url_for('admin_area'))


@do.route("/do/makeannouncement", methods=['POST'])
def make_announcement():
    """ Flagging post as announcement - not api """
    if not current_user.is_admin():
        abort(404)

    form = DeletePost()

    if form.validate():
        ann = SiteMetadata.query.filter_by(key='announcement').first()
        if not ann:
            ann = SiteMetadata()
            ann.key = 'announcement'
            db.session.add(ann)
        ann.value = form.post.data
        db.session.commit()

    return redirect(url_for('index'))


@do.route("/do/usebtcdonation", methods=['POST'])
def use_btc_donation():
    """ Enable bitcoin donation module """
    if not current_user.is_admin():
        abort(404)

    form = UseBTCdonationForm()

    if form.validate():
        usebtc = SiteMetadata.query.filter_by(key='usebtc').first()
        btcaddress = SiteMetadata.query.filter_by(key='btcaddr').first()
        btcmessage = SiteMetadata.query.filter_by(key='btcmsg').first()
        if not usebtc:
            usebtc = SiteMetadata()
            usebtc.key = 'usebtc'
            usebtc.value = form.enablebtcmod.data
            db.session.add(usebtc)
        else:
            usebtc.value = form.enablebtcmod.data

        if not btcaddress:
            btcaddr = SiteMetadata()
            btcaddr.key = 'btcaddr'
            btcaddr.value = form.btcaddress.data
            db.session.add(btcaddr)
        else:
            btcaddress.value = form.btcaddress.data

        if not btcmessage:
            btcmsg = SiteMetadata()
            btcmsg.key = 'btcmsg'
            btcmsg.value = form.message.data
            db.session.add(btcmsg)
        else:
            btcmessage.value = form.message.data

        alog = SiteLog()
        alog.action = 10  # money realated!
        alog.time = datetime.datetime.utcnow()
        if form.enablebtcmod.data:
            alog.desc = current_user.get_username() + \
                        ' enabled btc donations: ' + form.btcaddress.data
        else:
            alog.desc = current_user.get_username() + \
                        ' disabled btc donations'
        alog.link = url_for('admin_area')
        db.session.add(alog)
        db.session.commit()
        return json.dumps({'status': 'ok'})
    return redirect(url_for('admin_area'))


@do.route("/do/stick/<int:post>", methods=['POST'])
def toggle_sticky(post):
    """ Toggles post stickyness - not api """
    post = SubPost.query.filter_by(pid=post).first()

    if not current_user.is_mod(post.sub) or not current_user.is_admin():
        abort(403)

    form = DeletePost()

    if form.validate():
        md = SubMetadata.query.filter_by(key='sticky').first()
        if not md:
            md = SubMetadata(post.sub, 'sticky', post.pid)
            log = SubLog(post.sub.sid)
            log.action = 4  # sub action
            log.desc = current_user.get_username() + ' stickied: ' + post.title
            log.link = url_for('view_post', sub=post.sub.name, pid=post.pid)
            db.session.add(log)
            db.session.add(md)
        else:
            log = SubLog(post.sub.sid)
            log.action = 4  # sub action
            log.desc = current_user.get_username() + ' removed stickied: ' + \
                post.title
            log.link = url_for('view_post', sub=post.sub.name, pid=post.pid)
            db.session.add(log)
            db.session.delete(md)
        db.session.commit()
        SubMetadata.cache.uncache(key='sticky', sid=post.sid, value=post.pid)
        cache.delete_memoized(getMetadata, post.sub, 'sticky')
        ckey = make_template_fragment_key('sticky', vary_on=[post.sub.sid])
        cache.delete(ckey)
        ckey = make_template_fragment_key('subposts', vary_on=[post.sub.sid])
        cache.delete(ckey)

    return redirect(url_for('view_sub', sub=post.sub.name))


@do.route("/do/flair/<sub>/edit", methods=['POST'])
@login_required
def edit_flair(sub):
    """ Edits flairs (from edit flair page) """
    sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
    if not sub:
        abort(404)

    if not current_user.is_topmod(sub) and not current_user.is_admin():
        abort(403)

    form = EditSubFlair()
    if form.validate():
        flair = SubFlair.query.filter_by(sid=sub.sid,
                                         xid=form.flair.data).first()
        if not flair:
            return json.dumps({'status': 'error',
                               'error': ['Flair does not exist']})

        flair.text = form.text.data
        db.session.commit()
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/flair/<sub>/delete", methods=['POST'])
@login_required
def delete_flair(sub):
    """ Removes a flair (from edit flair page) """
    sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
    if not sub:
        abort(404)

    if not current_user.is_topmod(sub) and not current_user.is_admin():
        abort(403)

    form = DeleteSubFlair()
    if form.validate():
        flair = SubFlair.query.filter_by(sid=sub.sid,
                                         xid=form.flair.data).first()
        if not flair:
            return json.dumps({'status': 'error',
                               'error': ['Flair does not exist']})

        db.session.delete(flair)
        db.session.commit()
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/flair/<sub>/create", methods=['POST'])
@login_required
def create_flair(sub):
    """ Creates a new flair (from edit flair page) """
    sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
    if not sub:
        abort(404)

    if not current_user.is_topmod(sub) and not current_user.is_admin():
        abort(403)
    form = CreateSubFlair()
    if form.validate():
        flair = SubFlair()
        flair.sid = sub.sid
        flair.text = form.text.data
        db.session.add(flair)
        db.session.commit()
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/recovery", methods=['POST'])
def recovery():
    """ Password recovery page. Email+captcha and sends recovery email """
    if current_user.is_authenticated:
        abort(403)

    form = forms.PasswordRecoveryForm()
    if form.validate():
        user = User.query.filter_by(email=form.email.data).first()
        if not user:
            return json.dumps({'status': 'ok'})

        # User exists, check if they don't already have a key sent
        key = getMetadata(user, 'recovery-key', record=True)
        if key:
            # Key exists, check if it has expired
            keyExp = getMetadata(user, 'recovery-key-time', record=True)
            expiration = float(keyExp.value)
            if (time.time() - expiration) > 86400:  # 1 day
                # Key is old. remove it and proceed
                db.session.delete(key)
                db.session.delete(keyExp)
            else:
                # silently fail >_>
                return json.dumps({'status': 'ok'})

        # checks done, doing the stuff.
        key = UserMetadata(user.uid, 'recovery-key', uuid.uuid4())
        keyExp = UserMetadata(user.uid, 'recovery-key-time', time.time())
        db.session.add(key)
        db.session.add(keyExp)
        db.session.commit()
        sendMail(
            subject='Password recovery',
            to=user.email,
            content="""<h1><strong>{0}</strong></h1>
            <p>Somebody (most likely you) has requested a password reset for
            your account</p>
            <p>To proceed, visit the following address</p>
            <a href="{1}">{1}</a>
            <hr>
            <p>If you didn't request a password recovery, please ignore this
            email</p>
            """.format(config.LEMA, url_for('password_reset', key=key.value,
                                            uid=user.uid, _external=True))
        )
        cache.delete_memoized(getMetadata, user, 'recovery-key', record=True)
        cache.delete_memoized(getMetadata, user, 'recovery-key-time',
                              record=True)
        UserMetadata.cache.uncache(key='recovery-key', uid=user.uid)
        UserMetadata.cache.uncache(key='recovery-key-time', uid=user.uid)

        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/reset", methods=['POST'])
def reset():
    """ Password reset. Takes key and uid and changes password """
    if current_user.is_authenticated:
        abort(403)

    form = forms.PasswordResetForm()
    if form.validate():
        user = User.query.get(form.user.data)
        if not user:
            return json.dumps({'status': 'ok'})

        # User exists, check if they don't already have a key sent
        key = getMetadata(user, 'recovery-key', record=True)
        keyExp = getMetadata(user, 'recovery-key-time', record=True)
        if not key:
            abort(403)

        if key.value != form.key.data:
            abort(403)

        db.session.delete(key)
        db.session.delete(keyExp)
        db.session.commit()
        cache.delete_memoized(getMetadata, user, 'recovery-key', record=True)
        cache.delete_memoized(getMetadata, user, 'recovery-key-time',
                              record=True)
        UserMetadata.cache.uncache(key='recovery-key', uid=user.uid)
        UserMetadata.cache.uncache(key='recovery-key-time', uid=user.uid)

        # All good. Set da password.
        user.setPassword(form.password.data)
        db.session.commit()
        login_user(SiteUser(user))
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/edit_comment", methods=['POST'])
@login_required
def edit_comment():
    """ Edits a comment """
    form = forms.EditCommentForm()
    if form.validate():
        comment = SubPostComment.query.get(form.cid.data)
        if not comment:
            abort(404)

        if comment.uid != current_user.get_id() and not \
                current_user.is_admin():
            abort(403)

        comment.content = form.text.data
        comment.lastedit = datetime.datetime.utcnow()
        db.session.commit()
        SubPostComment.cache.uncache(pid=comment.pid, parentcid=None)
        SubPostComment.cache.uncache(pid=comment.pid,
                                     parentcid=comment.parentcid)
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/delete_comment", methods=['POST'])
@login_required
def delete_comment():
    """ Edits a comment """
    form = forms.DeleteCommentForm()
    if form.validate():
        comment = SubPostComment.query.get(form.cid.data)
        if not comment:
            abort(404)

        if comment.uid != current_user.get_id() and not \
                current_user.is_admin():
            abort(403)

        comment.status = 1
        db.session.commit()
        SubPostComment.cache.uncache(pid=comment.pid, parentcid=None)
        SubPostComment.cache.uncache(pid=comment.pid,
                                     parentcid=comment.parentcid)
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route('/do/votecomment/<cid>/<value>', methods=['POST'])
@login_required
def upvotecomment(cid, value):
    """ Logs an upvote to a post. """
    if value == "up":
        voteValue = 1
    elif value == "down":
        voteValue = -1
    else:
        abort(403)
    comment = SubPostComment.query.filter_by(cid=cid).first()
    if not comment:
        return json.dumps({'status': 'error',
                           'error': ['Comment does not exist']})

    if comment.uid == current_user.get_id():
        return json.dumps({'status': 'error',
                           'error': ['You can\'t vote on your own comments']})

    qvote = SubPostCommentVote.query.filter_by(cid=cid) \
                                    .filter_by(uid=current_user.get_id()) \
                                    .first()

    if not comment.score:
        comment.score = 0

    if qvote:
        if qvote.positive == (True if voteValue == 1 else False):
            return json.dumps({'status': 'error',
                               'error': ['You already voted.']})
        else:

            qvote.positive = True if voteValue == 1 else False
            comment.score = int(comment.score) + (voteValue*2)
            db.session.commit()
            return json.dumps({'status': 'ok',
                               'message': 'Vote flipped.'})
    else:
        vote = SubPostCommentVote()
        vote.cid = cid
        vote.uid = current_user.get_id()
        vote.positive = True if voteValue == 1 else False
        db.session.add(vote)

    comment.score = int(comment.score) + voteValue
    db.session.commit()
    return json.dumps({'status': 'ok'})
