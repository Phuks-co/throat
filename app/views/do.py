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
from flask import Blueprint, redirect, url_for, session, abort, jsonify
# from sqlalchemy import func, or_, and_
from flask_login import login_user, login_required, logout_user, current_user
from flask_cache import make_template_fragment_key
import config
from .. import forms, misc
from .. import database as db
# from ..models import db, User, Sub, SubPost, Message, SubPostComment
# from ..models import SubPostVote, SubMetadata, SubPostMetadata, SubStylesheet
# from ..models import UserMetadata, UserBadge, SubSubscriber, SiteMetadata
# from ..models import SubFlair, SubLog, SiteLog, SubPostCommentVote
from ..forms import RegistrationForm, LoginForm, LogOutForm, CreateSubFlair
from ..forms import CreateSubForm, EditSubForm, EditUserForm, EditSubCSSForm
from ..forms import CreateUserBadgeForm, EditModForm, BanUserSubForm
from ..forms import CreateSubTextPost, CreateSubLinkPost, EditSubTextPostForm
from ..forms import PostComment, CreateUserMessageForm, DeletePost
from ..forms import EditSubLinkPostForm, SearchForm, EditMod2Form, EditSubFlair
from ..forms import DeleteSubFlair, UseBTCdonationForm
from ..misc import SiteUser, cache, sendMail, getDefaultSubs

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
        user = db.get_user_from_name(form.username.data)
        if not user:
            return json.dumps({'status': 'error',
                               'error': ['User does not exist.']})

        if user['crypto'] == 1:  # bcrypt
            thash = bcrypt.hashpw(form.password.data.encode('utf-8'),
                                  user['password'].encode('utf-8'))
            if thash == user['password'].encode('utf-8'):
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
        if db.get_user_from_name(form.username.data):
            return json.dumps({'status': 'error',
                               'error': ['Username is already registered.']})
        x = db.query('SELECT `uid` FROM `user` WHERE `email`=%s',
                     (form.email.data,))
        if x.fetchone() and form.email.data != '':
            return json.dumps({'status': 'error',
                               'error': ['Email is alredy in use.']})

        user = db.create_user(form.username.data, form.email.data,
                              form.password.data)
        # defaults
        defaults = getDefaultSubs()
        for d in defaults:
            db.create_subscription(user['uid'], d['sid'], 1)

        login_user(SiteUser(user))
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/edit_user/<user>", methods=['POST'])
@login_required
def edit_user(user):
    """ Edit user endpoint """
    user = db.get_user_from_name(user)
    if not user:
        return json.dumps({'status': 'error',
                           'error': ['User does not exist']})
    if current_user.get_id() != user['uid'] and not current_user.is_admin():
        abort(403)

    form = EditUserForm()
    if form.validate():
        if not db.is_password_valid(user['uid'], form.oldpassword.data):
            return json.dumps({'status': 'error', 'error': ['Wrong password']})

        db.uquery('UPDATE `user` SET `email`=%s WHERE `uid`=%s',
                  (form.email.data, user['uid']))
        if form.password.data:
            db.update_user_password(form.password.data)

        db.update_user_metadata(user['uid'], 'exlinks',
                                form.external_links.data)

        db.update_user_metadata(user['uid'], 'nostyles',
                                form.disable_sub_style.data)

        db.update_user_metadata(user['uid'], 'nsfw',
                                form.show_nsfw.data)

        return json.dumps({'status': 'ok',
                           'addr': url_for('view_user', user=user['name'])})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/delete_post", methods=['POST'])
@login_required
def delete_post():
    """ Post deletion endpoint """
    form = DeletePost()

    if form.validate():
        post = db.get_post_from_pid(form.post.data)
        if not post:
            return json.dumps({'status': 'error',
                               'error': ['Post does not exist.']})
        sub = db.get_sub_from_sid(post['sid'])
        if not current_user.is_mod(sub) and not current_user.is_admin() \
           and not post['uid'] == current_user.get_id():
            return json.dumps({'status': 'error',
                               'error': ['Not authorized.']})

        if post['uid'] == session['user_id']:
            deletion = 1
        else:
            deletion = 2

        if not current_user.is_mod(sub) and current_user.is_admin() \
           and not post['uid'] == current_user.get_id():
            db.create_sitelog(4, current_user.get_username() +
                              ' deleted a post',
                              url_for('view_sub', sud=sub['sid']))
        db.uquery('UPDATE `sub_post` SET `deleted`=%s WHERE pid=%s',
                  (deletion, post['pid']))

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

        if db.get_sub_from_name(form.subname.data):
            return json.dumps({'status': 'error',
                               'error': ['Sub is already registered.']})

        if misc.moddedSubCount(current_user.get_id()) >= 15:
            return json.dumps({'status': 'error',
                               'error': ["You can't mod more than 15 subs."]})

        sub = db.create_sub(current_user.get_id(), form.subname.data,
                            form.title.data)

        # admin/site log
        db.create_sitelog(6,
                          current_user.get_username() + ' created a new sub',
                          url_for('view_sub', sub=sub['name']))

        db.create_subscription(current_user.get_id(), sub['sid'], 1)

        return json.dumps({'status': 'ok',
                           'addr': url_for('view_sub', sub=form.subname.data)})

    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/edit_sub_css/<sub>", methods=['POST'])
@login_required
def edit_sub_css(sub):
    """ Edit sub endpoint """
    sub = db.get_sub_from_name(sub)
    if not sub:
        return json.dumps({'status': 'error',
                           'error': ['Sub does not exist']})
    if not current_user.is_mod(sub) and not current_user.is_admin():
        abort(403)

    form = EditSubCSSForm()
    if form.validate():
        db.uquery('UPDATE `sub_stylesheet` SET `content`=%s WHERE `sid`=%s',
                  (form.css.data, sub['sid']))
        db.create_sublog(sub['sid'], 4,
                          'CSS edited by ' + current_user.get_username())

        return json.dumps({'status': 'ok',
                           'addr': url_for('view_sub', sub=sub['name'])})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/edit_sub/<sub>", methods=['POST'])
