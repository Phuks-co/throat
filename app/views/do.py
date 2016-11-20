""" /do/ views (AJAX stuff) """

import json
import re
import datetime
import bcrypt
from flask import Blueprint, redirect, url_for, session, abort
from sqlalchemy import func
from flask_login import login_user, login_required, logout_user, current_user
from flask_cache import make_template_fragment_key
from ..models import db, User, Sub, SubPost, Message, SubPostComment
from ..models import SubPostVote, SubMetadata, SubPostMetadata, SubStylesheet
from ..models import UserMetadata, UserBadge, SubSubscriber, SiteMetadata
from ..forms import RegistrationForm, LoginForm, LogOutForm
from ..forms import CreateSubForm, EditSubForm, EditUserForm, EditSubCSSForm
from ..forms import CreateUserBadgeForm, EditModForm, BanUserSubForm
from ..forms import CreateSubTextPost, CreateSubLinkPost, EditSubTextPostForm
from ..forms import PostComment, CreateUserMessageForm, DeletePost
from ..forms import EditSubLinkPostForm, SearchForm, EditMod2Form
from ..misc import SiteUser, cache, getMetadata

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
    if current_user.get_id() != user.uid or not current_user.is_admin():
        abort(403)

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

        if post.uid == session['user_id']:
            md = SubPostMetadata(post.pid, 'deleted', '1')
            cache.delete_memoized(getMetadata, post, 'deleted')
        else:
            md = SubPostMetadata(post.pid, 'moddeleted', '1')
            cache.delete_memoized(getMetadata, post, 'moddeleted')

        ckey = make_template_fragment_key('subposts', vary_on=[post.sub.sid])
        cache.delete(ckey)
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

    form = EditSubCSSForm()
    if form.validate():
        if sub.stylesheet.first():
            sub.stylesheet.first().content = form.css.data
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
            nsfw = sub.properties.filter_by(key='nsfw').first()
            if nsfw:
                nsfw.value = form.nsfw.data
            else:
                nsfw = SubMetadata(sub, 'nsfw', form.nsfw.data)
                db.session.add(nsfw)
            restricted = sub.properties.filter_by(key='restricted').first()
            if restricted:
                restricted.value = form.restricted.data
            else:
                restricted = SubMetadata(sub, 'restricted',
                                         form.restricted.data)
                db.session.add(restricted)
            usercanflair = sub.properties.filter_by(key='ucf').first()
            if usercanflair:
                usercanflair.value = form.usercanflair.data
            else:
                usercanflair = SubMetadata(sub, 'ucf', form.usercanflair.data)
                db.session.add(usercanflair)
            if form.subsort.data != "None":
                subsort = sub.properties.filter_by(key='sort').first()
                if subsort:
                    subsort.value = form.subsort.data
                else:
                    subsort = SubMetadata(sub, 'sort', form.subsort.data)
                    db.session.add(subsort)

            if form.flair1.data:
                flair1 = sub.properties.filter_by(key='fl1').first()
                if flair1:
                    flair1.value = form.flair1.data
                else:
                    flair1 = SubMetadata(sub, 'fl1', form.flair1.data)
                    db.session.add(flair1)
            if form.flair2.data:
                flair2 = sub.properties.filter_by(key='fl2').first()
                if flair2:
                    flair2.value = form.flair2.data
                else:
                    flair2 = SubMetadata(sub, 'fl2', form.flair2.data)
                    db.session.add(flair2)
            if form.flair3.data:
                flair3 = sub.properties.filter_by(key='fl3').first()
                if flair3:
                    flair3.value = form.flair3.data
                else:
                    flair3 = SubMetadata(sub, 'fl3', form.flair3.data)
                    db.session.add(flair3)
            if form.flair4.data:
                flair4 = sub.properties.filter_by(key='fl4').first()
                if flair4:
                    flair4.value = form.flair4.data
                else:
                    flair4 = SubMetadata(sub, 'fl4', form.flair4.data)
                    db.session.add(flair4)
            if form.flair5.data:
                flair5 = sub.properties.filter_by(key='fl5').first()
                if flair5:
                    flair5.value = form.flair5.data
                else:
                    flair5 = SubMetadata(sub, 'fl5', form.flair5.data)
                    db.session.add(flair5)
            if form.flair6.data:
                flair6 = sub.properties.filter_by(key='fl6').first()
                if flair6:
                    flair6.value = form.flair6.data
                else:
                    flair6 = SubMetadata(sub, 'fl6', form.flair6.data)
                    db.session.add(flair6)
            if form.flair7.data:
                flair7 = sub.properties.filter_by(key='fl7').first()
                if flair7:
                    flair7.value = form.flair7.data
                else:
                    flair7 = SubMetadata(sub, 'fl7', form.flair7.data)
                    db.session.add(flair7)
            if form.flair8.data:
                flair8 = sub.properties.filter_by(key='fl8').first()
                if flair8:
                    flair8.value = form.flair8.data
                else:
                    flair8 = SubMetadata(sub, 'fl8', form.flair8.data)
                    db.session.add(flair8)
            db.session.commit()
            return json.dumps({'status': 'ok',
                               'addr': url_for('view_sub', sub=sub.name)})
        return json.dumps({'status': 'error', 'error': get_errors(form)})
    else:
        abort(403)


