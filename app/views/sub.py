""" All endpoints related to stuff done inside of a particular sub """
import datetime
import time
from flask import Blueprint, redirect, url_for, abort, render_template, request, Response
from flask_login import login_required, current_user
from feedgen.feed import FeedGenerator
from peewee import fn, JOIN
from ..misc import engine
from ..models import Sub, SubMetadata, SubStylesheet, SubUploads, SubPostComment, SubPost, SubPostPollOption
from ..models import SubPostPollVote, SubPostMetadata, SubFlair, SubLog, User, UserSaved, SubMod, SubBan, SubRule
from ..forms import EditSubFlair, EditSubForm, EditSubCSSForm, EditSubTextPostForm, EditMod2Form, EditSubRule
from ..forms import EditSubLinkPostForm, BanUserSubForm, EditPostFlair, CreateSubFlair, PostComment, CreateSubRule
from .. import misc
import json
from playhouse.shortcuts import model_to_dict


sub = Blueprint('sub', __name__)


@sub.route("/<sub>/")
@sub.route("/<sub>")
def view_sub(sub):
    """ Here we can view subs """
    if sub.lower() == "all":
        return redirect(url_for('home.all_hot', page=1))

    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        abort(404)

    try:
        x = SubMetadata.select().where(SubMetadata.sid == sub.sid)
        x = x.where(SubMetadata.key == 'sort').get()
        x = x.value
    except SubMetadata.DoesNotExist:
        x = 'v'
    if x == 'v_two':
        return redirect(url_for('sub.view_sub_new', sub=sub.name))
    elif x == 'v_three':
        return redirect(url_for('sub.view_sub_top', sub=sub.name))
    else:
        return redirect(url_for('sub.view_sub_hot', sub=sub.name))


@sub.route("/<sub>/edit/css")
@login_required
def edit_sub_css(sub):
    """ Here we can edit sub info and settings """
    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        abort(404)

    if not current_user.is_mod(sub.sid, 1) and not current_user.is_admin():
        abort(403)

    c = SubStylesheet.get(SubStylesheet.sid == sub.sid)

    form = EditSubCSSForm(css=c.source)
    stor = 0
    ufiles = SubUploads.select().where(SubUploads.sid == sub.sid)
    for uf in ufiles:
        stor += uf.size / 1024

    return engine.get_template('sub/css.html').render({'sub': sub, 'form': form, 'error': False, 'storage': int(stor), 'files': ufiles})


@sub.route("/<sub>/edit/flairs")
@login_required
def edit_sub_flairs(sub):
    """ Here we manage the sub's flairs. """
    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        abort(404)

    if not current_user.is_mod(sub.sid, 1) and not current_user.is_admin():
        abort(403)

    flairs = SubFlair.select().where(SubFlair.sid == sub.sid).dicts()
    formflairs = []
    for flair in flairs:
        formflairs.append(EditSubFlair(flair=flair['xid'], text=flair['text']))
    return render_template('editflairs.html', sub=sub, flairs=formflairs,
                           createflair=CreateSubFlair())


@sub.route("/<sub>/edit/rules")
@login_required
def edit_sub_rules(sub):
    """ Here we manage the sub's rules. """
    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        abort(404)

    if not current_user.is_mod(sub.sid, 1) and not current_user.is_admin():
        abort(403)

    rules = SubRule.select().where(SubRule.sid == sub.sid).dicts()
    formrules = []
    for rule in rules:
        formrules.append(EditSubRule(rule=rule['rid'], text=rule['text']))
    return render_template('editrules.html', sub=sub, rules=formrules,
                           createrule=CreateSubRule())