@login_required
def edit_sub(sub):
    """ Edit sub endpoint """
    sub = db.get_sub_from_name(sub)
    if not sub:
        return json.dumps({'status': 'error',
                           'error': ['Sub does not exist']})
    if current_user.is_mod(sub) or current_user.is_admin():
        form = EditSubForm()
        if form.validate():
            db.uquery('UPDATE `sub` SET `title`=%s, `sidebar`=%s, `nsfw`=%s '
                      'WHERE `sid`=%s', (form.title.data, form.sidebar.data,
                                         form.nsfw.data, sub['sid']))
            db.update_sub_metadata(sub['sid'], 'restricted',
                                   form.restricted.data)
            db.update_sub_metadata(sub['sid'], 'ucf', form.usercanflair.data)
            db.update_sub_metadata(sub['sid'], 'videomode',
                                   form.videomode.data)

            if form.subsort.data != "None":
                db.update_sub_metadata(sub['sid'], 'sort',
                                       form.subsort.data)

            db.create_sublog(sub['sid'], 4, 'Sub settings edited by ' +
                             current_user.get_username())

            if not current_user.is_mod(sub) and current_user.is_admin():
                db.create_sitelog(4, 'Sub settings edited by ' +
                                  current_user.get_username(),
                                  url_for('view_sub', sub=sub['name']))

            return json.dumps({'status': 'ok',
                               'addr': url_for('view_sub', sub=sub['name'])})
        return json.dumps({'status': 'error', 'error': get_errors(form)})
    else:
        abort(403)


@do.route("/do/assign_post_flair/<sub>/<pid>/<fl>", methods=['POST'])
def assign_post_flair(sub, pid, fl):
    """ Assign a post's flair """
    sub = db.get_sub_from_name(sub)
    if not sub:
        return json.dumps({'status': 'error',
                           'error': ['Sub does not exist']})
    post = db.get_post_from_pid(pid)
    if not post:
        return json.dumps({'status': 'error',
                           'error': ['Post does not exist']})
    if current_user.is_mod(sub) or post['uid'] == current_user.get_id() \
       or current_user.is_admin():
        flair = db.query('SELECT * FROM `sub_flair` WHERE `xid`=%s AND '
                         '`sid`=%s', (fl, sub['sid'])).fetchone()
        if not flair:
            return json.dumps({'status': 'error',
                               'error': ['Flair does not exist']})

        db.update_post_metadata(post['pid'], 'flair', flair['text'])
        db.create_sublog(sub['sid'], 3, current_user.get_username() +
                         ' assigned post flair',
                         url_for('view_post', sub=sub['name'],
                                 pid=post['pid']))

        if not current_user.is_mod(sub) and current_user.is_admin():
            db.create_sitelog(4, current_user.get_username() +
                              ' assigned post flair',
                              url_for('view_post', sub=sub['name'],
                                      pid=post['pid']))

        return json.dumps({'status': 'ok'})
    else:
        abort(403)


@do.route("/do/remove_post_flair/<sub>/<pid>", methods=['POST'])
def remove_post_flair(sub, pid):
    """ Deletes a post's flair """
    sub = db.get_sub_from_name(sub)
    if not sub:
        return json.dumps({'status': 'error',
                           'error': ['Sub does not exist']})
    post = db.get_post_from_pid(pid)
    if not post:
        return json.dumps({'status': 'error',
                           'error': ['Post does not exist']})
    if current_user.is_mod(sub) or post['uid'] == current_user.get_id() \
       or current_user.is_admin():
        postfl = misc.getPostFlair(post)
        if not postfl:
            return json.dumps({'status': 'error',
                               'error': ['Flair does not exist']})
        else:
            db.uquery('DELETE FROM `sub_post_metadata` WHERE `pid`=%s AND '
                      '`key`=%s', (post['pid'], 'flair'))
            db.create_sublog(sub['sid'], 3, current_user.get_username() +
                             ' removed post flair',
                             url_for('view_post', sub=sub['name'], pid=pid))

            if not current_user.is_mod(sub) and current_user.is_admin():
                db.create_sitelog(4, current_user.get_username() +
                                  ' removed post flair',
                                  url_for('view_post', sub=sub['name'],
                                          pid=pid))
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
    sub = db.get_sub_from_name(form.sub.data)
    if not sub:
        return json.dumps({'status': 'error',
                           'error': ['Sub does not exist']})
    user = db.get_user_from_name(form.user.data)
    if not user:
        return json.dumps({'status': 'error',
                           'error': ['User does not exist']})
    if form.validate():
        db.update_sub_metadata(sub['sid'], 'mod1', user['uid'])

        db.create_sublog(sub['sid'],
                         current_user.get_username() + ' transferred sub '
                         'ownership to ' + user['name'],
                         url_for('view_sub', sub=sub['name']))
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/subscribe/<sid>", methods=['POST'])
@login_required
def subscribe_to_sub(sid):
    """ Subscribe to sub """
    userid = current_user.get_id()
    sub = db.get_sub_from_sid(sid)
    if not sub:
        return jsonify(status='error', message='sub not found')

    if current_user.has_subscribed(sid):
        return jsonify(status='ok', message='already subscribed')

    db.create_subscription(userid, sub['sid'], 1)
    if current_user.has_blocked(sid):
        db.uquery('DELETE FROM `sub_subscriber` WHERE `uid`=%s AND `sid`=%s '
                  'AND `status`=2', (userid, sid))
    return json.dumps({'status': 'ok', 'message': 'subscribed'})


