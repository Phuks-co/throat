""" /do/ views (AJAX stuff) """

import json
import re
import time
import datetime
import uuid
import bcrypt
import requests
import magic
import hashlib
import os
import pyexiv2
from PIL import Image
from bs4 import BeautifulSoup
from flask import Blueprint, redirect, url_for, session, abort, jsonify
from flask import render_template, request
from flask_login import login_user, login_required, logout_user, current_user
from flask_cache import make_template_fragment_key
import config
from .. import forms, misc, caching
from ..socketio import socketio
from .. import database as db
from ..forms import LogOutForm, CreateSubFlair, DummyForm
from ..forms import CreateSubForm, EditSubForm, EditUserForm, EditSubCSSForm
from ..forms import CreateUserBadgeForm, EditModForm, BanUserSubForm
from ..forms import CreateSubTextPost, EditSubTextPostForm
from ..forms import PostComment, CreateUserMessageForm, DeletePost
from ..forms import EditSubLinkPostForm, SearchForm, EditMod2Form
from ..forms import DeleteSubFlair, UseBTCdonationForm, BanDomainForm
from ..forms import CreateMulti, EditMulti, DeleteMulti
from ..forms import UseInviteCodeForm, SecurityQuestionForm
from ..misc import cache, sendMail, allowedNames, get_errors, engine
from ..models import SubPost, SubPostComment, Sub, Message, User, UserIgnores, SubLog, SiteLog, SubMetadata
from ..models import SubStylesheet, SubSubscriber, SubUploads, UserUploads, SiteMetadata, SubPostMetadata, SubPostReport
from ..models import SubPostVote, SubPostCommentVote, UserMetadata, SubFlair, SubPostPollOption, SubPostPollVote
from peewee import fn, JOIN

do = Blueprint('do', __name__)

# allowedCSS = re.compile("\'(^[0-9]{1,5}[a-zA-Z ]+$)|none\'")


@do.route("/do/logout", methods=['POST'])
@login_required
def logout():
    """ Logout endpoint """
    form = LogOutForm()
    if form.validate():
        if session.get('usid'):
            socketio.emit('uinfo', {'loggedin': False}, namespace='/alt',
                          room=session['usid'])
        logout_user()
    if request.get_json() and request.get_json().get('j'):
        return jsonify(status='ok')
    else:
        return redirect(url_for('index'))


@do.route("/do/search", defaults={'stype': 'search'}, methods=['POST'])
@do.route("/do/search/<stype>", methods=['POST'])
def search(stype):
    """ Search endpoint """
    if stype not in ('search', 'subs', 'admin_users', 'admin_post_voting', 'admin_subs', 'admin_post'):
        abort(404)
    if not stype.endswith('search'):
        stype += '_search'

    if not current_user.is_admin() and stype.startswith('admin'):
        abort(403)
    form = SearchForm()
    term = re.sub(r'[^A-Za-z0-9.,\-_\'" ]+', '', form.term.data)
    return redirect(url_for(stype, term=term))


@do.route("/do/edit_user", methods=['POST'])
@login_required
def edit_user():
    """ Edit user endpoint """
    form = EditUserForm()
    if form.validate():
        usr = User.get(User.uid == current_user.uid)
        if not misc.validate_password(usr, form.oldpassword.data):
            return json.dumps({'status': 'error', 'error': ['Wrong password']})
        if form.delete_account.data:
            usr.status = 10
            usr.save()
            if session.get('usid'):
                socketio.emit('uinfo', {'loggedin': False}, namespace='/alt', room=session['usid'])
            logout_user()
            return json.dumps({'status': 'ok', 'addr': '/'})
        usr.email = form.email.data
        if form.password.data:
            password = bcrypt.hashpw(form.password.data.encode('utf-8'), bcrypt.gensalt())
            if isinstance(password, bytes):
                password = password.decode('utf-8')

            usr.password = password
            usr.crypto = 1

        usr.save()
        current_user.update_prefs('exlinks', form.external_links.data)
        current_user.update_prefs('labrat', form.experimental.data)
        current_user.update_prefs('nostyles', form.disable_sub_style.data)
        current_user.update_prefs('nsfw', form.show_nsfw.data)
        current_user.update_prefs('noscroll', form.noscroll.data)
        current_user.update_prefs('nochat', form.nochat.data)

        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/delete_post", methods=['POST'])
@login_required
def delete_post():
    """ Post deletion endpoint """
    form = DeletePost()

    if form.validate():
        try:
            post = SubPost.get(SubPost.pid == form.post.data)
        except SubPost.DoesNotExist:
            return jsonify(status='error', error=['Post does not exist'])

        if post.deleted != 0:
            return jsonify(status='error', error=['Post was already deleted'])

        sub = Sub.get(Sub.sid == post.sid)
        subI = misc.getSubData(post.sid)

        if not current_user.is_mod(sub.sid) and not current_user.is_admin() and not post.uid.uid == current_user.uid:
            return jsonify(status='error', error=['Not authorized'])

        if post.uid.uid == current_user.uid:
            deletion = 1
        else:
            if not form.reason.data:
                return jsonify(status="error", error=["Cannot delete without reason"])
            deletion = 2
            # notify user.
            misc.create_message(mfrom=current_user.uid, to=post.uid.uid,
                                subject='Your post on /s/' + sub.name + ' has been deleted.',
                                content='Reason: ' + form.reason.data,
                                link=sub.name, mtype=11)
            
            misc.create_sublog(misc.LOG_TYPE_SUB_DELETE_POST, current_user.uid, post.sid,
                    comment=form.reason.data, link=url_for('view_post_inbox', pid=post.pid),
                    admin=True if (not current_user.is_mod(post.sid) and current_user.is_admin()) else False)



        # time limited to prevent socket spam
        if (datetime.datetime.utcnow() - post.posted).seconds < 86400:
            socketio.emit('deletion', {'pid': post.pid}, namespace='/snt', room='/all/new')

        # check if the post is an announcement. Unannounce if it is.
        try:
            ann = SiteMetadata.select().where(SiteMetadata.key == 'announcement').where(SiteMetadata.value == post.pid).get()
            ann.delete_instance()
            cache.delete_memoized(misc.getAnnouncementPid)
        except SiteMetadata.DoesNotExist:
            pass

        sub.posts -= 1
        sub.save()

        post.deleted = deletion
        post.save()

        return jsonify(status='ok')
    return jsonify(status='ok', error=get_errors(form))


@do.route("/do/create_sub", methods=['POST'])
@login_required
def create_sub():
    """ Sub creation endpoint """
    form = CreateSubForm()
    if form.validate():
        if not allowedNames.match(form.subname.data):
            return jsonify(status='error', error=['Sub name has invalid characters'])

        if len(form.subname.data) < 2:
            return jsonify(status='error', error=['Sub name too short'])

        if len(form.subname.data) > 32:
            return jsonify(status='error', error=['Sub name too long'])

        if form.subname.data.lower() in ('all', 'new', 'hot', 'top', 'admin', 'home'):
            return jsonify(status='error', error=['Invalid sub name'])

        try:
            Sub.get(Sub.name == form.subname.data)
            return jsonify(status='error', error=['Sub is already registered'])
        except Sub.DoesNotExist:
            pass

        level = misc.get_user_level(current_user.uid)[0]
        if not getattr(config, 'TESTING', False):
            if (level <= 1) and (not current_user.admin):
                return jsonify(status='error', error=['You must be at least level 2.'])

            if misc.moddedSubCount(current_user.uid) >= 20 and (not current_user.admin):
                return jsonify(status='error', error=['You cannot mod more than 20 subs.'])

            if misc.moddedSubCount(current_user.uid) >= (level - 1) and (not current_user.admin):
                return jsonify(status='error', error=['You cannot mod more than {0} subs. Try leveling up your account'.format(level - 1)])

        sub = Sub.create(sid=uuid.uuid4(), name=form.subname.data, title=form.title.data)
        SubMetadata.create(sid=sub.sid, key='mod', value=current_user.uid)
        SubMetadata.create(sid=sub.sid, key='mod1', value=current_user.uid)
        SubMetadata.create(sid=sub.sid, key='creation', value=datetime.datetime.utcnow())
        SubStylesheet.create(sid=sub.sid, content='', source='/* CSS here */')

        # admin/site log
        misc.create_sublog(misc.LOG_TYPE_SUB_CREATE, uid=current_user.uid, sid=sub.sid, admin=True)

        SubSubscriber.create(uid=current_user.uid, sid=sub.sid, status=1)

        return jsonify(status='ok', addr=url_for('sub.view_sub', sub=form.subname.data))

    return jsonify(status='error', error=get_errors(form))


@do.route("/do/edit_sub_css/<sub>", methods=['POST'])
@login_required
def edit_sub_css(sub):
    """ Edit sub endpoint """
    try:
        sub = Sub.get(Sub.name == sub)
    except Sub.DoesNotExist:
        return jsonify(status='error', error=["Sub does not exist"])

    if not current_user.is_mod(sub.sid) and not current_user.is_admin():
        return jsonify(status='error', error=["Not authorized"])

    form = EditSubCSSForm()
    if form.validate():
        styles = SubStylesheet.get(SubStylesheet.sid == sub.sid)
        dcss = misc.validate_css(form.css.data, sub.sid)
        if dcss[0] != 0:
            return jsonify(status='error', error=['Error on {0}:{1}: {2}'.format(dcss[1], dcss[2], dcss[0])])

        styles.content = dcss[1]
        styles.source = form.css.data
        styles.save()
        SubLog.create(sid=sub.sid, action=4, link=url_for('sub.view_sub', sub=sub.name), time=datetime.datetime.utcnow(),
                      desc='{0} modified the sub\'s stylesheet'.format(current_user.name))

        return json.dumps({'status': 'ok',
                           'addr': url_for('sub.view_sub', sub=sub.name)})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/edit_sub/<sub>", methods=['POST'])
@login_required
def edit_sub(sub):
    """ Edit sub endpoint """
    try:
        sub = Sub.get(Sub.name == sub)
    except Sub.DoesNotExist:
        return jsonify(status='error', error=["Sub does not exist"])
    if current_user.is_mod(sub.sid) or current_user.is_admin():
        form = EditSubForm()
        if form.validate():
            sub.title = form.title.data
            sub.sidebar = form.sidebar.data
            sub.nsfw = form.nsfw.data 
            sub.save()
            
            sub.update_metadata('restricted', form.restricted.data)
            sub.update_metadata('ucf', form.usercanflair.data)
            sub.update_metadata('videomode', form.videomode.data)
            sub.update_metadata('allow_polls', form.polling.data)

            if form.subsort.data != "None":
                sub.update_metadata('sort', form.subsort.data)

            misc.create_sublog(misc.LOG_TYPE_SUB_SETTINGS, current_user.uid, sub.sid)

            if not current_user.is_mod(sub.sid) and current_user.is_admin():
                misc.create_sitelog(misc.LOG_TYPE_SUB_SETTINGS, current_user.uid,
                                    comment='/s/' + sub.name,
                                    link=url_for('sub.view_sub', sub=sub.name))

            return jsonify(status="ok", addr=url_for('sub.view_sub', sub=sub.name))
        return jsonify(status="error", error=get_errors(form))
    else:
        abort(403)