@do.route("/do/delete_sub_flair/<sub>/<fl>", methods=['POST'])
def delete_sub_flair(sub, fl):
    """ Deletes a sub flair """
    sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
    if not sub:
        return json.dumps({'status': 'error',
                           'error': ['Sub does not exist']})
    if current_user.is_mod(sub) or current_user.is_admin():
        flair = sub.properties.filter_by(key=fl).first()
        db.session.delete(flair)
        db.session.commit()
        return json.dumps({'status': 'ok'})
    else:
        abort(404)


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
        flair = sub.properties.filter_by(key=fl).first()
        postfl = post.properties.filter_by(key='flair').first()
        if postfl:
            postfl.value = flair.value
        else:
            x = SubPostMetadata(pid, 'flair', flair.value)
            db.session.add(x)
        db.session.commit()
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
        postfl = post.properties.filter_by(key='flair').first()
        if not postfl:
            return json.dumps({'status': 'error',
                               'error': ['Flair does not exist']})
        else:
            db.session.delete(postfl)
        db.session.commit()
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

    xvotes = getMetadata(post, 'score', record=True)
    if not xvotes:
        print("WHYYYYYYYYYYYYYYYYYYYYYYYYYY")
        xvotes = SubPostMetadata(post.pid, 'score', 1)
        db.session.add(xvotes)
        cache.delete_memoized(getMetadata, post, 'score', record=True)
        SubPostMetadata.cache.uncache(key='score', pid=post.pid)

    if qvote:
        if qvote.positive:
            return json.dumps({'status': 'error',
                               'error': ['You already voted.']})
        else:

            qvote.positive = True
            xvotes.value = int(xvotes.value) + 2
            db.session.commit()
            return json.dumps({'status': 'ok',
                               'message': 'Negative vote reverted.'})
    else:
        vote = SubPostVote()
        vote.pid = pid
        vote.uid = current_user.get_id()
        vote.positive = True
        db.session.add(vote)

    xvotes.value = int(xvotes.value) + 1
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

    xvotes = getMetadata(post, 'score', record=True)
    if not xvotes:
        xvotes = SubPostMetadata(post.pid, 'score', 1)
        db.session.add(xvotes)
        cache.delete_memoized(getMetadata, post, 'score', record=True)
        SubPostMetadata.cache.uncache(key='score', pid=post.pid)


    if qvote:
        if not qvote.positive:
            return json.dumps({'status': 'error',
                               'error': ['You already voted.']})
        else:
            qvote.positive = False
            xvotes.value = int(xvotes.value) - 2
            db.session.commit()
            return json.dumps({'status': 'ok',
                               'message': 'Positive vote reverted.'})
    else:
        vote = SubPostVote()
        vote.pid = pid
        vote.uid = current_user.get_id()
        vote.positive = False
        db.session.add(vote)
    xvotes.value = int(xvotes.value) - 1
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
        if current_user.get_id() != post.uid:
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
        bq = UserMetadata.query.filter_by(uid=uid, key='badge', value=bid)
        if bq.first():
            return json.dumps({'status': 'error',
                               'error': ['Badge is already assigned']})

        badge = UserMetadata()
        badge.uid = uid
        badge.key = 'badge'
        badge.value = bid
        db.session.add(badge)
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
        db.session.commit()
        return json.dumps({'status': 'ok', 'message': 'Badge deleted'})
    else:
        abort(403)