@do.route("/do/unsubscribe/<sid>", methods=['POST'])
@login_required
def unsubscribe_from_sub(sid):
    """ Unsubscribe from sub """
    userid = current_user.get_id()
    sub = db.get_sub_from_sid(sid)
    if not sub:
        return jsonify(status='error', message='sub not found')

    if not current_user.has_subscribed(sid):
        return jsonify(status='ok', message='not subscribed')

    db.uquery('DELETE FROM `sub_subscriber` WHERE `uid`=%s AND `sid`=%s '
              'AND `status`=1', (userid, sid))
    return jsonify(status='ok', message='unsubscribed')


@do.route("/do/block/<sid>", methods=['POST'])
@login_required
def block_sub(sid):
    """ Block sub """
    userid = current_user.get_id()
    if current_user.has_blocked(sid):
        return json.dumps({'status': 'ok', 'message': 'already blocked'})

    db.create_subscription(userid, sid, 2)

    if current_user.has_subscribed(sid):
        db.uquery('DELETE FROM `sub_subscriber` WHERE `uid`=%s AND `sid`=%s '
                  'AND `status`=1', (userid, sid))
    return json.dumps({'status': 'ok', 'message': 'blocked'})


@do.route("/do/unblock/<sid>", methods=['POST'])
@login_required
def unblock_sub(sid):
    """ Unblock sub """
    userid = current_user.get_id()
    sub = db.get_sub_from_sid(sid)
    if not sub:
        return jsonify(status='error', message='sub not found')

    if not current_user.has_blocked(sid):
        return jsonify(status='ok', message='not blocked')

    db.uquery('DELETE FROM `sub_subscriber` WHERE `uid`=%s AND `sid`=%s '
              'AND `status`=2', (userid, sid))
    return jsonify(status='ok', message='unblocked')


@do.route("/do/txtpost", methods=['POST'])
@login_required
@misc.ratelimit(1, per=30, key_func=lambda: 'post')
def create_txtpost():
    """ Sub text post creation endpoint """

    form = CreateSubTextPost()
    if form.validate():
        # Put pre-posting checks here
        sub = db.get_sub_from_name(form.sub.data)
        if not sub:
            return json.dumps({'status': 'error',
                               'error': ['Sub does not exist']})
        if current_user.is_subban(sub):
            return json.dumps({'status': 'error',
                               'error': ['You\'re banned from posting on this'
                                         ' sub']})
        post = db.create_post(sid=sub['sid'],
                              uid=current_user.uid,
                              title=form.title.data,
                              content=form.content.data,
                              ptype=0)

        misc.workWithMentions(form.content.data, None, post, sub)
        misc.workWithMentions(form.title.data, None, post, sub)
        return jsonify(status='ok', addr=url_for('view_post', sub=sub['name'],
                                                 pid=post['pid']))
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/get_txtpost/<pid>", methods=['GET'])
def get_txtpost(pid):
    """ Sub text post expando get endpoint """
    post = db.get_post_from_pid(pid)
    if post:
        return jsonify(status='ok', content=misc.our_markdown(post['content']))
    else:
        return jsonify(status='error', error=['No longer available'])


@do.route("/do/edit_txtpost/<sub>/<pid>", methods=['POST'])
@login_required
def edit_txtpost(sub, pid):
    """ Sub text post creation endpoint """
    form = EditSubTextPostForm()
    if form.validate():
        post = db.get_post_from_pid(pid)
        if not post:
            return jsonify(status='error', error=['No such post'])
        db.uquery('UPDATE `sub_post` SET `content`=%s, `nsfw`=%s WHERE '
                  '`pid`=%s', (form.content.data, form.nsfw.data, pid))
        return json.dumps({'status': 'ok', 'sub': sub, 'pid': pid})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/lnkpost", methods=['POST'])