@do.route("/do/flair/<sub>/<pid>/<fl>", methods=['POST'])
@login_required
def assign_post_flair(sub, pid, fl):
    """ Assign a post's flair """
    try:
        sub = Sub.get(Sub.name == sub)
    except Sub.DoesNotExist:
        return jsonify(status='error', error=["Sub does not exist"])

    try:
        post = SubPost.get(SubPost.pid == pid)
    except SubPost.DoesNotExist:
        return jsonify(status='error', error=['Post does not exist'])

    form = DummyForm()
    if form.validate():
        if current_user.is_mod(sub.sid) or (post.uid.uid == current_user.uid and sub.get_metadata('ucf')):
            try:
                flair = SubFlair.get((SubFlair.xid == fl) & (SubFlair.sid == sub.sid))
            except SubFlair.DoesNotExist:
                return jsonify(status='error', error='Flair does not exist')

            post.flair = flair.text
            post.save()


            return jsonify(status='ok')
        else:
            return jsonify(status='error', error='Not authorized')
    return jsonify(status="error", error=get_errors(form))


@do.route("/do/remove_post_flair/<sub>/<pid>", methods=['POST'])
def remove_post_flair(sub, pid):
    """ Deletes a post's flair """
    try:
        sub = Sub.get(Sub.name == sub)
    except Sub.DoesNotExist:
        return jsonify(status='error', error=["Sub does not exist"])

    try:
        post = SubPost.get(SubPost.pid == pid)
    except SubPost.DoesNotExist:
        return jsonify(status='error', error=['Post does not exist'])

    if current_user.is_mod(sub['sid']) or (post.uid.uid == current_user.uid and sub.get_metadata('ucf')):
        if not post.flair:
            return jsonify(status='error', error='Post has no flair')
        else:
            post.flair = None
            post.save()

        return jsonify(status='ok')
    else:
        abort(403)


@do.route("/do/edit_mod", methods=['POST'])
@login_required
def edit_mod():
    """ Admin endpoint used for sub transfers. """
    if not current_user.is_admin():
        abort(403)
    form = EditModForm()

    try:
        sub = Sub.get(Sub.name == form.sub.data)
    except Sub.DoesNotExist:
        return jsonify(status='error', error=["Sub does not exist"])
    
    try:
        user = User.get(User.name == form.user.data)
    except User.DoesNotExist:
        return jsonify(status='error', error=["User does not exist"])

    if form.validate():
        sub.update_metadata('mod1', user.uid)

        qdel = SubMetadata.delete().where(SubMetadata.key == 'mod2').where(SubMetadata.value == user.uid).where(SubMetadata.sid == sub.sid)
        qdel.execute()

        misc.create_sublog(misc.LOG_TYPE_SUB_TRANSFER, current_user.uid, sub.sid,
                           comment=user.name, admin=True)

        return jsonify(status='ok')
    return jsonify(status="error", error=get_errors(form))


@do.route("/do/subscribe/<sid>", methods=['POST'])
@login_required
def subscribe_to_sub(sid):
    """ Subscribe to sub """
    try:
        sub = Sub.get(Sub.sid == sid)
    except Sub.DoesNotExist:
        return jsonify(status='error', error='sub not found')

    if current_user.has_subscribed(sid):
        return jsonify(status='ok', message='already subscribed')

    form = DummyForm()
    if form.validate():
        if current_user.has_blocked(sid):
            ss = SubSubscriber.get((SubSubscriber.uid == current_user.uid) & (SubSubscriber.sid == sid) & (SubSubscriber.status == 2))
            ss.delete_instance()

        SubSubscriber.create(time=datetime.datetime.utcnow(), uid=current_user.uid, sid=sid, status=1)
        sub.subscribers += 1
        sub.save()
        return jsonify(status='ok')
    return jsonify(status='error', error=get_errors(form))


@do.route("/do/unsubscribe/<sid>", methods=['POST'])
@login_required
def unsubscribe_from_sub(sid):
    """ Unsubscribe from sub """
    try:
        sub = Sub.get(Sub.sid == sid)
    except Sub.DoesNotExist:
        return jsonify(status='error', error='sub not found')

    if not current_user.has_subscribed(sid):
        return jsonify(status='ok', message='not subscribed')

    form = DummyForm()
    if form.validate():
        ss = SubSubscriber.get((SubSubscriber.uid == current_user.uid) & (SubSubscriber.sid == sid) & (SubSubscriber.status == 1))
        ss.delete_instance()

        sub.subscribers -= 1
        sub.save()
        return jsonify(status='ok')
    return jsonify(status='error', error=get_errors(form))


@do.route("/do/block/<sid>", methods=['POST'])
@login_required
def block_sub(sid):
    """ Block sub """
    try:
        sub = Sub.get(Sub.sid == sid)
    except Sub.DoesNotExist:
        return jsonify(status='error', error='sub not found')

    if current_user.has_blocked(sid):
        return jsonify(status='ok', message='already blocked')

    form = DummyForm()
    if form.validate():
        if current_user.has_subscribed(sub.name):
            sub.subscribers -= 1
            sub.save()
            ss = SubSubscriber.get((SubSubscriber.uid == current_user.uid) & (SubSubscriber.sid == sid) & (SubSubscriber.status == 1))
            ss.delete_instance()

        SubSubscriber.create(time=datetime.datetime.utcnow(), uid=current_user.uid, sid=sid, status=2)
        return jsonify(status='ok')
    return jsonify(status='error', error=get_errors(form))


@do.route("/do/unblock/<sid>", methods=['POST'])
@login_required
def unblock_sub(sid):
    """ Unblock sub """
    try:
        sub = Sub.get(Sub.sid == sid)
    except Sub.DoesNotExist:
        return jsonify(status='error', error='sub not found')

    if not current_user.has_blocked(sid):
        return jsonify(status='ok', message='sub not blocked')

    form = DummyForm()
    if form.validate():
        ss = SubSubscriber.get((SubSubscriber.uid == current_user.uid) & (SubSubscriber.sid == sub.sid) & (SubSubscriber.status == 2))
        ss.delete_instance()
        return jsonify(status='ok')
    return jsonify(status='error', error=get_errors(form))


@do.route("/do/get_txtpost/<pid>", methods=['GET'])
def get_txtpost(pid):
    """ Sub text post expando get endpoint """
    try:
        try:
            post = misc.getSinglePost(pid)
        except SubPost.DoesNotExist:
            abort(404)
        
        if post['deleted']:
            abort(404)
        cont = misc.our_markdown(post['content'])
        if post['ptype'] == 3:
            postmeta = misc.metadata_to_dict(SubPostMetadata.select().where(SubPostMetadata.pid == pid))
            options, total_votes, has_voted, voted_for, poll_open = ([], 0, None, None, True)
            # poll. grab options and votes.
            options = SubPostPollOption.select(SubPostPollOption.id, SubPostPollOption.text, fn.Count(SubPostPollVote.id).alias('votecount'))
            options = options.join(SubPostPollVote, JOIN.LEFT_OUTER, on=(SubPostPollVote.vid == SubPostPollOption.id))
            options = options.where(SubPostPollOption.pid == pid).group_by(SubPostPollOption.id)
            total_votes = SubPostPollVote.select().where(SubPostPollVote.pid == pid).count()

            if current_user.is_authenticated:
                # Check if user has already voted on this poll.
                try:
                    u_vote = SubPostPollVote.get((SubPostPollVote.pid == pid) & (SubPostPollVote.uid == current_user.uid))
                    has_voted = True
                    voted_for = u_vote.vid_id
                except SubPostPollVote.DoesNotExist:
                    has_voted = False
                
                # Check if the poll is open
                poll_open = True
                if 'poll_closed' in postmeta:
                    poll_open = False

                if 'poll_closes_time' in postmeta:
                    if int(postmeta['poll_closes_time']) < time.time():
                        poll_open = False

                cont = render_template('postpoll.html', post=post, poll_options=options, votes=total_votes, has_voted=has_voted, voted_for=voted_for,
                           poll_open=poll_open, postmeta=postmeta) + cont
        
        return jsonify(status='ok', content=cont)
    except SubPost.DoesNotExist:
        return jsonify(status='error', error=['No longer available'])


@do.route("/do/edit_txtpost/<pid>", methods=['POST'])
@login_required
def edit_txtpost(pid):
    """ Sub text post creation endpoint """
    form = EditSubTextPostForm()
    if form.validate():
        try:
            post = SubPost.get(SubPost.pid == pid)
        except SubPost.DoesNotExist:
            return jsonify(status='error', error=['Post not found'])

        if post.deleted != 0:
            return jsonify(status='error', error=['Post was deleted'])

        if current_user.is_subban(post.sid):
            return jsonify(status='error', error=['You are banned on this sub.'])

        post.content = form.content.data
        # Only save edited time if it was posted more than five minutes ago
        if (datetime.datetime.utcnow() - post.posted).seconds > 300:
            post.edited = datetime.datetime.utcnow()
        post.save()
        return jsonify(status='ok')
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/grabtitle", methods=['POST'])
@login_required
def grab_title():
    """ Safely grabs the <title> from a page """
    url = request.json.get('u')
    if not url:
        abort(400)
    try:
        req = misc.safeRequest(url)
    except (requests.exceptions.RequestException, ValueError):
        return jsonify(status='error', error=['Couldn\'t get title'])

    og = BeautifulSoup(req[1], 'lxml')
    try:
        title = og('title')[0].text
    except (OSError, ValueError, IndexError):
        return jsonify(status='error', error=['Couldn\'t get title'])
    return jsonify(status='ok', title=title.strip(misc.WHITESPACE))


def post_over_limit(limit):
    form = CreateSubTextPost()
    return render_template('createpost.html', txtpostform=form, error='Wait a bit before posting.')