@do.route("/do/sendmsg/<user>", methods=['POST'])
@login_required
def create_sendmsg(user):
    """ User PM message creation endpoint """
    form = CreateUserMessageForm()
    if form.validate():
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
            meta = SubMetadata(sub, 'ban', user.uid)
            db.session.add(msg)
            db.session.add(meta)
            db.session.commit()
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
            msg = Message()
            msg.receivedby = user.uid
            msg.sentby = current_user.get_id()
            msg.subject = sub.name
            # msg.content = 'Mod inviteinvite'
            msg.posted = datetime.datetime.utcnow()
            msg.mtype = '0'
            meta = SubMetadata(sub, 'mod2i', user.uid)
            db.session.add(msg)
            db.session.add(meta)
            db.session.commit()
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
        inv = sub.properties.filter_by(key='ban') \
                            .filter_by(value=user.uid).first()
        inv.key = 'xban'
        db.session.commit()
        return json.dumps({'status': 'ok', 'msg': 'user demodded'})
    else:
        abort(403)


@do.route("/do/remove_mod2/<sub>/<user>", methods=['POST'])
@login_required
def remove_mod2(sub, user):
    """ Remove Mod2 """
    user = User.query.filter(func.lower(User.name) == func.lower(user)).first()
    sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
    if current_user.is_topmod(sub) or current_user.is_admin():
        inv = sub.properties.filter_by(key='mod2') \
                            .filter_by(value=user.uid).first()
        inv.key = 'xmod2'
        db.session.commit()
        return json.dumps({'status': 'ok', 'msg': 'user demodded'})
    else:
        abort(403)


@do.route("/do/revoke_mod2inv/<sub>/<user>", methods=['POST'])
@login_required
def revoke_mod2inv(sub, user):
    """ Remove Mod2 """
    user = User.query.filter(func.lower(User.name) == func.lower(user)).first()
    sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
    if current_user.is_topmod(sub) or current_user.is_admin():
        inv = sub.properties.filter_by(key='mod2i') \
                                   .filter_by(value=user.uid).first()
        inv.key = 'xmod2i'
        db.session.commit()
        return json.dumps({'status': 'ok', 'msg': 'user invite revoked'})
    else:
        abort(403)


@do.route("/do/accept_mod2inv/<sub>/<user>", methods=['POST'])
@login_required
def accept_mod2inv(sub, user):
    """ Remove Mod2 """
    user = User.query.filter(func.lower(User.name) == func.lower(user)).first()
    sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
    inv = sub.properties.filter_by(key='mod2i') \
                        .filter_by(value=user.uid).first()
    if inv:
        inv.key = 'mod2'
        db.session.commit()
        return json.dumps({'status': 'ok', 'msg': 'user modded'})
    else:
        abort(404)


@do.route("/do/refuse_mod2inv/<sub>/<user>", methods=['POST'])
@login_required
def refuse_mod2inv(sub, user):
    """ refuse Mod2 """
    user = User.query.filter(func.lower(User.name) == func.lower(user)).first()
    sub = Sub.query.filter(func.lower(Sub.name) == func.lower(sub)).first()
    inv = sub.properties.filter_by(key='mod2i') \
                        .filter_by(value=user.uid).first()
    if inv:
        inv.key = 'xmod2i'
        db.session.commit()
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
        message.mtype = '-1'
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


@do.route("/do/stick/<int:post>", methods=['POST'])
def toggle_sticky(post):
    """ Toggles post stickyness - not api """
    post = SubPost.query.filter_by(pid=post).first()

    if not post or not current_user.is_mod(post.sub) \
        or not current_user.is_admin():
        abort(403)

    form = DeletePost()

    if form.validate():
        md = SubMetadata.query.filter_by(key='sticky').first()
        if not md:
            md = SubMetadata(post.sub, 'sticky', post.pid)
            db.session.add(md)
        else:
            db.session.delete(md)
        db.session.commit()
        SubMetadata.cache.uncache(key='sticky', sid=post.sid, value=post.pid)
        cache.delete_memoized(getMetadata, post.sub, 'sticky')
        ckey = make_template_fragment_key('sticky', vary_on=[post.sub.sid])
        cache.delete(ckey)
        ckey = make_template_fragment_key('subposts', vary_on=[post.sub.sid])
        cache.delete(ckey)

    return redirect(url_for('view_sub', sub=post.sub.name))