@login_required
@misc.ratelimit(1, per=30, key_func=lambda: 'post')
def create_lnkpost():
    """ Sub text post creation endpoint """

    form = CreateSubLinkPost()
    if form.validate():
        # Put pre-posting checks here
        sub = db.get_sub_from_name(form.sub.data)
        if not sub:
            return json.dumps({'status': 'error',
                               'error': ['Sub does not exist']})
        if current_user.is_subban(sub):
            return json.dumps({'status': 'error',
                               'error': ['You\'re banned from posting on this'
                                         ' sub']})
        l = db.query('SELECT `pid` FROM `sub_post` WHERE `sid`=%s AND '
                     '`link`=%s AND `posted` > DATE_SUB(NOW(), INTERVAL 1 '
                     'MONTH)', (sub['sid'], form.link.data)).fetchone()
        if l:
            return jsonify(status='error', error=['This link was recently '
                                                  'posted on this sub.'])
        post = db.create_post(sid=sub['sid'],
                              uid=current_user.uid,
                              title=form.title.data,
                              link=form.link.data,
                              ptype=1,
                              content='')

        misc.workWithMentions(form.title.data, None, post, sub)

        # Try to get thumbnail.
        # 1 - Check if it's an image
        try:
            req = misc.safeRequest(form.link.data)
        except (requests.exceptions.RequestException, ValueError):
            return jsonify(status='ok', addr=url_for('view_post',
                                                     sub=sub['name'],
                                                     pid=post['pid']))
        ctype = req[0].headers['content-type'].split(";")[0].lower()
        filename = str(uuid.uuid4()) + '.jpg'
        good_types = ['image/gif', 'image/jpeg', 'image/png']
        if ctype in good_types:
            # yay, it's an image!!1
            # Resize
            im = Image.open(BytesIO(req[1])).convert('RGB')
        elif ctype == 'text/html':
            # Not an image!! Let's try with OpenGraph
            og = BeautifulSoup(req[1], 'lxml')
            try:
                img = og('meta', {'property': 'og:image'})[0].get('content')
                req = misc.safeRequest(img)
            except (OSError, ValueError, IndexError):
                # no image
                return jsonify(status='ok', addr=url_for('view_post',
                                                         sub=sub['name'],
                                                         pid=post['pid']))
            im = Image.open(BytesIO(req[1])).convert('RGB')
        else:
            return jsonify(status='ok', addr=url_for('view_post',
                                                     pid=post['pid'],
                                                     sub=sub['name']))
        background = Image.new('RGB', (70, 70), (0, 0, 0))

        im.thumbnail((70, 70), Image.ANTIALIAS)

        bg_w, bg_h = background.size
        img_w, img_h = im.size
        background.paste(im, (int((bg_w - img_w) / 2),
                              int((bg_h - img_h) / 2)))
        background.save(config.THUMBNAILS + '/' + filename, "JPEG")
        db.uquery('UPDATE `sub_post` SET `thumbnail`=%s WHERE `pid`=%s',
                  (filename, post['pid']))
        im.close()
        background.close()
        return jsonify(status='ok', addr=url_for('view_post', sub=sub['name'],
                                                 pid=post['pid']))
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/edit_linkpost/<sub>/<pid>", methods=['POST'])
@login_required
def edit_linkpost(sub, pid):
    """ Sub text post creation endpoint """
    form = EditSubLinkPostForm()
    if form.validate():
        post = db.get_post_from_pid(pid)
        if not post:
            return jsonify(status='error', error=['No such post'])
        db.uquery('UPDATE `sub_post` SET `nsfw`=%s WHERE `pid`=%s',
                  (form.nsfw.data, pid))
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
    post = db.get_post_from_pid(pid)
    if not post:
        return jsonify(status='error', error=['Post does not exist'])

    if post['uid'] == current_user.get_id():
        return jsonify(status='error',
                       error=["You can't vote on your own posts"])

    qvote = db.query('SELECT * FROM `sub_post_vote` WHERE `pid`=%s AND '
                     '`uid`=%s', (pid, current_user.uid)).fetchone()
    user = db.get_user_from_uid(post['uid'])

    if qvote:
        if bool(qvote['positive']) == (True if voteValue == 1 else False):
            return json.dumps({'status': 'error',
                               'error': ['You already voted.']})
        else:
            positive = True if voteValue == 1 else False
            db.uquery('UPDATE `sub_post_vote` SET `positive`=%s WHERE '
                      '`xid`=%s', (positive, qvote['xid']))
            db.uquery('UPDATE `sub_post` SET `score`=`score`+%s WHERE '
                      '`pid`=%s', (voteValue*2, post['pid']))
            if user['score'] is not None:
                db.uquery('UPDATE `user` SET `score`=`score`+%s WHERE '
                          '`uid`=%s', (voteValue*2, post['uid']))
            return jsonify(status='ok', message='Vote flipped')
    else:
        positive = True if voteValue == 1 else False
        db.uquery('INSERT INTO `sub_post_vote` (`pid`, `uid`, `positive`) '
                  'VALUES (%s, %s, %s)', (pid, current_user.uid, positive))
    db.uquery('UPDATE `sub_post` SET `score`=`score`+%s WHERE '
              '`pid`=%s', (voteValue, post['pid']))

    if user['score'] is not None:
        db.uquery('UPDATE `user` SET `score`=`score`+%s WHERE '
                  '`uid`=%s', (voteValue, post['uid']))
    return jsonify(status='ok')


@do.route('/do/sendcomment/<sub>/<pid>', methods=['POST'])
@login_required
@misc.ratelimit(1, per=30)  # Once every 30 secs
def create_comment(sub, pid):
    """ Here we send comments. """
    form = PostComment()
    if form.validate():
        # 1 - Check if sub exists.
        sub = db.get_sub_from_name(sub)
        if not sub:
            return json.dumps({'status': 'error',
                               'error': ['Sub does not exist']})
        # 2 - Check if post exists.
        post = db.get_post_from_pid(pid)
        if not post:
            return json.dumps({'status': 'error',
                               'error': ['Post does not exist']})
        # 3 - Check if the post is in that sub.
        if not post['sid'] == sub['sid']:
            return json.dumps({'status': 'error',
                               'error': ['Post does not exist']})

        # 4 - All OK, post dem comment.
        comment = db.create_comment(pid=pid,
                                    uid=current_user.uid,
                                    content=form.comment.data.encode(),
                                    parentcid=form.parent.data)

        # 5 - send pm to parent
        if form.parent.data != "0":
            to = misc.getCommentParentUID(comment['cid'])
            subject = 'Comment reply: ' + post['title']
            mtype = 5
            cache.delete_memoized(db.get_post_comments, post['pid'],
                                  form.parent.data)
        else:
            to = post['uid']
            subject = 'Post reply: ' + post['title']
            mtype = 4
            cache.delete_memoized(db.get_post_comments, post['pid'])
            cache.delete_memoized(db.get_post_comments, post['pid'], None)
        if to != current_user.uid:
            db.create_message(mfrom=current_user.uid,
                              to=to,
                              subject=subject,
                              content='',
                              link=comment['cid'],
                              mtype=mtype)

        # 6 - Process mentions
        misc.workWithMentions(form.comment.data, to, post, sub)

        return json.dumps({'status': 'ok', 'page': url_for('view_post_inbox',
                                                           pid=pid)})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/create_user_badge", methods=['POST'])
@login_required
def create_user_badge():
    """ User Badge creation endpoint """
    if current_user.is_admin():
        form = CreateUserBadgeForm()
        if form.validate():
            db.create_badge(form.badge.data, form.name.data, form.text.data)

            db.create_sitelog(2, current_user.get_username() +
                              ' created a new badge')
            return json.dumps({'status': 'ok'})
        return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/assign_user_badge/<uid>/<bid>", methods=['POST'])