@do.route("/do/post", methods=['POST'])
@login_required
@misc.ratelimit(1, per=30, over_limit=post_over_limit)
def create_post():
    """ Sub link post creation endpoint """
    if misc.get_user_level(current_user.uid)[0] <= 4:
        form = forms.CreteSubPostCaptcha()
        if not form.validate():
            return render_template('createpost.html', txtpostform=form, error=get_errors(form)[0])
    form = CreateSubTextPost()
    if form.validate():
        # Put pre-posting checks here
        if not current_user.is_admin():
            try:
                enable_posting = SiteMetadata.get(SiteMetadata.key == 'enable_posting')
                if enable_posting.value in ('False', '0'):
                    return render_template('createpost.html', txtpostform=form, error="Posting has been temporarily disabled")
            except SiteMetadata.DoesNotExist:
                pass
                    
        sub = db.get_sub_from_name(form.sub.data)
        if not sub:
            return render_template('createpost.html', txtpostform=form, error="Sub does not exist")
        if sub['name'].lower() in ('all', 'new', 'hot', 'top', 'admin', 'home'):
            return render_template('createpost.html', txtpostform=form, error="You cannot post in this sub.")
        if current_user.is_subban(sub):
            return render_template('createpost.html', txtpostform=form, error="You're banned from posting on this sub")
        if misc.isRestricted(sub) and not current_user.is_mod(sub['sid']):
            return render_template('createpost.html', txtpostform=form, error="Only mods can post on this sub")

        if misc.get_user_level(current_user.uid)[0] < 7:
            today = datetime.datetime.utcnow() - datetime.timedelta(days=1)
            lposts = SubPost.select().where(SubPost.uid == current_user.uid).where(SubPost.sid == sub['sid']).where(SubPost.posted > today).count()
            tposts = SubPost.select().where(SubPost.uid == current_user.uid).where(SubPost.posted > today).count()
            if lposts > 10 or tposts > 25:
                return render_template('createpost.html', txtpostform=form, error="You have posted too much today")
        if len(form.title.data.strip(misc.WHITESPACE)) < 3:
            return render_template('createpost.html', txtpostform=form, error="Title is too short and/or contains whitespace characters")
        fileid = False
        if form.ptype.data == 'link':
            fupload = misc.upload_file()
            if fupload:
                form.link.data = config.STORAGE_HOST + fupload
                fileid = fupload

            if not form.link.data:
                return render_template('createpost.html', txtpostform=form, error="No link provided")

            lx = db.query('SELECT `pid` FROM `sub_post` WHERE `sid`=%s AND '
                          '`link`=%s AND `deleted`=0 AND `posted` > DATE_SUB(NOW(), INTERVAL 1 '
                          'MONTH)', (sub['sid'], form.link.data)).fetchone()
            if lx:
                return render_template('createpost.html', txtpostform=form, error="This link was recently posted on this sub")
            
            if misc.is_domain_banned(form.link.data):
                return render_template('createpost.html', txtpostform=form, error="This domain is banned")

            img = misc.get_thumbnail(form.link.data)
        if form.ptype.data == 'poll':
            ptype = 3
            # Check if this sub allows polls...
            try:
                allows_polls = SubMetadata.get((SubMetadata.sid == sub['sid']) & (SubMetadata.key == "allow_polls"))
                if allows_polls.value != '1':
                    return render_template('createpost.html', txtpostform=form, error="This sub does not allow polling")
            except SubMetadata.DoesNotExist:
                return render_template('createpost.html', txtpostform=form, error="This sub does not allow polling")
            # check if we got at least three options
            options = request.form.getlist('op[]')
            options = [x for x in options if len(x.strip(misc.WHITESPACE)) > 0]  # Remove empty strings
            if len(options) < 2:
                return render_template('createpost.html', txtpostform=form, error="Not enough poll options provided")
            
            for p in options:
                if len(p) > 128:
                    return render_template('createpost.html', txtpostform=form, error="Poll option text is too long.")
            
            if form.closetime.data:
                try:
                    closetime = int(form.closetime.data)
                    if (closetime - time.time()) > 8000000:
                        return render_template('createpost.html', txtpostform=form, error="Poll closing time is too far in the future.")
                except ValueError:
                    return render_template('createpost.html', txtpostform=form, error="Invalid closing time.")
                
                if time.time() > closetime:
                    return render_template('createpost.html', txtpostform=form, error="The closing time is in the past!")
        elif form.ptype.data == 'link':
            ptype = 1
        else:
            ptype = 0

        post = SubPost.create(sid=sub['sid'],
                              uid=current_user.uid,
                              title=form.title.data,
                              content=form.content.data if ptype != 1 else '',
                              link=form.link.data if ptype == 1 else None,
                              posted=datetime.datetime.utcnow(),
                              score=1, upvotes=1, downvotes=0,
                              deleted=0,
                              comments=0,
                              ptype=ptype,
                              nsfw=form.nsfw.data if not sub['nsfw'] else 1,
                              thumbnail=img if ptype == 1 else '')
        
        if ptype == 3:
            # Create SubPostPollOption objects...
            poll_options = [{'pid': post.pid, 'text': x} for x in options]
            SubPostPollOption.insert_many(poll_options).execute()
            # apply all poll options..
            if form.hideresults.data:
                SubPostMetadata.create(pid=post.pid, key='hide_results', value=1)
            
            if form.closetime.data:
                SubPostMetadata.create(pid=post.pid, key='poll_closes_time', value=closetime)
                
        db.uquery('UPDATE `sub` SET posts = posts + 1 WHERE `sid`=%s',
                  (sub['sid'], ))
        addr = url_for('sub.view_post', sub=sub['name'], pid=post.pid)
        posts = misc.getPostList(misc.postListQueryBase(nofilter=True).where(SubPost.pid == post.pid), 'new', 1).dicts()
        socketio.emit('thread',
                      {'addr': addr, 'sub': sub['name'], 'type': form.ptype.data,
                       'user': current_user.name, 'pid': post.pid, 'sid': sub['sid'],
                       'html': engine.get_template('shared/post.html').render({'posts': posts, 'sub': False})},
                      namespace='/snt',
                      room='/all/new')

        # XXX: The auto-upvote is placed *after* broadcasting the post via socketio so that the upvote arrow
        # does not appear highlighted to everybody.
        SubPostVote.create(uid=current_user.uid, pid=post.pid, positive=True)
        User.update(given=User.given + 1).where(User.uid == current_user.uid).execute()
        # We send a yourvote message so that the upvote arrow *does* appear highlighted to the creator.
        socketio.emit('yourvote', {'pid': post.pid, 'status': 1, 'score': post.score}, namespace='/snt',
                      room='user' + current_user.uid)

        if fileid:
            db.create_user_upload_post(pid=post.pid, uid=current_user.uid, fileid=fileid, thumbnail=img if img else '')

        misc.workWithMentions(form.content.data, None, post, sub)
        misc.workWithMentions(form.title.data, None, post, sub)
        return redirect(addr)
    return render_template('createpost.html', txtpostform=form, error=get_errors(form)[0])


@do.route('/do/vote/<pid>/<value>', methods=['POST'])
def upvote(pid, value):
    """ Logs an upvote to a post. """
    form = DummyForm()
    if not form.validate():
        return json.dumps({'status': 'error', 'error': get_errors(form)})
    if not current_user.is_authenticated:
        abort(403)
    if value == "up":
        voteValue = 1
    elif value == "down":
        voteValue = -1
        if current_user.get_given()[2] < 0:
            return jsonify(status='error', error=['Score balance is negative'])
    else:
        abort(403)

    try:
        post = SubPost.get(SubPost.pid == pid)
    except SubPost.DoesNotExist:
        return jsonify(status='error', error=['Post does not exist'])

    if post.deleted:
        return jsonify(status='error',
                       error=["You can't vote on deleted posts"])

    #if post.uid.uid == current_user.uid:
    #    return jsonify(status='error',
    #                   error=["You can't vote on your own posts"])

    if current_user.is_subban(post.sid):
        return jsonify(status='error', error=['You are banned on this sub.'])

    if (datetime.datetime.utcnow() - post.posted) > datetime.timedelta(days=60):
        return jsonify(status='error', error=["Post is archived"])
    try:
        qvote = SubPostVote.select().where(SubPostVote.pid == pid).where(SubPostVote.uid == current_user.uid).get()
    except SubPostVote.DoesNotExist:
        qvote = False
    user = User.get(User.uid == post.uid)

    positive = True if voteValue == 1 else False
    if qvote:
        if bool(qvote.positive) == (True if voteValue == 1 else False):
            qvote.delete_instance()

            if positive:
                SubPost.update(score=SubPost.score - voteValue, upvotes=SubPost.upvotes - 1).where(SubPost.pid == post.pid).execute()
            else:
                SubPost.update(score=SubPost.score - voteValue, downvotes=SubPost.downvotes - 1).where(SubPost.pid == post.pid).execute()

            User.update(score=User.score - voteValue).where(User.uid == post.uid).execute()
            User.update(given=User.given - voteValue).where(User.uid == current_user.uid).execute()
            socketio.emit('uscore',
                          {'score': user.score - voteValue},
                          namespace='/snt', room="user" + post.uid.uid)

            socketio.emit('threadscore',
                          {'pid': post.pid, 'score': post.score - voteValue},
                          namespace='/snt', room=post.pid)

            socketio.emit('yourvote', {'pid': post.pid, 'status': 0, 'score': post.score - voteValue}, namespace='/snt',
                          room='user' + current_user.uid)
            

            return jsonify(status='ok', message='Vote removed', score=post.score - voteValue, rm=True)
        else:
            qvote.positive = positive
            qvote.save()

            if positive:
                SubPost.update(score=SubPost.score + (voteValue * 2), upvotes=SubPost.upvotes + 1, downvotes=SubPost.downvotes - 1).where(SubPost.pid == post.pid).execute()
            else:
                SubPost.update(score=SubPost.score + (voteValue * 2), upvotes=SubPost.upvotes - 1, downvotes=SubPost.downvotes + 1).where(SubPost.pid == post.pid).execute()

            User.update(score=User.score + (voteValue * 2)).where(User.uid == post.uid).execute()
            User.update(given=User.given + voteValue).where(User.uid == current_user.uid).execute()

            socketio.emit('uscore',
                            {'score': user.score + voteValue * 2},
                            namespace='/snt',
                            room="user" + post.uid.uid)

            socketio.emit('threadscore',
                          {'pid': post.pid,
                           'score': post.score + voteValue * 2},
                          namespace='/snt',
                          room=post.pid)
            
            socketio.emit('yourvote', {'pid': post.pid, 'status': voteValue, 'score': post.score + voteValue * 2}, namespace='/snt',
                          room='user' + current_user.uid)
            return jsonify(status='ok', message='Vote flipped', score=post.score + voteValue * 2)
    else: # First vote cast on post
        now = datetime.datetime.utcnow()
        sp_vote = SubPostVote.create(pid=pid, uid=current_user.uid, positive=positive, datetime=now)
        sp_vote.save()

        if positive:
            SubPost.update(score=SubPost.score + voteValue, upvotes=SubPost.upvotes + 1).where(SubPost.pid == post.pid).execute()
        else:
            SubPost.update(score=SubPost.score + voteValue, downvotes=SubPost.downvotes + 1).where(SubPost.pid == post.pid).execute()

        socketio.emit('threadscore', {'pid': post.pid, 'score': post.score + voteValue},
                      namespace='/snt', room=post.pid)
        socketio.emit('yourvote', {'pid': post.pid, 'status': voteValue, 'score': post.score + voteValue},
                      namespace='/snt', room='user' + current_user.uid)

        User.update(score=User.score + voteValue).where(User.uid == post.uid).execute()
        User.update(given=User.given + voteValue).where(User.uid == current_user.uid).execute()

        socketio.emit('uscore', {'score': user.score + voteValue},
                      namespace='/snt', room="user" + post.uid.uid)
        
        return jsonify(status='ok', score=post.score + voteValue)