@sub.route("/<sub>/edit")
@login_required
def edit_sub(sub):
    """ Here we can edit sub info and settings """
    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        abort(404)

    if current_user.is_mod(sub.sid, 1) or current_user.is_admin():
        submeta = misc.metadata_to_dict(SubMetadata.select().where(SubMetadata.sid == sub.sid))
        form = EditSubForm()
        # pre-populate the form.
        form.subsort.data = submeta.get('sort')
        form.sidebar.data = sub.sidebar
        form.title.data = sub.title

        return render_template('editsub.html', sub=sub, editsubform=form, metadata=submeta)
    else:
        abort(403)


@sub.route("/<sub>/sublog", defaults={'page': 1})
@sub.route("/<sub>/sublog/<int:page>")
def view_sublog(sub, page):
    """ Here we can see a log of mod/admin activity in the sub """
    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        abort(404)

    subInfo = misc.getSubData(sub.sid)
    log_is_private = subInfo.get('sublog_private', 0) == '1'

    if log_is_private and not (current_user.is_mod(sub.sid, 1) or current_user.is_admin()):
        abort(404)

    logs = SubLog.select().where(SubLog.sid == sub.sid).order_by(SubLog.lid.desc()).paginate(page, 50)
    return engine.get_template('sub/log.html').render({'sub': sub, 'logs': logs, 'page': page})


@sub.route("/<sub>/mods")
@login_required
def edit_sub_mods(sub):
    """ Here we can edit moderators for a sub """
    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        abort(404)

    if current_user.is_mod(sub.sid, 2) or current_user.is_modinv(sub.sid) or current_user.is_admin():
        subdata = misc.getSubData(sub.sid, extra=True)
        subMods = misc.getSubMods(sub.sid)
        modInvites = SubMod.select(User.name, SubMod.power_level).join(User).where((SubMod.sid == sub.sid) & (SubMod.invite == True))
        return render_template('submods.html', sub=sub, subdata=subdata,
                               editmod2form=EditMod2Form(), subMods=subMods, subModInvites=modInvites,
                               banuserform=BanUserSubForm())
    else:
        abort(403)


@sub.route("/<sub>/new.rss")
def sub_new_rss(sub):
    """ RSS feed for /sub/new """
    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        abort(404)

    fg = FeedGenerator()
    fg.id(request.url)
    fg.title('New posts from ' + sub.name)
    fg.link(href=request.url_root, rel='alternate')
    fg.link(href=request.url, rel='self')

    posts = misc.getPostList(misc.postListQueryBase(noAllFilter=True).where(Sub.sid == sub.sid),
                            'new', 1).dicts()

    return Response(misc.populate_feed(fg, posts).atom_str(pretty=True), mimetype='application/atom+xml')


@sub.route("/<sub>/new", defaults={'page': 1})
@sub.route("/<sub>/new/<int:page>")
def view_sub_new(sub, page):
    """ The index page, all posts sorted as most recent posted first """
    if sub.lower() == "all":
        return redirect(url_for('home.all_new', page=1))

    try:
        sub = Sub.select().where(fn.Lower(Sub.name) == sub.lower()).dicts().get()
    except Sub.DoesNotExist:
        abort(404)

    posts = misc.getPostList(misc.postListQueryBase(noAllFilter=True).where(Sub.sid == sub['sid']),
                             'new', page).dicts()

    try:
        vm = SubMetadata.select().where(SubMetadata.sid == sub['sid']).where(SubMetadata.key == 'videomode').get().value
    except SubMetadata.DoesNotExist:
        vm = 0
    playlist = []
    if vm == '1':
        for post in posts:
            if post['link']:
                yid = misc.getYoutubeID(post['link'])
                if yid is not None:
                    playlist.append(yid)

    return engine.get_template('sub.html').render({'sub': sub, 'subInfo': misc.getSubData(sub['sid']), 'playlist': playlist,
                                                   'posts': posts, 'page': page, 'sort_type': 'sub.view_sub_new',
                                                   'subMods': misc.getSubMods(sub['sid'])})