@login_required
def assign_user_badge(uid, bid):
    """ Assign User Badge endpoint """
    if current_user.is_admin():
        bq = db.query('SELECT `xid` FROM `user_metadata` WHERE `key`=%s AND '
                      '`uid`=%s AND `value`=%s', ('badge', uid, bid))

        if bq.rowcount != 0:
            return json.dumps({'status': 'error',
                               'error': ['Badge is already assigned']})

        db.uquery('INSERT INTO `user_metadata` (`uid`, `key`, `value`) VALUES '
                  '(%s, %s, %s)', (uid, 'badge', bid))

        user = db.get_user_from_uid(uid)
        db.create_sitelog(2, current_user.get_username() +
                          ' assigned a user badge to ' + user['name'],
                          url_for('view_user', user=user['name']))
        return json.dumps({'status': 'ok', 'bid': bid})
    else:
        abort(403)


@do.route("/do/remove_user_badge/<uid>/<bid>", methods=['POST'])
@login_required
def remove_user_badge(uid, bid):
    """ Remove User Badge endpoint """
    if current_user.is_admin():
        bq = db.query('SELECT `xid` FROM `user_metadata` WHERE `key`=%s AND '
                      '`uid`=%s AND `value`=%s', ('badge', uid, bid))

        if bq.rowcount == 0:
            return json.dumps({'status': 'error',
                               'error': ['Badge has already been removed']})

        db.uquery('DELETE FROM `user_metadata` WHERE `xid`=%s', (bq['xid']))
        user = db.get_user_from_uid(uid)
        db.create_sitelog(2, current_user.get_username() +
                          ' removed a user badge from ' + user['name'],
                          url_for('view_user', user=user['name']))

        return json.dumps({'status': 'ok', 'message': 'Badge deleted'})
    else:
        abort(403)


@do.route("/do/sendmsg", methods=['POST'])
@login_required
def create_sendmsg():
    """ User PM message creation endpoint """
    form = CreateUserMessageForm()
    if form.validate():
        db.create_message(mfrom=current_user.uid,
                          to=form.to.data,
                          subject=form.subject.data,
                          content=form.content.data,
                          link=None,
                          mtype=1)
        return json.dumps({'status': 'ok',
                           'sentby': current_user.get_id()})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/ban_user_sub/<sub>", methods=['POST'])
@login_required
def ban_user_sub(sub):
    """ Ban user from sub endpoint """
    sub = db.get_sub_from_name(sub)
    if not sub:
        return json.dumps({'status': 'error',
                           'error': ['Sub does not exist']})
    if current_user.is_mod(sub) or current_user.is_admin():
        form = BanUserSubForm()
        if form.validate():
            user = db.get_user_from_name(form.user.data)
            if not user:
                return json.dumps({'status': 'error',
                                   'error': ['User does not exist.']})
            if db.get_sub_metadata(sub['sid'], 'ban', value=user['uid']):
                return jsonify(status='error', error=['Already banned'])
            db.create_message(mfrom=current_user.uid,
                              to=user['uid'],
                              subject='You have been banned from /s/' +
                              sub['name'],
                              content='',
                              link=sub['name'],
                              mtype=7)

            db.create_sub_metadata(sub['sid'], 'ban', user['uid'])

            db.create_sublog(sub['sid'], 7, current_user.get_username() +
                             ' banned ' + user['name'],
                             url_for('view_sub_bans', sub=sub['name']))
            return json.dumps({'status': 'ok',
                               'sentby': current_user.get_id()})
        return json.dumps({'status': 'error', 'error': get_errors(form)})
    else:
        abort(403)


@do.route("/do/inv_mod2/<sub>", methods=['POST'])
@login_required
def inv_mod2(sub):
    """ User PM for Mod2 invite endpoint """
    sub = db.get_sub_from_name(sub)
    if not sub:
        return json.dumps({'status': 'error',
                           'error': ['Sub does not exist']})
    if current_user.is_topmod(sub) or current_user.is_admin():
        form = EditMod2Form()
        if form.validate():
            user = db.get_user_from_name(form.user.data)
            if not user:
                return json.dumps({'status': 'error',
                                   'error': ['User does not exist.']})

            if misc.isMod(sub, user):
                return json.dumps({'status': 'error',
                                   'error': ['User is already a mod.']})

            if db.get_sub_metadata(sub['sid'], 'mod2i', user['uid']):
                return json.dumps({'status': 'error',
                                   'error': ['User has a pending invite.']})

            if misc.moddedSubCount(user['uid']) >= 15:
                return json.dumps({'status': 'error',
                                   'error': [
                                       "User can't mod more than 15 subs"
                                   ]})
            db.create_message(mfrom=current_user.uid,
                              to=user['uid'],
                              subject='You have been invited to mod a sub.',
                              content=current_user.get_username() +
                              ' has invited you to help moderate ' +
                              sub['name'],
                              link=sub['name'],
                              mtype=2)

            db.create_sub_metadata(sub['sid'], 'mod2i', user['uid'])

            db.create_sublog(sub['sid'], 6, current_user.get_username() +
                             ' invited ' + user['name'] + ' to the mod team',
                             url_for('edit_sub_mods', sub=sub['name']))
            return json.dumps({'status': 'ok',
                               'sentby': current_user.get_id()})
        return json.dumps({'status': 'error', 'error': get_errors(form)})
    else:
        abort(403)


@do.route("/do/remove_sub_ban/<sub>/<user>", methods=['POST'])
@login_required
def remove_sub_ban(sub, user):
    """ Remove Mod2 """
    user = db.get_user_from_name(user)
    sub = db.get_sub_from_name(sub)
    if current_user.is_mod(sub) or current_user.is_admin():
        if not misc.isSubBan(sub, user):
            return jsonify(status='error', error=['User was not banned'])

        db.uquery('UPDATE `sub_metadata` SET `key`=%s WHERE `key`=%s AND '
                  '`value`=%s', ('xban', 'ban', user['uid']))

        db.create_message(mfrom=current_user.uid,
                          to=user['uid'],
                          subject='You have been unbanned from /s/' +
                          sub['name'],
                          content='',
                          mtype=7,
                          link=sub['name'])

        db.create_sublog(sub['sid'], 7, current_user.get_username() +
                         ' removed ban on ' + user['name'],
                         url_for('view_sub_bans', sub=sub['name']))
        return json.dumps({'status': 'ok', 'msg': 'user ban removed'})
    else:
        abort(403)