@do.route('/do/sendcomment/<pid>', methods=['POST'])
@login_required
@misc.ratelimit(1, per=30)  # Once every 30 secs
def create_comment(pid):
    """ Here we send comments. """
    form = PostComment()
    if form.validate():
        if pid == '0':
            pid = form.post.data

        try:
            post = SubPost.get(SubPost.pid == pid)
        except SubPost.DoesNotExist:
            return jsonify(status='error', error=['Post does not exist'])
        if post.deleted:
            return jsonify(status='error', error=['Post was deleted'])

        if (datetime.datetime.utcnow() - post.posted) > datetime.timedelta(days=60):
            return jsonify(status='error', error=["Post is archived"])

        sub = db.get_sub_from_sid(post.sid.sid)
        if current_user.is_subban(sub):
            return jsonify(status='error', error=['You are currently banned from commenting'])

        if form.parent.data != '0':
            try:
                parent = SubPostComment.get(SubPostComment.cid == form.parent.data)
            except SubPostComment.DoesNotExist:
                return jsonify(status='error', error=["Parent comment does not exist"])

            # XXX: We check both for None and 0 because I've found both on a Phuks snapshot...
            if (parent.status is not None and parent.status != 0) or parent.pid.pid != post.pid:
                return jsonify(status='error', error=["Parent comment does not exist"])

        comment = SubPostComment.create(pid=pid, uid=current_user.uid,
                                        content=form.comment.data.encode(),
                                        parentcid=form.parent.data if form.parent.data != '0' else None,
                                        time=datetime.datetime.utcnow(),
                                        cid=uuid.uuid4(), score=0, upvotes=0, downvotes=0)
        
        SubPost.update(comments=SubPost.comments + 1).where(SubPost.pid == post.pid).execute()
        comment.save()

        socketio.emit('threadcomments',
                      {'pid': post.pid,
                       'comments': post.comments + 1},
                      namespace='/snt',
                      room=post.pid)

        # 5 - send pm to parent
        if form.parent.data != "0":
            parent = SubPostComment.get(SubPostComment.cid == form.parent.data)
            to = parent.uid.uid
            subject = 'Comment reply: ' + post.title
            mtype = 5
            # XXX: LEGACY
            cache.delete_memoized(db.get_post_comments, post.pid,
                                  form.parent.data)
        else:
            to = post.uid.uid
            subject = 'Post reply: ' + post.title
            mtype = 4
            # XXX: LEGACY
            cache.delete_memoized(db.get_post_comments, post.pid)
            cache.delete_memoized(db.get_post_comments, post.pid, None)
        if to != current_user.uid and current_user.uid not in misc.get_ignores(to):
            misc.create_message(mfrom=current_user.uid,
                                to=to,
                                subject=subject,
                                content='',
                                link=comment.cid,
                                mtype=mtype)
            socketio.emit('notification',
                          {'count': misc.get_notification_count(to)},
                          namespace='/snt',
                          room='user' + to)

        # 6 - Process mentions
        misc.workWithMentions(form.comment.data, to, post, sub, cid=comment.cid)

        return json.dumps({'status': 'ok', 'addr': url_for('sub.view_perm', sub=post.sid.name,
                                                           pid=pid, cid=comment.cid)})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/sendmsg", methods=['POST'])
@login_required
def create_sendmsg():
    """ User PM message creation endpoint """
    form = CreateUserMessageForm()
    if form.validate():
        user = db.get_user_from_name(form.to.data)
        if not user:
            return json.dumps({'status': 'error',
                               'error': ['User does not exist']})
        misc.create_message(mfrom=current_user.uid,
                            to=user['uid'],
                            subject=form.subject.data,
                            content=form.content.data,
                            link=None,
                            mtype=1 if current_user.uid not in misc.get_ignores(user['uid']) else 41)
        socketio.emit('notification',
                      {'count': misc.get_notification_count(user['uid'])},
                      namespace='/snt',
                      room='user' + user['uid'])
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
    if not current_user.is_mod(sub['sid']):
        abort(403)
    form = BanUserSubForm()
    if form.validate():
        user = db.get_user_from_name(form.user.data)
        if not user:
            return json.dumps({'status': 'error',
                               'error': ['User does not exist.']})
        if db.get_sub_metadata(sub['sid'], 'ban', value=user['uid']):
            return jsonify(status='error', error=['Already banned'])
        misc.create_message(mfrom=current_user.uid,
                            to=user['uid'],
                            subject='You have been banned from /s/' +
                            sub['name'],
                            content='Reason: ' + form.reason.data,
                            link=sub['name'],
                            mtype=7)
        socketio.emit('notification',
                      {'count': misc.get_notification_count(user['uid'])},
                      namespace='/snt',
                      room='user' + user['uid'])
        
        SubMetadata.create(sid=sub['sid'], key='ban', value=user['uid']).save()
        SubMetadata.delete().where((SubMetadata.sid==sub['sid']) & (SubMetadata.key == 'xban') & (SubMetadata.value == user['uid'])).execute()

        misc.create_sublog(misc.LOG_TYPE_SUB_BAN, current_user.uid, sub['sid'], target=user['uid'], comment=form.reason.data)

        caching.cache.delete_memoized(db.get_sub_metadata, sub['sid'], 'ban', _all=True)
        return json.dumps({'status': 'ok',
                           'sentby': current_user.get_id()})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/inv_mod2/<sub>", methods=['POST'])
@login_required
def inv_mod2(sub):
    """ User PM for Mod2 invite endpoint """
    sub = db.get_sub_from_name(sub)
    if not sub:
        return json.dumps({'status': 'error',
                           'error': ['Sub does not exist']})
    if current_user.is_topmod(sub['sid']) or current_user.is_admin():
        form = EditMod2Form()
        if form.validate():
            user = db.get_user_from_name(form.user.data)
            if not user:
                return json.dumps({'status': 'error',
                                   'error': ['User does not exist.']})

            if misc.isMod(sub['sid'], user['uid']):
                return json.dumps({'status': 'error',
                                   'error': ['User is already a mod.']})

            if db.get_sub_metadata(sub['sid'], 'mod2i', value=user['uid']):
                return json.dumps({'status': 'error',
                                   'error': ['User has a pending invite.']})

            if misc.moddedSubCount(user['uid']) >= 15:
                return json.dumps({'status': 'error',
                                   'error': [
                                       "User can't mod more than 15 subs"
                                   ]})
            misc.create_message(mfrom=current_user.uid,
                                to=user['uid'],
                                subject='You have been invited to mod a sub.',
                                content=current_user.get_username() +
                                ' has invited you to help moderate ' +
                                sub['name'],
                                link=sub['name'],
                                mtype=2)
            socketio.emit('notification',
                          {'count': misc.get_notification_count(user['uid'])},
                          namespace='/snt',
                          room='user' + user['uid'])
            db.create_sub_metadata(sub['sid'], 'mod2i', user['uid'])

            misc.create_sublog(misc.LOG_TYPE_SUB_MOD_INVITE, current_user.uid, sub['sid'], target=user['uid'],
                               admin=True if (not current_user.is_topmod(sub['sid']) and current_user.is_admin()) else False)

            caching.cache.delete_memoized(db.get_sub_metadata, sub['sid'], 'mod2i', value=user['uid'])

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
    form = DummyForm()
    if form.validate():
        if current_user.is_mod(sub['sid']) or current_user.is_admin():
            if not misc.isSubBan(sub, user):
                return jsonify(status='error', error=['User was not banned'])

            db.uquery('UPDATE `sub_metadata` SET `key`=%s WHERE `key`=%s AND '
                      '`value`=%s', ('xban', 'ban', user['uid']))

            misc.create_message(mfrom=current_user.uid,
                                to=user['uid'],
                                subject='You have been unbanned from /s/' +
                                sub['name'],
                                content='',
                                mtype=7,
                                link=sub['name'])
            socketio.emit('notification',
                          {'count': misc.get_notification_count(user['uid'])},
                          namespace='/snt',
                          room='user' + user['uid'])
            
            misc.create_sublog(misc.LOG_TYPE_SUB_UNBAN, current_user.uid, sub['sid'], target=user['uid'],
                               admin=True if (not current_user.is_mod(sub['sid']) and current_user.is_admin()) else False)

            caching.cache.delete_memoized(db.get_sub_metadata, sub['sid'], 'ban', _all=True)
            caching.cache.delete_memoized(db.get_sub_metadata, sub['sid'], 'xban', _all=True)
            return json.dumps({'status': 'ok', 'msg': 'user ban removed'})
        else:
            abort(403)
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/remove_mod2/<sub>/<user>", methods=['POST'])
@login_required
def remove_mod2(sub, user):
    """ Remove Mod2 """
    user = db.get_user_from_name(user)
    sub = db.get_sub_from_name(sub)
    form = DummyForm()
    if form.validate():
        if current_user.is_topmod(sub['sid']) or current_user.is_admin():
            x = db.get_sub_metadata(sub['sid'], 'mod2', value=user['uid'])
            if not x:
                return jsonify(status='error', error=['User is not mod'])
            
            SubMetadata.delete().where((SubMetadata.sid == sub['sid']) & (SubMetadata.key == 'mod2') & (SubMetadata.value == user['uid'])).execute()
            SubMetadata.create(sid=sub['sid'], key='xmod2', value=user['uid']).save()

            misc.create_sublog(misc.LOG_TYPE_SUB_MOD_REMOVE, current_user.uid, sub['sid'], target=user['uid'],
                               admin=True if (not current_user.is_topmod(sub['sid']) and current_user.is_admin()) else False)

            caching.cache.delete_memoized(db.get_sub_metadata, sub['sid'], 'mod2', _all=True)
            return json.dumps({'status': 'ok', 'msg': 'user demodded'})
        else:
            abort(403)
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/revoke_mod2inv/<sub>/<user>", methods=['POST'])
@login_required
def revoke_mod2inv(sub, user):
    """ revoke Mod2 inv """
    user = db.get_user_from_name(user)
    sub = db.get_sub_from_name(sub)
    form = DummyForm()
    if form.validate():
        if current_user.is_topmod(sub['sid']) or current_user.is_admin():
            x = db.get_sub_metadata(sub['sid'], 'mod2i', value=user['uid'])
            if not x:
                return jsonify(status='error', error=['User is not mod'])
            db.uquery('DELETE FROM `sub_metadata` WHERE `key`=%s AND `value`=%s',
                      ('mod2i', user['uid']))

            misc.create_sublog(misc.LOG_TYPE_SUB_MOD_INV_CANCEL, current_user.uid, sub['sid'], target=user['uid'],
                               admin=True if (not current_user.is_topmod(sub['sid']) and current_user.is_admin()) else False)

            caching.cache.delete_memoized(db.get_sub_metadata, sub['sid'], 'mod2i', _all=True)
            return json.dumps({'status': 'ok', 'msg': 'user invite revoked'})
        else:
            abort(403)
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/accept_mod2inv/<sub>/<user>", methods=['POST'])
@login_required
def accept_mod2inv(sub, user):
    """ Accept mod invite """
    user = db.get_user_from_name(user)
    if user['uid'] != current_user.get_id():
        abort(403)
    sub = db.get_sub_from_name(sub)
    form = DummyForm()
    if form.validate():
        if misc.isModInv(sub['sid'], user):
            if misc.moddedSubCount(user['uid']) >= 15:
                return json.dumps({'status': 'error',
                                   'error': ["You can't mod more than 15 subs"]})
            
            SubMetadata.update(key='mod2').where((SubMetadata.sid == sub['sid']) & (SubMetadata.key == 'mod2i') & (SubMetadata.value == user['uid'])).execute()
            SubMetadata.delete().where((SubMetadata.sid == sub['sid']) & (SubMetadata.key == 'xmod2') & (SubMetadata.value == user['uid'])).execute()

            misc.create_sublog(misc.LOG_TYPE_SUB_MOD_ACCEPT, current_user.uid, sub['sid'], target=user['uid'])

            if not current_user.has_subscribed(sub['name']):
                db.create_subscription(current_user.uid, sub['sid'], 1)
            caching.cache.delete_memoized(db.get_sub_metadata, sub['sid'], 'mod2', _all=True)
            caching.cache.delete_memoized(db.get_sub_metadata, sub['sid'], 'mod2i', _all=True)
            caching.cache.delete_memoized(db.get_sub_metadata, sub['sid'], 'mod2i', value=user['uid'])
            return json.dumps({'status': 'ok', 'msg': 'user modded'})
        else:
            abort(404)
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/refuse_mod2inv/<sub>/<user>", methods=['POST'])
@login_required
def refuse_mod2inv(sub, user):
    """ refuse Mod2 """
    user = db.get_user_from_name(user)
    sub = db.get_sub_from_name(sub)
    if user['uid'] != current_user.get_id():
        abort(403)

    form = DummyForm()
    if form.validate():
        if misc.isModInv(sub['sid'], user):
            SubMetadata.delete().where((SubMetadata.sid == sub['sid']) & (SubMetadata.key == 'mod2i') & (SubMetadata.value == user['uid'])).execute()

            misc.create_sublog(misc.LOG_TYPE_SUB_MOD_INV_REJECT, current_user.uid, sub['sid'], target=user['uid'])

            caching.cache.delete_memoized(db.get_sub_metadata, sub['sid'], 'mod2i', _all=True)
            caching.cache.delete_memoized(db.get_sub_metadata, sub['sid'], 'mod2i', value=user['uid'])
            return json.dumps({'status': 'ok', 'msg': 'invite refused'})
        else:
            abort(404)
    return json.dumps({'status': 'error', 'error': get_errors(form)})


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
        socketio.emit('notification',
                      {'count': current_user.notifications},
                      namespace='/snt',
                      room='user' + current_user.uid)
        return json.dumps({'status': 'ok', 'mid': mid})
    else:
        abort(403)