@sub.route("/<sub>/bannedusers")
def view_sub_bans(sub):
    """ See banned users for the sub """
    try:
        sub = Sub.get(fn.Lower(Sub.name) == sub.lower())
    except Sub.DoesNotExist:
        abort(404)

    user = User.alias()
    created_by = User.alias()
    banned = SubBan.select(user, created_by, SubBan.created, SubBan.reason, SubBan.expires)
    banned = banned.join(user, on=SubBan.uid).switch(SubBan).join(created_by, JOIN.LEFT_OUTER, on=SubBan.created_by_id)
    banned = banned.where((SubBan.sid == sub.sid) & ((SubBan.effective == True) & ((SubBan.expires.is_null(True)) | (SubBan.expires > datetime.datetime.utcnow()) )))
    banned = banned.order_by(SubBan.created.is_null(True), SubBan.created.desc())

    xbans = SubBan.select(user, created_by, SubBan.created, SubBan.reason, SubBan.expires)
    xbans = xbans.join(user, on=SubBan.uid).switch(SubBan).join(created_by, JOIN.LEFT_OUTER, on=SubBan.created_by_id)

    xbans = xbans.where(SubBan.sid == sub.sid)
    xbans = xbans.where((SubBan.effective == False) | ((SubBan.expires.is_null(False)) & (SubBan.expires < datetime.datetime.utcnow()) ))
    xbans = xbans.order_by(SubBan.created.is_null(True), SubBan.created.desc(), SubBan.expires.asc())

    return engine.get_template('sub/bans.html').render({'sub': sub, 'banned': banned, 'xbans': xbans,
                                                        'banuserform': BanUserSubForm(), 'submods': misc.getSubMods(sub.sid)})


@sub.route("/<sub>/top", defaults={'page': 1})
@sub.route("/<sub>/top/<int:page>")
def view_sub_top(sub, page):
    """ The index page, /top sorting """
    if sub.lower() == "all":
        return redirect(url_for('home.all_top', page=1))

    try:
        sub = Sub.select().where(fn.Lower(Sub.name) == sub.lower()).dicts().get()
    except Sub.DoesNotExist:
        abort(404)

    posts = misc.getPostList(misc.postListQueryBase(noAllFilter=True).where(Sub.sid == sub['sid']),
                             'top', page).dicts()

    try:
        vm = SubMetadata.select().where(SubMetadata.sid == sub['sid']).where(SubMetadata.key == 'videomode').get().value
    except SubMetadata.DoesNotExist:
        vm = 0
    playlist = []
    if vm == '1':
        for post in posts:
            if post['link']:
                yid = misc.getYoutubeID(post['link'])
                if yid is not None:
                    playlist.append(yid)

    return engine.get_template('sub.html').render({'sub': sub, 'subInfo': misc.getSubData(sub['sid']), 'playlist': playlist,
                                                   'posts': posts, 'page': page, 'sort_type': 'sub.view_sub_top',
                                                   'subMods': misc.getSubMods(sub['sid'])})


@sub.route("/<sub>/hot", defaults={'page': 1})
@sub.route("/<sub>/hot/<int:page>")
def view_sub_hot(sub, page):
    """ The index page, /hot sorting """
    if sub.lower() == "all":
        return redirect(url_for('home.all_hot', page=1))
    try:
        sub = Sub.select().where(fn.Lower(Sub.name) == sub.lower()).dicts().get()
    except Sub.DoesNotExist:
        abort(404)

    posts = misc.getPostList(misc.postListQueryBase(noAllFilter=True).where(Sub.sid == sub['sid']),
                             'hot', page).dicts()
    try:
        vm = SubMetadata.select().where(SubMetadata.sid == sub['sid']).where(SubMetadata.key == 'videomode').get().value
    except SubMetadata.DoesNotExist:
        vm = 0
    playlist = []
    if vm == '1':
        for post in posts:
            if post['link']:
                yid = misc.getYoutubeID(post['link'])
                if yid is not None:
                    playlist.append(yid)

    return engine.get_template('sub.html').render({'sub': sub, 'subInfo': misc.getSubData(sub['sid']), 'playlist': playlist,
                                                   'posts': posts, 'page': page, 'sort_type': 'sub.view_sub_hot',
                                                   'subMods': misc.getSubMods(sub['sid'])})