@do.route("/do/remove_mod2/<sub>/<user>", methods=['POST'])
@login_required
def remove_mod2(sub, user):
    """ Remove Mod2 """
    user = db.get_user_from_name(user)
    sub = db.get_sub_from_name(sub)
    if current_user.is_topmod(sub) or current_user.is_admin():
        x = db.get_sub_metadata(sub['sid'], 'mod2', value=user['uid'])
        if not x:
            return jsonify(status='error', error=['User is not mod'])

        db.uquery('DELETE FROM `sub_metadata` WHERE `key`=%s AND `value`=%s',
                  ('mod2', user['uid']))

        db.create_sublog(sub['sid'], 6, current_user.get_username() +
                         ' removed ' + user['name'] + ' from the mod team',
                         url_for('edit_sub_mods', sub=sub['name']))

        return json.dumps({'status': 'ok', 'msg': 'user demodded'})
    else:
        abort(403)


@do.route("/do/revoke_mod2inv/<sub>/<user>", methods=['POST'])
@login_required
def revoke_mod2inv(sub, user):
    """ revoke Mod2 inv """
    user = db.get_user_from_name(user)
    sub = db.get_sub_from_name(sub)
    if current_user.is_topmod(sub) or current_user.is_admin():
        x = db.get_sub_metadata(sub['sid'], 'mod2i', value=user['uid'])
        if not x:
            return jsonify(status='error', error=['User is not mod'])
        db.uquery('DELETE FROM `sub_metadata` WHERE `key`=%s AND `value`=%s',
                  ('mod2i', user['uid']))

        db.create_sublog(sub['sid'], 6, current_user.get_username() +
                         ' canceled ' + user['name'] + '\'s mod invite',
                         url_for('edit_sub_mods', sub=sub['name']))
        return json.dumps({'status': 'ok', 'msg': 'user invite revoked'})
    else:
        abort(403)


@do.route("/do/accept_mod2inv/<sub>/<user>", methods=['POST'])
@login_required
def accept_mod2inv(sub, user):
    """ Accept mod invite """
    user = db.get_user_from_name(user)
    if user['uid'] != current_user.get_id():
        abort(403)
    sub = db.get_sub_from_name(sub)
    if misc.isModInv(sub, user):
        if misc.moddedSubCount(user['uid']) >= 15:
            return json.dumps({'status': 'error',
                               'error': ["You can't mod more than 15 subs"]})
        db.uquery('UPDATE `sub_metadata` SET `key`=%s WHERE `key`=%s AND '
                  '`value`=%s', ('mod2', 'mod2i', user['uid']))
        db.create_sublog(sub['sid'], 6, user['name'] + ' accepted mod invite',
                         url_for('edit_sub_mods', sub=sub['name']))

        if not current_user.has_subscribed(sub['sid']):
            db.create_subscription(current_user.uid, sub['sid'], 1)
        return json.dumps({'status': 'ok', 'msg': 'user modded'})
    else:
        abort(404)


@do.route("/do/refuse_mod2inv/<sub>/<user>", methods=['POST'])
@login_required
def refuse_mod2inv(sub, user):
    """ refuse Mod2 """
    user = db.get_user_from_name(user)
    sub = db.get_sub_from_name(sub)
    if user.uid != current_user.get_id():
        abort(403)

    if misc.isModInv(sub, user):
        db.uquery('DELETE FROM `sub_metadata` WHERE `key`=%s AND `value`=%s',
                  ('mod2i', user['uid']))

        db.create_sublog(sub['sid'], 6, user['name'] + ' rejected mod invite',
                         url_for('edit_sub_mods', sub=sub['name']))
        return json.dumps({'status': 'ok', 'msg': 'invite refused'})
    else:
        abort(404)


@do.route("/do/read_pm/<mid>", methods=['POST'])
@login_required
def read_pm(mid):
    """ Mark PM as read """
    message = db.query('SELECT * FROM `message` WHERE `mid`=%s', (mid,))
    message = message.fetchone()
    if session['user_id'] == message['receivedby']:
        if message['read'] is not None:
            return json.dumps({'status': 'ok'})
        read = datetime.datetime.utcnow()
        db.uquery('UPDATE `message` SET `read`=%s WHERE `mid`=%s', (read, mid))
        return json.dumps({'status': 'ok', 'mid': mid})
    else:
        abort(403)


@do.route("/do/readall_msgs/<user>/<boxid>", methods=['POST'])
@login_required
def readall_msgs(user, boxid):
    """ Mark all messages in a box as read """
    if current_user.name == user:
        q = 'SELECT * FROM `message` WHERE `read` IS NULL AND `receivedby`=%s '
        if boxid == '1':
            q += 'AND `mtype` IN (1, 8) '
        elif boxid == '2':
            q += 'AND `mtype`=4 '
        elif boxid == '3':
            q += 'AND `mtype`=5 '
        elif boxid == '4':
            q += 'AND `mtype` IN (2, 7) '
        else:
            return jsonify(status='error', error=['wrong boxid bruh'])
        x = db.query(q, (current_user.uid,))

        now = datetime.datetime.utcnow()
        for message in x:
            db.uquery('UPDATE `message` SET `read`=%s WHERE `mid`=%s',
                      (message['mid'], now))

        return json.dumps({'status': 'ok', 'message': 'All marked as read'})
    else:
        abort(403)