@do.route("/do/readall_msgs/<boxid>", methods=['POST'])
@login_required
def readall_msgs(boxid):
    """ Mark all messages in a box as read """
    now = datetime.datetime.utcnow()
    q = Message.update(read=now).where(Message.read.is_null()).where(Message.receivedby == current_user.uid)
    q.where(Message.mtype == boxid).execute()
    socketio.emit('notification',
                  {'count': current_user.notifications},
                  namespace='/snt',
                  room='user' + current_user.uid)
    return jsonify(status='ok')


@do.route("/do/delete_pm/<mid>", methods=['POST'])
@login_required
def delete_pm(mid):
    """ Delete PM """
    try:
        message = Message.get(Message.mid == mid)
        if message.receivedby != current_user.uid:
            return jsonify(status='error', error="Message does not exist")
        
        message.mtype = 6
        message.save()
        return jsonify(status='ok')
    except Message.DoesNotExist:
        return jsonify(status='error', error="Message does not exist")


@do.route("/do/edit_title", methods=['POST'])
@login_required
def edit_title():
    form = DeletePost()
    if form.validate():
        if not form.reason.data:
            return jsonify(status="error", error="Missing title")

        if len(form.reason.data.strip(misc.WHITESPACE)) < 3:
            return jsonify(status="error", error="Title too short.")

        try:
            post = SubPost.get(SubPost.pid == form.post.data)
        except SubPost.DoesNotExist:
            return jsonify(status="error", error="Post does not exist")
        sub = Sub.get(Sub.sid == post.sid)
        if current_user.is_subban(sub):
            return jsonify(status='error', error='You are banned on this sub.')

        if (datetime.datetime.utcnow() - post.posted) > datetime.timedelta(seconds=300):
            return jsonify(status="error", error="You cannot edit the post title anymore")

        if post.uid.uid != current_user.uid:
            return jsonify(status="error", error="You did not post this!")

        post.title = form.reason.data
        post.save()
        return jsonify(status="ok")
    return jsonify(status="error", error="Bork bork")


@do.route("/do/save_pm/<mid>", methods=['POST'])
@login_required
def save_pm(mid):
    """ Save/Archive PM """
    try:
        message = Message.get(Message.mid == mid)
        if message.receivedby != current_user.uid:
            return jsonify(status='error', error="Message does not exist")
        
        message.mtype = 9
        message.save()
        return jsonify(status='ok')
    except Message.DoesNotExist:
        return jsonify(status='error', error="Message does not exist")


@do.route("/do/admin/deleteannouncement")
@login_required
def deleteannouncement():
    """ Removes the current announcement """
    if not current_user.is_admin():
        abort(403)

    try:
        ann = SiteMetadata.get(SiteMetadata.key == 'announcement')
        post = SubPost.get(SubPost.pid == ann.value)
    except SiteMetadata.DoesNotExist:
        return redirect(url_for('admin_area'))

    ann.delete_instance()
    misc.create_sitelog(misc.LOG_TYPE_UNANNOUNCE, uid=current_user.uid, link=url_for('sub.view_post', sub=post.sid.name, pid=post.pid))

    cache.delete_memoized(misc.getAnnouncementPid)
    socketio.emit('rmannouncement', {}, namespace='/snt')
    return redirect(url_for('admin_area'))


@do.route("/do/makeannouncement", methods=['POST'])
def make_announcement():
    """ Flagging post as announcement - not api """
    if not current_user.is_admin():
        abort(403)

    form = DeletePost()

    if form.validate():
        try:
            curr_ann = SiteMetadata.get(SiteMetadata.key == 'announcement')
            if curr_ann.value == form.post.data:
                return jsonify(status='error', error='Post already announced')
            deleteannouncement()
        except SiteMetadata.DoesNotExist:
            pass

        try:
            post = SubPost.get(SubPost.pid == form.post.data)
        except SubPost.DoesNotExist:
            return jsonify(status='error', error='Post does not exist')

        SiteMetadata.create(key='announcement', value=post.pid)

        misc.create_sitelog(misc.LOG_TYPE_ANNOUNCEMENT, uid=current_user.uid, link=url_for('sub.view_post', sub=post.sid.name, pid=post.pid))

        cache.delete_memoized(misc.getAnnouncementPid)
        socketio.emit('announcement',
                      {"cont": engine.get_template('shared/announcement.html').render({"ann": misc.getAnnouncement()})},
                      namespace='/snt')
        return jsonify(status='ok')
    return jsonify(status='error', error=get_errors(form))


@do.route("/do/ban_domain", methods=['POST'])
def ban_domain():
    """ Add domain to ban list """
    if not current_user.is_admin():
        abort(403)

    form = BanDomainForm()

    if form.validate():
        try:
            sm = SiteMetadata.get((SiteMetadata.key == 'banned_domain') & (SiteMetadata.value == form.domain.data))
            return jsonify(status='error', error='Domain is already banned')
        except SiteMetadata.DoesNotExist:
            sm = SiteMetadata.create(key='banned_domain', value=form.domain.data)
            sm.save()
            sc.create_sitelog(misc.LOG_TYPE_DOMAIN_BAN, current_user.uid, comment=domain)
            return jsonify(status='ok')

    return jsonify(status='error', error=get_errors(form))


@do.route("/do/remove_banned_domain/<domain>", methods=['POST'])
def remove_banned_domain(domain):
    """ Remove domain if ban list """
    if not current_user.is_admin():
        abort(403)

    try:
        sm = SiteMetadata.get((SiteMetadata.key == 'banned_domain') & (SiteMetadata.value == domain))
        sm.delete_instance()
    except:
        return jsonify(status='error', error='Domain is not banned')

    misc.create_sitelog(misc.LOG_TYPE_DOMAIN_UNBAN, current_user.uid, comment=domain)

    return json.dumps({'status': 'ok'})


@do.route("/do/admin/enable_posting/<value>")
def enable_posting(value):
    """ Emergency Mode: disable posting """
    if not current_user.is_admin():
        abort(404)

    c = db.query('SELECT * FROM `site_metadata` WHERE `key`=%s',
                 ('enable_posting',)).fetchone()
    if c:
        db.update_site_metadata('enable_posting', value)
    else:
        db.create_site_metadata('enable_posting', value)
    if value == 'True':
        db.create_sitelog(5, current_user.get_username() + ' enabled posting ')
    else:
        db.create_sitelog(5, current_user.get_username() + ' disabled posting ')
    caching.cache.delete_memoized(db.get_site_metadata, 'enable_posting')
    cache.delete_memoized(db.get_site_metadata, 'enable_posting')
    return redirect(url_for('admin_area'))


@do.route("/do/save_post/<pid>", methods=['POST'])
def save_post(pid):
    """ Save a post to your Saved Posts """
    if db.get_user_saved(current_user.uid, pid):
        return json.dumps({'status': 'error', 'error': ['Already saved']})

    db.create_user_saved(current_user.uid, pid)
    return json.dumps({'status': 'ok'})


@do.route("/do/remove_saved_post/<pid>", methods=['POST'])
def remove_saved_post(pid):
    """ Remove a saved post """
    if not db.get_user_saved(current_user.uid, pid):
        return json.dumps({'status': 'error', 'error': ['Already deleted']})

    db.uquery('DELETE FROM `user_saved` WHERE `uid`=%s AND `pid`=%s',
              (current_user.uid, pid))
    return json.dumps({'status': 'ok'})


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
            desc = current_user.get_username() + ' enabled btc donations: ' + form.btcaddress.data
        else:
            desc = current_user.get_username() + ' disabled btc donations'
        db.create_sitelog(10, desc, '')
        return json.dumps({'status': 'ok'})
    return redirect(url_for('admin_area'))


@do.route("/do/useinvitecode", methods=['POST'])
def use_invite_code():
    """ Enable invite code to register """
    if not current_user.is_admin():
        abort(404)

    form = UseInviteCodeForm()

    if form.validate():
        db.update_site_metadata('useinvitecode', form.enableinvitecode.data)
        db.update_site_metadata('invitecode', form.invitecode.data)

        if form.enableinvitecode.data:
            desc = current_user.get_username() + ' enabled invite code requirement'
        else:
            desc = current_user.get_username() + ' disabled invite code requirement'
        db.create_sitelog(7, desc, '')
        # return json.dumps({'status': 'ok'})
    return redirect(url_for('admin_area'))


