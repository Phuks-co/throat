""" Generic sub actions (creating subs, creating posts, etc) """
import uuid
from datetime import datetime, timedelta, timezone
from peewee import fn
from flask import Blueprint, abort, request, render_template, redirect, url_for
from flask_login import login_required, current_user
from flask_babel import _, lazy_gettext as _l
from .. import misc
from ..config import config
from ..misc import engine
from ..socketio import socketio
from ..models import Sub, db as pdb, SubMod, SubMetadata, SubStylesheet, SubSubscriber, SiteMetadata, SubPost
from ..models import SubPostPollOption, SubPostMetadata, SubPostVote, User, UserUploads
from ..forms import CreateSubPostForm, CreateSubForm
from ..storage import file_url, upload_file

bp = Blueprint('subs', __name__)


def post_over_limit():
    captcha = None
    if misc.get_user_level(current_user.uid)[0] <= 4:
        captcha = misc.create_captcha()
    form = CreateSubPostForm()
    return engine.get_template('sub/createpost.html').render({'error': _('Wait a bit before posting.'), 'form': form, 'sub': None, 'captcha': captcha})


@bp.route("/submit/<ptype>", defaults={'sub': ''}, methods=['GET'])
@bp.route("/submit/<ptype>/<sub>", methods=['GET'])
@login_required
def submit(ptype, sub):
    if ptype not in ['link', 'text', 'poll', 'upload']:
        abort(404)

    captcha = None
    if misc.get_user_level(current_user.uid)[0] <= 4:
        captcha = misc.create_captcha()

    form = CreateSubPostForm()
    if current_user.canupload:
        form.ptype.choices.append(('upload', _l('Upload file')))

    form.ptype.data = ptype

    if sub != '':
        form.sub.data = sub
        try:
            sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
            subdata = misc.getSubData(sub.sid)
            if subdata.get('allow_polls', False):
                form.ptype.choices.append(('poll', _l('Poll')))
        except Sub.DoesNotExist:
            abort(404)

    if request.args.get('title'):
        form.title.data = request.args.get('title')

    if request.args.get('url'):
        form.link.data = request.args.get('url')

    return engine.get_template('sub/createpost.html').render(
        {'error': misc.get_errors(form, True), 'form': form, 'sub': sub, 'captcha': captcha})