@sub.route("/<sub>/<int:pid>")
def view_post(sub, pid, comments=False, highlight=None):
    """ View post and comments (WIP) """
    try:
        post = misc.getSinglePost(pid)
    except SubPost.DoesNotExist:
        abort(403)
    if post['sub'].lower() != sub.lower():
        abort(404)

    sub = Sub.select().where(fn.Lower(Sub.name) == sub.lower()).dicts().get()
    subInfo = misc.getSubData(sub['sid'])

    try:
        UserSaved.get((UserSaved.uid == current_user.uid) & (UserSaved.pid == pid))
        is_saved = True
    except UserSaved.DoesNotExist:
        is_saved = False

    if not comments:
        comments = SubPostComment.select(SubPostComment.cid, SubPostComment.parentcid).where(SubPostComment.pid == post['pid']).order_by(SubPostComment.score.desc()).dicts()
        if not comments.count():
            comments = []
        else:
            comments = misc.get_comment_tree(comments, uid=current_user.uid)

    pollData = {'has_voted': False}
    postmeta = {}
    if post['ptype'] == 3:
        postmeta = misc.metadata_to_dict(SubPostMetadata.select().where(SubPostMetadata.pid == pid))
        # poll. grab options and votes.
        options = SubPostPollOption.select(SubPostPollOption.id, SubPostPollOption.text, fn.Count(SubPostPollVote.id).alias('votecount'))
        options = options.join(SubPostPollVote, JOIN.LEFT_OUTER, on=(SubPostPollVote.vid == SubPostPollOption.id))
        options = options.where(SubPostPollOption.pid == pid).group_by(SubPostPollOption.id)
        pollData['options'] = options
        total_votes = SubPostPollVote.select().where(SubPostPollVote.pid == pid).count()
        pollData['total_votes'] = total_votes
        if current_user.is_authenticated:
            # Check if user has already voted on this poll.
            try:
                u_vote = SubPostPollVote.get((SubPostPollVote.pid == pid) & (SubPostPollVote.uid == current_user.uid))
                pollData['has_voted'] = True
                pollData['voted_for'] = u_vote.vid_id
            except SubPostPollVote.DoesNotExist:
                pollData['has_voted'] = False

        # Check if the poll is open
        pollData['poll_open'] = True
        if 'poll_closed' in postmeta:
            pollData['poll_open'] = False

        if 'poll_closes_time' in postmeta:
            pollData['poll_closes'] = datetime.datetime.utcfromtimestamp(int(postmeta['poll_closes_time'])).isoformat()
            if int(postmeta['poll_closes_time']) < time.time():
                pollData['poll_open'] = False

    return engine.get_template('sub/post.html').render({'post': post, 'sub': sub, 'subInfo': subInfo,
                                                        'is_saved': is_saved, 'pollData': pollData, 'postmeta': postmeta,
                                                        'commentform': PostComment(), 'comments': comments,
                                                        'subMods': misc.getSubMods(sub['sid']), 'highlight': highlight})


@sub.route("/<sub>/<pid>/<cid>")
def view_perm(sub, pid, cid):
    """ Permalink to comment """
    # We get the comment...
    try:
        the_comment = SubPostComment.select().where(SubPostComment.cid == cid).dicts()[0]
    except (SubPostComment.DoesNotExist, IndexError):
        abort(404)

    comments = SubPostComment.select(SubPostComment.cid, SubPostComment.parentcid).where(SubPostComment.pid == pid).order_by(SubPostComment.score.desc()).dicts()
    if not comments.count():
        comments = []
    else:
        comment_tree = misc.get_comment_tree(comments, cid, uid=current_user.uid)
    return view_post(sub, pid, comment_tree, cid)