@do.route("/do/stick/<int:post>", methods=['POST'])
def toggle_sticky(post):
    """ Toggles post stickyness """
    try:
        post = SubPost.get(SubPost.pid == post)
    except SubPost.DoesNotExist:
        return jsonify(status='error', error='Post does not exist')
    

    if not current_user.is_mod(post.sid_id):
        abort(403)

    form = DeletePost()

    if form.validate():
        try:
            is_sticky = SubMetadata.get((SubMetadata.sid == post.sid_id) & (SubMetadata.key == 'sticky') & (SubMetadata.value == post.pid))
            is_sticky.delete_instance()
            misc.create_sublog(misc.LOG_TYPE_SUB_STICKY_DEL, current_user.uid, post.sid,
                               link=url_for('sub.view_post', sub=post.sid.name, pid=post.pid))
        except SubMetadata.DoesNotExist:
            post.sid.update_metadata('sticky', post.pid)
            misc.create_sublog(misc.LOG_TYPE_SUB_STICKY_ADD, current_user.uid, post.sid,
                    link=url_for('sub.view_post', sub=post.sid.name, pid=post.pid))

        cache.delete_memoized(misc.getStickyPid, post.sid_id)
    return jsonify(status='ok')


@do.route("/do/flair/<sub>/delete", methods=['POST'])
@login_required
def delete_flair(sub):
    """ Removes a flair (from edit flair page) """
    sub = db.get_sub_from_name(sub)
    if not sub:
        abort(404)

    if not current_user.is_mod(sub['sid']) and not current_user.is_admin():
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
    try:
        sub = Sub.get(Sub.name == sub)
    except Sub.DoesNotExist:
        abort(404)

    if not current_user.is_mod(sub.sid) and not current_user.is_admin():
        abort(403)

    form = CreateSubFlair()
    if form.validate():
        allowed_flairs = re.compile("^[a-zA-Z0-9._ -]+$")
        if not allowed_flairs.match(form.text.data):
            return jsonify(status='error', error=['Flair has invalid characters'])

        SubFlair.create(sid=sub.sid, text=form.text.data)
        return jsonify(status='ok')
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/edit_multi", methods=['POST'])
@login_required
def edit_multi():
    """ Edits multi """
    form = EditMulti()
    if form.validate():
        mid = form.multi.data
        multi = db.get_user_multi(mid)
        if not multi:
            return json.dumps({'status': 'error',
                               'error': ['Multi does not exist']})
        names = str(form.subs.data).split('+')
        sids = ''
        for sub in names:
            sub = db.get_sub_from_name(sub)
            if sub:
                sids += str(sub['sid']) + '+'
            else:
                return json.dumps({'status': 'error',
                                   'error': ['Invalid sub in list']})
        db.uquery('UPDATE `user_multi` SET `name`=%s, `subs`=%s, `sids`=%s '
                  'WHERE `mid`=%s ',
                  (form.name.data, form.subs.data, sids[:-1],
                   form.multi.data))

        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/delete_multi", methods=['POST'])
@login_required
def delete_multi():
    """ Removes a multi """
    form = DeleteMulti()
    if form.validate():
        mid = form.multi.data
        multi = db.get_user_multi(mid)
        if not multi:
            return json.dumps({'status': 'error',
                               'error': ['Multi does not exist']})
        db.uquery('DELETE FROM `user_multi` WHERE `mid`=%s ',
                  (mid, ))

        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/create_multi", methods=['POST'])