@bp.route("/submit/<ptype>", defaults={'sub': ''}, methods=['POST'])
@bp.route("/submit/<ptype>/<sub>", methods=['POST'])
@login_required
@misc.ratelimit(1, per=30, over_limit=post_over_limit)
def create_post(ptype, sub):
    if ptype not in ['link', 'text', 'poll', 'upload']:
        abort(404)

    captcha = None
    if misc.get_user_level(current_user.uid)[0] <= 4:
        captcha = misc.create_captcha()

    form = CreateSubPostForm()
    if current_user.canupload:
        form.ptype.choices.append(('upload', _l('Upload file')))

    if not form.sub.data and sub != '':
        form.sub.data = sub

    if form.sub.data:
        try:
            sub = Sub.get(fn.Lower(Sub.name) == form.sub.data.lower())
            subdata = misc.getSubData(sub.sid)
            if subdata.get('allow_polls', False):
                form.ptype.choices.append(('poll', _l('Poll')))
        except Sub.DoesNotExist:
            pass

    if not form.validate():
        if not form.ptype.data:
            form.ptype.data = ptype

        return engine.get_template('sub/createpost.html').render({'error': misc.get_errors(form, True), 'form': form, 'sub': sub, 'captcha': captcha}), 400

    if misc.get_user_level(current_user.uid)[0] <= 4:
        if not misc.validate_captcha(form.ctok.data, form.captcha.data):
            return engine.get_template('sub/createpost.html').render(
                {'error': _("Invalid captcha."), 'form': form, 'sub': sub, 'captcha': captcha}), 400

    # Put pre-posting checks here
    if not current_user.is_admin():
        try:
            enable_posting = SiteMetadata.get(SiteMetadata.key == 'enable_posting')
            if enable_posting.value in ('False', '0'):
                return engine.get_template('sub/createpost.html').render(
                    {'error': _("Posting has been temporarily disabled."), 'form': form, 'sub': sub,
                     'captcha': captcha}), 400
        except SiteMetadata.DoesNotExist:
            pass

    try:
        sub = Sub.get(fn.Lower(Sub.name) == form.sub.data.lower())
    except Sub.DoesNotExist:
        return engine.get_template('sub/createpost.html').render(
            {'error': _("Sub does not exist."), 'form': form, 'sub': sub, 'captcha': captcha}), 400

    subdata = misc.getSubData(sub.sid)

    if sub.name.lower() in ('all', 'new', 'hot', 'top', 'admin', 'home'):
        return engine.get_template('sub/createpost.html').render(
            {'error': _("You cannot post in this sub."), 'form': form, 'sub': sub, 'captcha': captcha}), 400

    if current_user.is_subban(sub):
        return engine.get_template('sub/createpost.html').render(
            {'error': _("You're banned from posting on this sub."), 'form': form, 'sub': sub, 'captcha': captcha}), 400

    submods = misc.getSubMods(sub.sid)
    if subdata.get('restricted', 0) == '1' and not (current_user.uid in submods['all']):
        return engine.get_template('sub/createpost.html').render(
            {'error': _("Only mods can post on this sub."), 'form': form, 'sub': sub, 'captcha': captcha}), 400

    if misc.get_user_level(current_user.uid)[0] < 7:
        today = datetime.utcnow() - timedelta(days=1)
        lposts = SubPost.select().where(SubPost.uid == current_user.uid).where(SubPost.sid == sub.sid).where(
            SubPost.posted > today).count()
        tposts = SubPost.select().where(SubPost.uid == current_user.uid).where(SubPost.posted > today).count()
        if lposts > config.site.daily_sub_posting_limit or tposts > config.site.daily_site_posting_limit:
            return engine.get_template('sub/createpost.html').render(
                {'error': _("You have posted too much today."), 'form': form, 'sub': sub, 'captcha': captcha}), 400

    if len(form.title.data.strip(misc.WHITESPACE)) < 3:
        return engine.get_template('sub/createpost.html').render(
            {'error': _("Title is too short and/or contains whitespace characters."), 'form': form, 'sub': sub,
             'captcha': captcha}), 400

    fileid = False
    img = ''
    if form.ptype.data in ('link', 'upload'):
        # TODO: Make a different ptype for uploads?
        ptype = 1
        fupload = upload_file()
        if fupload[0] is not False and fupload[1] is False:
            return engine.get_template('sub/createpost.html').render(
                {'error': fupload[0], 'form': form, 'sub': sub, 'captcha': captcha}), 400

        if fupload[1]:
            form.link.data = file_url(fupload[0])
            fileid = fupload[0]

        if not form.link.data:
            return engine.get_template('sub/createpost.html').render(
                {'error': _("No link provided."), 'form': form, 'sub': sub, 'captcha': captcha}), 400

        try:
            lx = SubPost.select(SubPost.pid).where(SubPost.sid == sub.sid)
            lx = lx.where(SubPost.link == form.link.data).where(SubPost.deleted == 0)
            monthago = datetime.utcnow() - timedelta(days=30)
            lx.where(SubPost.posted > monthago).get()
            return engine.get_template('sub/createpost.html').render(
                {'error': _("This link was recently posted on this sub."), 'form': form, 'sub': sub, 'captcha': captcha}), 400
        except SubPost.DoesNotExist:
            pass

        if misc.is_domain_banned(form.link.data.lower()):
            return engine.get_template('sub/createpost.html').render(
                {'error': _("This domain is banned."), 'form': form, 'sub': sub, 'captcha': captcha}), 400
        img = misc.get_thumbnail(form.link.data)
    elif form.ptype.data == 'poll':
        ptype = 3
        # Check if this sub allows polls...
        if not subdata.get('allow_polls', False):
            return engine.get_template('sub/createpost.html').render(
                {'error': _("This sub does not allow polling."), 'form': form, 'sub': sub, 'captcha': captcha}), 400
        # check if we got at least three options
        options = form.options.data
        options = [x for x in options if len(x.strip(misc.WHITESPACE)) > 0]  # Remove empty strings
        if len(options) < 2:
            return engine.get_template('sub/createpost.html').render(
                {'error': _("Not enough poll options provided."), 'form': form, 'sub': sub, 'captcha': captcha}), 400

        for p in options:
            if len(p) > 128:
                return engine.get_template('sub/createpost.html').render(
                    {'error': _("Poll option text is too long."), 'form': form, 'sub': sub, 'captcha': captcha}), 400

        if form.closetime.data:
            try:
                closetime = datetime.strptime(form.closetime.data, "%Y-%m-%dT%H:%M:%S.%fZ")
                if (closetime - datetime.utcnow()) > timedelta(days=60):
                    return engine.get_template('sub/createpost.html').render(
                        {'error': _("Poll closing time is too far in the future."), 'form': form, 'sub': sub,
                         'captcha': captcha}), 400
            except ValueError:
                return engine.get_template('sub/createpost.html').render(
                    {'error': _("Invalid closing time."), 'form': form, 'sub': sub, 'captcha': captcha}), 400

            if datetime.utcnow() > closetime:
                return engine.get_template('sub/createpost.html').render(
                    {'error': _("The closing time is in the past!"), 'form': form, 'sub': sub, 'captcha': captcha}), 400
    elif form.ptype.data == 'text':
        ptype = 0
    else:
        return engine.get_template('sub/createpost.html').render(
            {'error': _("Invalid post type"), 'form': form, 'sub': sub, 'captcha': captcha}), 400

    post = SubPost.create(sid=sub.sid,
                          uid=current_user.uid,
                          title=form.title.data,
                          content=form.content.data if ptype != 1 else '',
                          link=form.link.data if ptype == 1 else None,
                          posted=datetime.utcnow(),
                          score=1, upvotes=1, downvotes=0,
                          deleted=0,
                          comments=0,
                          ptype=ptype,
                          nsfw=form.nsfw.data if not sub.nsfw else 1,
                          thumbnail=img)

    if ptype == 3:
        # Create SubPostPollOption objects...
        poll_options = [{'pid': post.pid, 'text': x} for x in options]
        SubPostPollOption.insert_many(poll_options).execute()
        # apply all poll options..
        if form.hideresults.data:
            SubPostMetadata.create(pid=post.pid, key='hide_results', value=1)

        if form.closetime.data:
            SubPostMetadata.create(pid=post.pid, key='poll_closes_time',
                                   value=int(closetime.replace(tzinfo=timezone.utc).timestamp()))

    Sub.update(posts=Sub.posts + 1).where(Sub.sid == sub.sid).execute()
    addr = url_for('sub.view_post', sub=sub.name, pid=post.pid)
    posts = misc.getPostList(misc.postListQueryBase(nofilter=True).where(SubPost.pid == post.pid), 'new', 1).dicts()
    socketio.emit('thread',
                  {'addr': addr, 'sub': sub.name, 'type': form.ptype.data,
                   'user': current_user.name, 'pid': post.pid, 'sid': sub.sid,
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
        UserUploads.create(pid=post.pid, uid=current_user.uid, fileid=fileid, thumbnail=img if img else '',
                           status=0)

    misc.workWithMentions(form.content.data, None, post, sub)
    misc.workWithMentions(form.title.data, None, post, sub)
    return redirect(addr)


@bp.route("/random")
def random_sub():
    """ Here we get a random sub """
    rsub = Sub.select(Sub.name).order_by(pdb.random()).limit(1)
    return redirect(url_for('sub.view_sub', sub=rsub.get().name))


@bp.route("/createsub", methods=['GET', 'POST'])
@login_required
def create_sub():
    """ Here we can view the create sub form """
    form = CreateSubForm()
    # return engine.get_template('sub/create.html').render({'csubform': createsub})
    if not form.validate():
        return engine.get_template('sub/create.html').render({'error': misc.get_errors(form, True), 'csubform': form})

    if not misc.allowedNames.match(form.subname.data):
        return engine.get_template('sub/create.html').render(
            {'error': _('Sub name has invalid characters'), 'csubform': form})

    if form.subname.data.lower() in ('all', 'new', 'hot', 'top', 'admin', 'home'):
        return engine.get_template('sub/create.html').render({'error': _('Invalid sub name'), 'csubform': form})

    try:
        Sub.get(fn.Lower(Sub.name) == form.subname.data.lower())
        return engine.get_template('sub/create.html').render(
            {'error': _('Sub is already registered'), 'csubform': form})
    except Sub.DoesNotExist:
        pass

    if config.site.sub_creation_admin_only and not current_user.admin:
        return engine.get_template('sub/create.html').render(
            {'error': _("Only Site Admins may create new subs. Please contact an administrator to request a new sub.", level=config.site.sub_creation_min_level),
             'csubform': form})

    level = misc.get_user_level(current_user.uid)[0]
    if not config.app.development and config.site.sub_creation_min_level != 0:
        if (level <= 1) and (not current_user.admin):
            return engine.get_template('sub/create.html').render(
                {'error': _("You must be at least level %(level)i.", level=config.site.sub_creation_min_level),
                 'csubform': form})

        owned = SubMod.select().where(SubMod.uid == current_user.uid).where(
            (SubMod.power_level == 0) & (SubMod.invite == False)).count()

        if owned >= 20 and (not current_user.admin):
            return engine.get_template('sub/create.html').render(
                {'error': _('You cannot own more than %(max)i subs.', max=config.site.sub_ownership_limit),
                 'csubform': form})

        if owned >= (level - 1) and (not current_user.admin):
            return engine.get_template('sub/create.html').render(
                {'error': _('You cannot own more than %(max)i subs. Try leveling up your account.',
                            max=config.site.sub_ownership_limit),
                 'csubform': form})

    sub = Sub.create(sid=uuid.uuid4(), name=form.subname.data, title=form.title.data)
    SubMetadata.create(sid=sub.sid, key='mod', value=current_user.uid)
    SubMod.create(sid=sub.sid, uid=current_user.uid, power_level=0)
    SubStylesheet.create(sid=sub.sid, content='', source='/* CSS here */')

    # admin/site log
    misc.create_sublog(misc.LOG_TYPE_SUB_CREATE, uid=current_user.uid, sid=sub.sid, admin=True)

    SubSubscriber.create(uid=current_user.uid, sid=sub.sid, status=1)

    return redirect(url_for('sub.view_sub', sub=form.subname.data))