@do.route("/do/delete_pm/<mid>", methods=['POST'])
@login_required
def delete_pm(mid):
    """ Delete PM """
    message = db.query('SELECT * FROM `message` WHERE `mid`=%s', (mid,))
    message = message.fetchone()
    if session['user_id'] == message['receivedby']:
        db.uquery('UPDATE `message` SET `mtype`=6 WHERE `mid`=%s', (mid, ))
        return json.dumps({'status': 'ok', 'mid': mid})
    else:
        abort(403)


@do.route("/do/admin/deleteannouncement")
def deleteannouncement():
    """ Removes the current announcement """
    if not current_user.is_admin():
        abort(404)

    db.uquery('DELETE FROM `site_metadata` WHERE `key`=%s', ('announcement',))
    db.create_sitelog(3, current_user.get_username() +
                      ' removed an announcement',
                      url_for('view_post_inbox', pid=form.post.data))
    return redirect(url_for('admin_area'))


@do.route("/do/makeannouncement", methods=['POST'])
def make_announcement():
    """ Flagging post as announcement - not api """
    if not current_user.is_admin():
        abort(404)

    form = DeletePost()

    if form.validate():
        db.update_site_metadata('announcement', form.post.data)
        db.create_sitelog(3, current_user.get_username() +
                          ' made an announcement',
                          url_for('view_post_inbox', pid=form.post.data))

    return redirect(url_for('index'))


@do.route("/do/usebtcdonation", methods=['POST'])
def use_btc_donation():
    """ Enable bitcoin donation module """
    if not current_user.is_admin():
        abort(404)

    form = UseBTCdonationForm()

    if form.validate():
        db.update_site_metadata('usebtc', form.enablebtcmod.data)
        db.update_site_metadata('btcaddr', form.btcaddress.data)
        db.update_site_metadata('btcmsg', form.message.data)

        if form.enablebtcmod.data:
            desc = current_user.get_username() + ' enabled btc donations: ' + \
                  form.btcaddress.data
        else:
            desc = current_user.get_username() + ' disabled btc donations'
        db.create_sitelog(10, desc, '')
        return json.dumps({'status': 'ok'})
    return redirect(url_for('admin_area'))


@do.route("/do/stick/<int:post>", methods=['POST'])
def toggle_sticky(post):
    """ Toggles post stickyness - not api """
    post = db.get_post_from_pid(post)
    sub = db.get_sub_from_sid(post['sid'])
    if not current_user.is_mod(sub) and not current_user.is_admin():
        abort(403)

    form = DeletePost()

    if form.validate():
        x = db.get_sub_metadata(sub['sid'], 'sticky')
        if not x or int(x['value']) != post['pid']:
            db.update_sub_metadata(sub['sid'], 'sticky', post['pid'])
            db.create_sublog(sub['sid'], 4, current_user.get_username() +
                             ' touched sticky',
                             url_for('view_post', sub=sub['name'],
                                     pid=post['pid']))
        else:
            db.uquery('DELETE FROM `sub_metadata` WHERE `value`=%s AND '
                      '`key`=%s', (post['pid'], 'sticky'))
        cache.delete_memoized(misc.getStickies, post['sid'])
        cache.delete_memoized(db.get_sub_metadata, post['sid'], 'sticky',
                              _all=True)
        ckey = make_template_fragment_key('sticky', vary_on=[post['sid']])
        cache.delete(ckey)

    return redirect(url_for('view_sub', sub=sub['name']))


@do.route("/do/flair/<sub>/edit", methods=['POST'])
@login_required
def edit_flair(sub):
    """ Edits flairs (from edit flair page) """
    sub = db.get_sub_from_name(sub)
    if not sub:
        abort(404)

    if not current_user.is_mod(sub) and not current_user.is_admin():
        abort(403)

    form = EditSubFlair()
    if form.validate():
        flair = db.query('SELECT * FROM `sub_flair` WHERE `sid`=%s AND '
                         '`xid`=%s', (sub['sid'], form.flair.data))

        if not flair.rowcount:
            return json.dumps({'status': 'error',
                               'error': ['Flair does not exist']})

        db.uquery('UPDATE `sub_flair` SET `text`=%s WHERE `xid`=%s',
                  (form.text.data, form.flair.data))
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/flair/<sub>/delete", methods=['POST'])
@login_required
def delete_flair(sub):
    """ Removes a flair (from edit flair page) """
    sub = db.get_sub_from_name(sub)
    if not sub:
        abort(404)

    if not current_user.is_mod(sub) and not current_user.is_admin():
        abort(403)

    form = DeleteSubFlair()
    if form.validate():
        flair = db.query('SELECT * FROM `sub_flair` WHERE `sid`=%s AND '
                         '`xid`=%s', (sub['sid'], form.flair.data))
        if not flair:
            return json.dumps({'status': 'error',
                               'error': ['Flair does not exist']})
        db.uquery('DELETE FROM `sub_flair` WHERE `xid`=%s', (form.flair.data,))

        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/flair/<sub>/create", methods=['POST'])