@login_required
def create_multi():
    """ Creates a new multi """
    form = CreateMulti()
    if form.validate():
        if db.get_usermulti_count(current_user.uid) >= 10:
            return json.dumps({'status': 'error',
                               'error': ['Only 10 allowed for now']})

        multiname = db.query('SELECT * FROM `user_multi` WHERE `uid`=%s '
                             'AND `name`=%s',
                             (current_user.uid, form.name.data))
        if multiname.fetchone():
            return json.dumps({'status': 'error',
                               'error': ['Name already in list']})
        names = str(form.subs.data).split('+')
        sids = ''
        for sub in names:
            sub = db.get_sub_from_name(sub)
            if sub:
                sids += str(sub['sid']) + '+'
            else:
                return json.dumps({'status': 'error',
                                   'error': ['Invalid sub in list']})

        db.uquery('INSERT INTO `user_multi` (`uid`, `name`, `subs`, `sids`) '
                  'VALUES (%s, %s, %s, %s)',
                  (current_user.uid, form.name.data, form.subs.data,
                   sids[:-1]))
        return json.dumps({'status': 'ok'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route("/do/recovery", methods=['POST'])
def recovery():
    """ Password recovery page. Email+captcha and sends recovery email """
    if current_user.is_authenticated:
        abort(403)

    form = forms.PasswordRecoveryForm()
    if form.validate():
        try:
            user = User.get(User.email == form.email.data)
        except User.DoesNotExist:
            return jsonify(status="ok")  # Silently fail every time.

        # User exists, check if they don't already have a key sent
        try:
            key = UserMetadata.get((UserMetadata.uid == user.uid) & (UserMetadata.key == 'recovery-key'))
            keyExp = UserMetadata.get((UserMetadata.uid == user.uid) & (UserMetadata.key == 'recovery-key-time'))
            expiration = float(keyExp.value)
            if (time.time() - expiration) > 86400:  # 1 day
                # Key is old. remove it and proceed
                key.delete_instance()
                keyExp.delete_instance()
            else:
                return jsonify(status="ok")
        except UserMetadata.DoesNotExist:
            pass

        # checks done, doing the stuff.
        rekey = uuid.uuid4()
        UserMetadata.create(uid=user.uid, key='recovery-key', value=rekey)
        UserMetadata.create(uid=user.uid, key='recovery-key-time', value=time.time())

        sendMail(
            subject='Password recovery',
            to=user.email,
            content="""<h1><strong>{0}</strong></h1>
            <p>Somebody (most likely you) has requested a password reset for
            your account</p>
            <p>To proceed, visit the following address (valid for the next 24hs)</p>
            <a href="{1}">{1}</a>
            <hr>
            <p>If you didn't request a password recovery, please ignore this
            email</p>
            """.format(config.LEMA, url_for('password_reset', key=rekey,
                                            uid=user.uid, _external=True))
        )

        return jsonify(status="ok")
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
        login_user(misc.load_user(user['uid']))
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
        post = SubPost.get(SubPost.pid == comment['pid'])
        sub = Sub.get(Sub.sid == post.sid)
        if current_user.is_subban(sub):
            return jsonify(status='error', error=['You are banned on this sub.'])

        if comment['status'] == '1':
            return jsonify(status='error',
                           error="You can't edit a deleted comment")
        dt = datetime.datetime.utcnow()
        db.uquery('UPDATE `sub_post_comment` SET `content`=%s, `lastedit`=%s '
                  'WHERE `cid`=%s', (form.text.data, dt, form.cid.data))
        return jsonify(status='ok')
    return json.dumps({'status': 'error', 'error': get_errors(form)[0]})


@do.route("/do/delete_comment", methods=['POST'])
@login_required
def delete_comment():
    """ deletes a comment """
    form = forms.DeleteCommentForm()
    if form.validate():
        comment = db.get_comment_from_cid(form.cid.data)
        post = SubPost.get(SubPost.pid == comment['pid'])
        if not comment:
            abort(404)

        if comment['uid'] != current_user.uid and not (current_user.is_admin() or current_user.is_mod(post.sid)):
            abort(403)

        if comment['uid'] != current_user.uid and (current_user.is_admin() or current_user.is_mod(post.sid)):
            misc.create_sublog(misc.LOG_TYPE_SUB_DELETE_COMMENT, current_user.uid, post.sid,
                               comment=form.reason.data, link=url_for('view_post_inbox', pid=comment['pid']),
                               admin=True if (not current_user.is_mod(post.sid) and current_user.is_admin()) else False)

        db.uquery('UPDATE `sub_post_comment` SET `status`=1 WHERE `cid`=%s',
                  (form.cid.data,))

        q = Message.delete().where(Message.mlink == form.cid.data)
        q.execute()
        return jsonify(status='ok')
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route('/do/votecomment/<cid>/<value>', methods=['POST'])
@login_required
def upvotecomment(cid, value):
    """ Logs an upvote to a post. """
    form = DummyForm()
    if not form.validate():
        return json.dumps({'status': 'error', 'error': get_errors(form)})

    if value == "up":
        voteValue = 1
    elif value == "down":
        voteValue = -1
        if current_user.get_given()[2] < 0:
            return jsonify(status='error', error=['Score balance is negative'])
    else:
        abort(403)
        
    try:
        comment = SubPostComment.get(SubPostComment.cid == cid)
    except SubPostComment.DoesNotExist:
        return jsonify(status="error", error=['Comment does not exist'])

    if comment.status is not None and comment.status != 0:
        return jsonify(status="error", error=['Comment does not exist'])

    user = comment.uid
    if user.uid == current_user.get_id():
        return json.dumps({'status': 'error',
                           'error': ['You can\'t vote on your own comments']})

    post = SubPost.get(SubPost.pid == comment.pid)
    if (datetime.datetime.utcnow() - post.posted) > datetime.timedelta(days=60):
        return jsonify(status='error', error=["Post is archived"])

    if current_user.is_subban(post.sid):
        return jsonify(status='error', error=['You are banned on this sub.'])

    qvote = db.query('SELECT * FROM `sub_post_comment_vote` WHERE `cid`=%s AND'
                     ' `uid`=%s', (cid, current_user.uid)).fetchone()

    if qvote:
        if bool(qvote['positive']) == (True if voteValue == 1 else False):
            SubPostCommentVote.delete().where(SubPostCommentVote.xid == qvote['xid']).execute()
            if voteValue == 1:
                kw = {'upvotes': SubPostComment.upvotes - 1}
            elif voteValue == -1:
                kw = {'downvotes': SubPostComment.downvotes - 1}
            SubPostComment.update(score=SubPostComment.score - voteValue, **kw).where(SubPostComment.cid == cid).execute()
            User.update(score=User.score - voteValue).where(User.uid == comment.uid).execute()
            User.update(given=User.given - voteValue).where(User.uid == current_user.uid).execute()

            socketio.emit('uscore',
                          {'score': user.score - voteValue},
                          namespace='/snt', room="user" + comment.uid.uid)

            return jsonify(status='ok', message='Vote removed', score=comment.score - voteValue, rm=True)
        else:
            positive = True if voteValue == 1 else False
            db.uquery('UPDATE `sub_post_comment_vote` SET `positive`=%s WHERE '
                      '`xid`=%s', (positive, qvote['xid']))
            
            if positive:
                kw = {'upvotes': SubPostComment.upvotes + 1, 'downvotes': SubPostComment.downvotes - 1}
            else:
                kw = {'upvotes': SubPostComment.upvotes - 1, 'downvotes': SubPostComment.downvotes + 1}

            SubPostComment.update(score=SubPostComment.score + (voteValue * 2), **kw).where(SubPostComment.cid == cid).execute()
            if user.score is not None:
                db.uquery('UPDATE `user` SET `score`=`score`+%s WHERE '
                          '`uid`=%s', (voteValue * 2, user.uid))
                socketio.emit('uscore',
                              {'score': user.score + voteValue * 2},
                              namespace='/snt',
                              room="user" + user.uid)
            return jsonify(status='ok', message='Vote flipped', score=comment.score + voteValue * 2)
    else:
        positive = True if voteValue == 1 else False
        now = datetime.datetime.utcnow()
        db.uquery('INSERT INTO `sub_post_comment_vote` (`cid`, `uid`, '
                  '`positive`, `datetime`) VALUES (%s, %s, %s, %s)',
                  (cid, current_user.uid, positive, now))

    if voteValue == 1:
        kw = {'upvotes': SubPostComment.upvotes + 1}
    elif voteValue == -1:
        kw = {'downvotes': SubPostComment.downvotes + 1}
    SubPostComment.update(score=SubPostComment.score + voteValue, **kw).where(SubPostComment.cid == cid).execute()

    if user.score is not None:
        db.uquery('UPDATE `user` SET `score`=`score`+%s WHERE '
                  '`uid`=%s', (voteValue, user.uid))
        socketio.emit('uscore',
                      {'score': user.score + voteValue},
                      namespace='/snt',
                      room="user" + user.uid)

    return jsonify(status='ok', score=comment.score + voteValue)


@do.route('/do/get_children/<pid>/<cid>', methods=['POST'])
def get_children(pid, cid):
    """ Gets children comments for <cid> """
    # TODO: Remove this pile of crap.
    # Note for future self: Wondering why I added this steaming pile of shit after the rewrite?
    # It's the only way to make this work, unless you're in a pretty distant future
    # where MySQL 8 or MariaDB 10.2 are already mainstream. If not, I wish you good luck. You're gonna need it.
    cmskel = db.query("SELECT t1.cid AS lev1, t2.cid as lev2, t3.cid as lev3, t4.cid as lev4, t5.cid as lev5 FROM sub_post_comment AS t1 "
                      "LEFT JOIN sub_post_comment AS t2 ON t2.parentcid = t1.cid LEFT JOIN sub_post_comment AS t3 ON t3.parentcid = t2.cid "
                      "LEFT JOIN sub_post_comment AS t4 ON t4.parentcid = t3.cid LEFT JOIN sub_post_comment AS t5 ON t5.parentcid = t4.cid WHERE t1.cid =%s", (cid, ))
    if cmskel.rowcount == 0:
        return jsonify(status='ok', posts=[])
    comms = []
    for pp in cmskel.fetchall():
        comms.append({'parentcid': pp['lev1'], 'cid': pp['lev2']})
        if pp['lev3']:
            comms.append({'parentcid': pp['lev2'], 'cid': pp['lev3']})
            if pp['lev4']:
                comms.append({'parentcid': pp['lev3'], 'cid': pp['lev4']})
                if pp['lev5']:
                    comms.append({'parentcid': pp['lev4'], 'cid': pp['lev5']})
    comms = [dict(t) for t in set([tuple(d.items()) for d in comms])]

    cmxk = misc.build_comment_tree(comms, cid)
    post = SubPost.select(SubPost.pid, SubPost.sid).where(SubPost.pid == pid).get()
    sub = Sub.select(Sub.name).where(Sub.sid == post.sid).get()
    return render_template('postcomments.html', sub=sub, post=post, comments=misc.expand_comment_tree(cmxk))


@do.route('/do/get_sibling/<int:pid>/<cid>/<int:page>', methods=['POST', 'GET'])
def get_sibling(pid, cid, page):  # XXX: Really similar to get_children. Should merge them in the future
    """ Gets children comments for <cid> """
    if cid == '1':
        cid = None
        ppage = 8  # We initially load 8 root comments ...
    else:
        ppage = 5

    cmskel = SubPostComment.select(SubPostComment.cid, SubPostComment.parentcid)
    cmskel = cmskel.where(SubPostComment.pid == pid).order_by(SubPostComment.score.desc()).dicts()
    if cmskel.count() == 0:
        return jsonify(status='ok', posts=[])
    cmxk = misc.build_comment_tree(cmskel, cid, perpage=ppage, pageno=page + 1)
    post = SubPost.select(SubPost.pid, SubPost.sid).where(SubPost.pid == pid).get()
    sub = Sub.select(Sub.name).where(Sub.sid == post.sid).get()
    return render_template('postcomments.html', sub=sub, post=post, comments=misc.expand_comment_tree(cmxk), siblingpage=page + 1)


@do.route('/do/preview', methods=['POST'])
@login_required
def preview():
    """ Returns parsed markdown. Used for post and comment previews. """
    form = DummyForm()
    if form.validate():
        if request.json.get('text'):
            return jsonify(status='ok', text=misc.our_markdown(request.json.get('text')))
        else:
            return jsonify(status='error', error='Missing text')
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route('/do/nsfw', methods=['POST'])
@login_required
def toggle_nsfw():
    """ Toggles NSFW tag on posts """
    form = DeletePost()

    if form.validate():
        try:
            post = SubPost.get(SubPost.pid == form.post.data)
        except SubPost.DoesNotExist:
            return json.dumps({'status': 'error', 'error': 'Post does not exist'})

        if current_user.uid == post.uid_id or current_user.is_admin() or current_user.is_mod(post.sid):
            post.nsfw = 1 if post.nsfw == 0 else 0
            post.save()
            return json.dumps({'status': 'ok', 'msg': 'NSFW set to {0}'.format(bool(post.nsfw))})
        else:
            return json.dumps({'status': 'error', 'error': 'Not authorized'})
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route('/do/toggle_ignore/<uid>', methods=['POST'])
@login_required
def ignore_user(uid):
    try:
        user = User.get(User.uid == uid)
    except User.DoesNotExist:
        return jsonify(status='error', error='User not found')

    try:
        uig = UserIgnores.get((UserIgnores.uid == current_user.uid) & (UserIgnores.target == uid))
        uig.delete_instance()
        return jsonify(status='ok', action='delete')
    except UserIgnores.DoesNotExist:
        uig = UserIgnores.create(uid=current_user.uid, target=user.uid)
        return jsonify(status='ok', action='ignore')


@do.route('/do/upload/<sub>', methods=['POST'])
@login_required
def sub_upload(sub):
    try:
        sub = Sub.get(Sub.name == sub)
    except Sub.DoesNotExist:
        abort(404)

    if not current_user.is_mod(sub.sid) and not current_user.is_admin():
        abort(403)

    c = SubStylesheet.get(SubStylesheet.sid == sub.sid)
    form = EditSubCSSForm(css=c.source)
    # get remaining space
    remaining = 1024 * 1024 * 2  # 2M
    ufiles = SubUploads.select().where(SubUploads.sid == sub.sid)
    for uf in ufiles:
        remaining -= uf.size

    fname = request.form.get('name')
    if len(fname) > 10:
        return engine.get_template('sub/css.html').render({'sub': sub, 'form': form, 'storage': int(remaining - (1024 * 1024)),
                                                           'error': 'File name too long.', 'files': ufiles})

    if len(fname) < 3:
        return engine.get_template('sub/css.html').render({'sub': sub, 'form': form, 'storage': int(remaining - (1024 * 1024)),
                                                           'error': 'File name too short or missing.', 'files': ufiles})

    if not allowedNames.match(fname):
        return engine.get_template('sub/css.html').render({'sub': sub, 'form': form, 'storage': int(remaining - (1024 * 1024)),
                                                           'error': 'Invalid file name.', 'files': ufiles})

    ufile = request.files.getlist('files')[0]
    if ufile.filename == '':
        return engine.get_template('sub/css.html').render({'sub': sub, 'form': form, 'storage': int(remaining - (1024 * 1024)),
                                                           'error': 'Please select a file to upload.', 'files': ufiles})

    mtype = magic.from_buffer(ufile.read(1024), mime=True)

    if mtype == 'image/jpeg':
        extension = '.jpg'
    elif mtype == 'image/png':
        extension = '.png'
    elif mtype == 'image/gif':
        extension = '.gif'
    else:
        return engine.get_template('sub/css.html').render({'sub': sub, 'form': form, 'storage': int(remaining - (1024 * 1024)),
                                                           'error': 'Invalid file type. Only jpg, png and gif allowed.', 'files': ufiles})

    ufile.seek(0)
    md5 = hashlib.md5()
    while True:
        data = ufile.read(65536)
        if not data:
            break
        md5.update(data)

    f_name = str(uuid.uuid5(misc.FILE_NAMESPACE, md5.hexdigest())) + extension
    ufile.seek(0)
    lm = False
    if not os.path.isfile(os.path.join(config.STORAGE, f_name)):
        lm = True
        ufile.save(os.path.join(config.STORAGE, f_name))
        # remove metadata
        if mtype != 'image/gif':  # Apparently we cannot write to gif images
            md = pyexiv2.ImageMetadata(os.path.join(config.STORAGE, f_name))
            md.read()
            for k in (md.exif_keys + md.iptc_keys + md.xmp_keys):
                del md[k]
            md.write()
    # sadly, we can only get file size accurately after saving it
    fsize = os.stat(os.path.join(config.STORAGE, f_name)).st_size
    if fsize > remaining:
        if lm:
            os.remove(os.path.join(config.STORAGE, f_name))
        return engine.get_template('sub/css.html').render({'sub': sub, 'form': form, 'storage': int(remaining - (1024 * 1024)),
                                                           'error': 'Not enough available space to upload file.', 'files': ufiles})
    # THUMBNAIL
    ufile.seek(0)
    im = Image.open(ufile).convert('RGB')
    x, y = im.size
    while y > x:
        slice_height = min(y - x, 10)
        bottom = im.crop((0, y - slice_height, x, y))
        top = im.crop((0, 0, x, slice_height))

        if misc._image_entropy(bottom) < misc._image_entropy(top):
            im = im.crop((0, 0, x, y - slice_height))
        else:
            im = im.crop((0, slice_height, x, y))

        x, y = im.size

    im.thumbnail((70, 70), Image.ANTIALIAS)

    im.seek(0)
    md5 = hashlib.md5(im.tobytes())
    filename = str(uuid.uuid5(misc.THUMB_NAMESPACE, md5.hexdigest())) + '.jpg'
    im.seek(0)
    if not os.path.isfile(os.path.join(config.THUMBNAILS, filename)):
        im.save(os.path.join(config.THUMBNAILS, filename), "JPEG", optimize=True, quality=85)
    im.close()

    SubUploads.create(sid=sub.sid, fileid=f_name, thumbnail=filename, size=fsize, name=fname)
    SubLog.create(sid=sub.sid, action=4, link=url_for('sub.view_sub', sub=sub.name), time=datetime.datetime.utcnow(),
                      desc='{0} modified the sub\'s stylesheet (uploaded file)'.format(current_user.name))
    return redirect(url_for('sub.edit_sub_css', sub=sub.name))


@do.route('/do/upload/<sub>/delete/<name>', methods=['POST'])
@login_required
def sub_upload_delete(sub, name):
    try:
        sub = Sub.get(Sub.name == sub)
    except Sub.DoesNotExist:
        jsonify(status='error')  # descriptive errors where?
    form = DummyForm()
    if not form.validate():
        return redirect(url_for('sub.edit_sub_css', sub=sub.name))
    if not current_user.is_mod(sub.sid) and not current_user.is_admin():
        jsonify(status='error')

    try:
        img = SubUploads.get((SubUploads.sid == sub.sid) & (SubUploads.name == name))
    except SubUploads.DoesNotExist:
        jsonify(status='error')
    fileid = img.fileid
    img.delete_instance()
    SubLog.create(sid=sub.sid, action=4, link=url_for('sub.view_sub', sub=sub.name), time=datetime.datetime.utcnow(),
                      desc='{0} modified the sub\'s stylesheet (removed upload)'.format(current_user.name))

    # We won't delete the pic if somebody else is still using it..
    try:
        UserUploads.get(UserUploads.fileid == fileid)
    except UserUploads.DoesNotExist:
        try:
            SubUploads.get(SubUploads.fileid == img.fileid)
        except SubUploads.DoesNotExist:
            os.remove(os.path.join(config.STORAGE, img.fileid))

    return jsonify(status='ok')


@do.route('/do/admin/create_question', methods=['POST'])
@login_required
def create_question():
    if not current_user.is_admin():
        abort(403)

    form = SecurityQuestionForm()

    if form.validate():
        SiteMetadata.create(key='secquestion', value=form.question.data + '|' + form.answer.data)
        return jsonify(status='ok')
    return jsonify(status='error')


@do.route('/do/admin/delete_question/<xid>', methods=['POST'])
@login_required
def delete_question(xid):
    if not current_user.is_admin():
        abort(403)

    form = DummyForm()
    if not form.validate():
        return jsonify(status='error')
    try:
        th = SiteMetadata.get((SiteMetadata.key == 'secquestion') & (SiteMetadata.xid == xid))
    except SiteMetadata.DoesNotExist:
        return jsonify(status='error')
    th.delete_instance()
    return jsonify(status='ok')


@do.route('/do/admin/ban_user/<username>', methods=['POST'])
@login_required
def ban_user(username):
    if not current_user.is_admin():
        abort(403)

    form = DummyForm()
    if not form.validate():
        abort(403)

    try:
        user = User.get(User.name == username)
    except User.DoesNotExist:
        abort(404)

    user.status = 5
    user.save()
    misc.create_sitelog(misc.LOG_TYPE_USER_BAN, uid=current_user.uid, comment=user.name)
    return redirect(url_for('view_user', user=username))


@do.route('/do/edit_top_bar', methods=['POST'])
@login_required
def edit_top_bar():
    form = DummyForm()
    if not form.validate():
        return jsonify(status='error', error='no CSRF')

    data = request.get_json()
    if not data.get('sids'):
        return jsonify(status='error')

    for i in data.get('sids'):
        # Check if we're being fed good UUIDs
        try:
            val = uuid.UUID(i, version=4)
        except ValueError:
            return jsonify(status='error')

    # If all the sids are good, we do the thing.
    i = 0
    for k in data.get('sids'):
        i += 1
        try:
            SubSubscriber.update(order=i).where((SubSubscriber.uid == current_user.uid) & (SubSubscriber.sid == k)).execute()
        except SubSubscriber.DoesNotExist:
            pass  # TODO: Add these as status=4 SubSubscriber (after implementing some way to delete those)

    return jsonify(status='ok')


@do.route('/do/admin/undo_votes/<uid>', methods=['POST'])
@login_required
def admin_undo_votes(uid):
    if not current_user.admin:
        abort(403)
    
    try:
        user = User.get(User.uid == uid)
    except User.DoesNotExist:
        return abort(404)

    form = DummyForm()
    if not form.validate():
        return redirect(url_for('view_user', user=user.name))
    

    post_v = SubPostVote.select().where(SubPostVote.uid == user.uid)
    comm_v = SubPostCommentVote.select().where(SubPostCommentVote.uid == user.uid)
    usr = {}

    for v in post_v:
        post = SubPost.select(SubPost.pid, SubPost.uid, SubPost.score).where(SubPost.pid == v.pid_id).get()
        if not usr.get(post.uid_id):
            usr[post.uid_id] = User.select(User.uid, User.score).where(User.uid == post.uid_id).get()
        tgus = usr[post.uid_id]
        post.score -= 1 if v.positive else -1
        tgus.score -= 1 if v.positive else -1
        user.given -= 1 if v.positive else -1
        post.save()
        tgus.save()
        v.delete_instance()
    for v in comm_v:
        comm = SubPostComment.select(SubPostComment.cid, SubPostComment.score, SubPostComment.uid).where(SubPostComment.cid == v.cid).get()
        if not usr.get(comm.uid_id):
            usr[comm.uid_id] = User.select(User.uid, User.score).where(User.uid == comm.uid_id).get()
        tgus = usr[comm.uid_id]
        if not comm.score:
            comm.score = 0
        else:
            comm.score -= 1 if v.positive else -1
        tgus.score -= 1 if v.positive else -1
        user.given -= 1 if v.positive else -1
        comm.save()
        tgus.save()
        v.delete_instance()
    user.save()
    return redirect(url_for('view_user', user=user.name))


@do.route('/do/cast_vote/<pid>/<oid>', methods=['POST'])
@login_required
def cast_vote(pid, oid):
    form = DummyForm()
    if form.validate():
        try:
            post = misc.getSinglePost(pid)
        except SubPost.DoesNotExist:
            return jsonify(status='error', error='Post does not exist')
        
        if post['ptype'] != 3:
            return jsonify(status='error', error='Post is not a poll')

        try:
            option = SubPostPollOption.get((SubPostPollOption.id == oid) & (SubPostPollOption.pid == pid))
        except SubPostPollOption.DoesNotExist:
            return jsonify(status='error', error='Poll option does not exist')

        # Check if user hasn't voted already.
        try:
            SubPostPollVote.get((SubPostPollVote.uid == current_user.uid) & (SubPostPollVote.pid == pid))
            return jsonify(status='error', error='Already voted')
        except SubPostPollVote.DoesNotExist:
            pass
        
        # Check if poll is still open...
        try:
            SubPostMetadata.get((SubPostMetadata.pid == pid) & (SubPostMetadata.key == 'poll_closed'))
            return jsonify(status='error', error='Poll is closed')
        except SubPostMetadata.DoesNotExist:
            pass

        try:
            ca = SubPostMetadata.get((SubPostMetadata.pid == pid) & (SubPostMetadata.key == 'poll_closes_time'))
            if int(ca.value) < time.time():
                return jsonify(status='error', error='Poll is closed')
        except SubPostMetadata.DoesNotExist:
            pass
        
        try:
            ca = SubPostMetadata.get((SubPostMetadata.pid == pid) & (SubPostMetadata.key == 'poll_vote_after_level'))
            if current_user.get_user_level()[0] < int(ca.value):
                return jsonify(status='error', error='Insufficient user level')
        except SubPostMetadata.DoesNotExist:
            pass

        # Everything OK. Issue vote.
        vote = SubPostPollVote.create(uid=current_user.uid, pid=pid, vid=oid)
    return jsonify(status='ok')


@do.route('/do/remove_vote/<pid>', methods=['POST'])
@login_required
def remove_vote(pid):
    form = DummyForm()
    if form.validate():
        try:
            post = misc.getSinglePost(pid)
        except SubPost.DoesNotExist:
            return jsonify(status='error', error='Post does not exist')
        
        if post['ptype'] != 3:
            return jsonify(status='error', error='Post is not a poll')

        # Check if poll is still open...
        try:
            SubPostMetadata.get((SubPostMetadata.pid == pid) & (SubPostMetadata.key == 'poll_closed'))
            return jsonify(status='error', error='Poll is closed')
        except SubPostMetadata.DoesNotExist:
            pass

        try:
            ca = SubPostMetadata.get((SubPostMetadata.pid == pid) & (SubPostMetadata.key == 'poll_closes_time'))
            if int(ca.value) < time.time():
                return jsonify(status='error', error='Poll is closed')
        except SubPostMetadata.DoesNotExist:
            pass
        
        # Check if user hasn't voted already.
        try:
            vote = SubPostPollVote.get((SubPostPollVote.uid == current_user.uid) & (SubPostPollVote.pid == pid))
            vote.delete_instance()
        except SubPostPollVote.DoesNotExist:
            pass
    return jsonify(status='ok')


@do.route('/do/close_poll', methods=['POST'])
@login_required
def close_poll():
    """ Closes a poll. """
    form = DeletePost()

    if form.validate():
        try:
            post = SubPost.get(SubPost.pid == form.post.data)
        except SubPost.DoesNotExist:
            return json.dumps({'status': 'error', 'error': 'Post does not exist'})

        if post.ptype != 3:
            abort(404)
        
        if current_user.uid == post.uid_id or current_user.is_admin() or current_user.is_mod(post.sid):
            # Check if poll's not closed already
            postmeta = misc.metadata_to_dict(SubPostMetadata.select().where(SubPostMetadata.pid == post.pid))
            if 'poll_closed' in postmeta:
                return json.dumps({'status': 'error', 'error': 'Poll already closed.'})

            if 'poll_closes_time' in postmeta:
                if int(postmeta['poll_closes_time']) < time.time():
                    return json.dumps({'status': 'error', 'error': 'Poll already closed.'})
            
            SubPostMetadata.create(pid=post.pid, key='poll_closed', value='1')
            return json.dumps({'status': 'ok'})
        else:
            abort(403)
    return json.dumps({'status': 'error', 'error': get_errors(form)})


@do.route('/do/report', methods=['POST'])
@login_required
def report():
    form = DeletePost()
    if form.validate():
        try:
            post = misc.getSinglePost(form.post.data)
        except SubPost.DoesNotExist:
            return jsonify(status='error', error='Post does not exist')
        
        if post['deleted'] != 0:
            return jsonify(status='error', error='Post does not exist')
        
        # check if user already reported the post
        try:
            rep = SubPostReport.get((SubPostReport.pid == post['pid']) & (SubPostReport.uid == current_user.uid))
            return jsonify(status='error', error='You have already reported this post')
        except SubPostReport.DoesNotExist:
            pass
        
        if len(form.reason.data) < 2:
            return jsonify(status='error', error='Report reason too short.')

        # do the reporting.
        SubPostReport.create(pid=post['pid'], uid=current_user.uid, reason=form.reason.data)
        # callbacks!
        cb = getattr(config, 'ON_POST_REPORT', False)
        if cb:
            cb(post, current_user, form.reason.data)
        return jsonify(status='ok')
    return json.dumps({'status': 'error', 'error': get_errors(form)})