@login_required
def create_flair(sub):
    """ Creates a new flair (from edit flair page) """
    sub = db.get_sub_from_name(sub)
    if not sub:
        abort(404)

    if not current_user.is_mod(sub) and not current_user.is_admin():
        abort(403)
    form = CreateSubFlair()
    if form.validate():
        db.uquery('INSERT INTO `sub_flair` (`sid`, `text`) VALUES (%s, %s)',
                  (sub['sid'], form.text.data))
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/recovery", methods=['POST'])
def recovery():
    """ Password recovery page. Email+captcha and sends recovery email """
    if current_user.is_authenticated:
        abort(403)

    form = forms.PasswordRecoveryForm()
    if form.validate():
        user = db.query('SELECT * FROM `user` WHERE `email`=%s',
                        (form.edmail.data)).fetchone()
        if not user:
            return json.dumps({'status': 'ok'})

        # User exists, check if they don't already have a key sent
        key = db.get_user_metadata(user['uid'], 'recovery-key')
        if key:
            # Key exists, check if it has expired
            keyExp = db.get_user_metadata(user['uid'], 'recovery-key-time')
            expiration = float(keyExp)
            if (time.time() - expiration) > 86400:  # 1 day
                # Key is old. remove it and proceed
                db.uquery('DELETE FROM `user_metadata` WHERE `uid`=%s AND '
                          '`key`=%s', (user['uid'], 'recovery-key'))
                db.uquery('DELETE FROM `user_metadata` WHERE `uid`=%s AND '
                          '`key`=%s', (user['uid'], 'recovery-key-time'))
            else:
                # silently fail >_>
                return json.dumps({'status': 'ok'})

        # checks done, doing the stuff.
        rekey = uuid.uuid4()
        db.create_user_metadata(user['uid'], 'recovery-key', rekey)
        db.create_user_metadata(user['uid'], 'recovery-key-time', time.time())

        sendMail(
            subject='Password recovery',
            to=user['email'],
            content="""<h1><strong>{0}</strong></h1>
            <p>Somebody (most likely you) has requested a password reset for
            your account</p>
            <p>To proceed, visit the following address</p>
            <a href="{1}">{1}</a>
            <hr>
            <p>If you didn't request a password recovery, please ignore this
            email</p>
            """.format(config.LEMA, url_for('password_reset', key=rekey,
                                            uid=user['uid'], _external=True))
        )

        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/reset", methods=['POST'])
def reset():
    """ Password reset. Takes key and uid and changes password """
    if current_user.is_authenticated:
        abort(403)

    form = forms.PasswordResetForm()
    if form.validate():
        user = db.get_user_from_uid(form.user.data)
        if not user:
            return json.dumps({'status': 'ok'})

        # User exists, check if they don't already have a key sent
        key = db.get_user_metadata(user['uid'], 'recovery-key')
        if not key:
            abort(403)

        if key != form.key.data:
            abort(403)

        db.uquery('DELETE FROM `user_metadata` WHERE `uid`=%s AND '
                  '`key`=%s', (user['uid'], 'recovery-key'))
        db.uquery('DELETE FROM `user_metadata` WHERE `uid`=%s AND '
                  '`key`=%s', (user['uid'], 'recovery-key-time'))

        # All good. Set da password.
        db.update_user_password(user['uid'], form.password.data)
        login_user(SiteUser(user))
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/edit_comment", methods=['POST'])
@login_required
def edit_comment():
    """ Edits a comment """
    form = forms.EditCommentForm()
    if form.validate():
        comment = db.get_comment_from_cid(form.cid.data)
        if not comment:
            abort(404)

        if comment['uid'] != current_user.uid and not current_user.is_admin():
            abort(403)

        dt = datetime.datetime.utcnow()
        db.uquery('UPDATE `sub_post_comment` SET `content`=%s, `lastedit`=%s '
                  'WHERE `cid`=%s', (form.text.data, dt, form.cid.data))
        return jsonify(status='ok')
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/delete_comment", methods=['POST'])
@login_required
def delete_comment():
    """ deletes a comment """
    form = forms.DeleteCommentForm()
    if form.validate():
        comment = db.get_comment_from_cid(form.cid.data)
        if not comment:
            abort(404)

        if comment['uid'] != current_user.uid and not current_user.is_admin():
            abort(403)

        if comment['uid'] != current_user.uid and current_user.is_admin():
            db.create_sitelog(4, current_user.get_username() +
                              ' deleted a comment',
                              url_for('view_post_inbox', pid=comment['pid']))
        db.uquery('UPDATE `sub_post_comment` SET `status`=1 WHERE `cid`=%s',
                  (form.cid.data,))
        return jsonify(status='ok')
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
    comment = db.get_comment_from_cid(cid)
    if not comment:
        return json.dumps({'status': 'error',
                           'error': ['Comment does not exist']})

    if comment['uid'] == current_user.get_id():
        return json.dumps({'status': 'error',
                           'error': ['You can\'t vote on your own comments']})

    qvote = db.query('SELECT * FROM `sub_post_comment_vote` WHERE `cid`=%s AND'
                     ' `uid`=%s', (cid, current_user.uid)).fetchone()
    user = db.get_user_from_uid(comment['uid'])

    if qvote:
        if bool(qvote['positive']) == (True if voteValue == 1 else False):
            return json.dumps({'status': 'error',
                               'error': ['You already voted.']})
        else:
            positive = True if voteValue == 1 else False
            db.uquery('UPDATE `sub_post_comment_vote` SET `positive`=%s WHERE '
                      '`xid`=%s', (positive, qvote['xid']))
            db.uquery('UPDATE `sub_post_comment` SET `score`=`score`+%s WHERE '
                      '`cid`=%s', (voteValue*2, comment['cid']))
            if user['score'] is not None:
                db.uquery('UPDATE `user` SET `score`=`score`+%s WHERE '
                          '`uid`=%s', (voteValue*2, comment['uid']))
            return jsonify(status='ok', message='Vote flipped')
    else:
        positive = True if voteValue == 1 else False
        db.uquery('INSERT INTO `sub_post_comment_vote` (`cid`, `uid`, '
                  '`positive`) VALUES (%s, %s, %s)',
                  (cid, current_user.uid, positive))
    db.uquery('UPDATE `sub_post_comment` SET `score`=`score`+%s WHERE '
              '`cid`=%s', (voteValue, comment['cid']))

    if user['score'] is not None:
        db.uquery('UPDATE `user` SET `score`=`score`+%s WHERE '
                  '`uid`=%s', (voteValue, comment['uid']))

    return json.dumps({'status': 'ok'})
