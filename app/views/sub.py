import datetime
import time
from flask import Blueprint, redirect, url_for, abort, render_template, request
from flask_login import login_required, current_user
from werkzeug.contrib.atom import AtomFeed
from peewee import fn, JOIN
from ..misc import engine
from ..models import Sub, SubMetadata, SubStylesheet, SubUploads, SubPostComment, SubPost, SubPostPollOption
from ..models import SubPostPollVote, SubPostMetadata, SubFlair, SubLog, User
from ..forms import EditSubFlair, EditSubForm, EditSubCSSForm, EditSubTextPostForm, EditMod2Form
from ..forms import EditSubLinkPostForm, BanUserSubForm, EditPostFlair, CreateSubFlair
from .. import database as db
from .. import misc

sub = Blueprint('sub', __name__)


@sub.route("/<sub>/")
@sub.route("/<sub>")
def view_sub(sub):
    """ Here we can view subs """
    if sub.lower() == "all":
        return redirect(url_for('all_hot', page=1))

    try:
        sub = Sub.get(Sub.name == sub)
    except Sub.DoesNotExist:
        abort(404)

    try:
        x = SubMetadata.select().where(SubMetadata.sid == sub.sid)
        x = x.where(SubMetadata.key == 'sort').get()
        x = x.value
    except SubMetadata.DoesNotExist:
        x = 'v'
    if x == 'v':
        return redirect(url_for('sub.view_sub_hot', sub=sub.name))
    elif x == 'v_two':
        return redirect(url_for('sub.view_sub_new', sub=sub.name))
    elif x == 'v_three':
        return redirect(url_for('sub.view_sub_top', sub=sub.name))


@sub.route("/<sub>/edit/css")
@login_required
def edit_sub_css(sub):
    """ Here we can edit sub info and settings """
    try:
        sub = Sub.get(Sub.name == sub)
    except Sub.DoesNotExist:
        abort(404)

    if not current_user.is_mod(sub.sid) and not current_user.is_admin():
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
        sub = Sub.get(Sub.name == sub)
    except Sub.DoesNotExist:
        abort(404)

    if not current_user.is_mod(sub.sid) and not current_user.is_admin():
        abort(403)

    flairs = SubFlair.select().where(SubFlair.sid == sub.sid).dicts()
    formflairs = []
    for flair in flairs:
        formflairs.append(EditSubFlair(flair=flair['xid'], text=flair['text']))
    return render_template('editflairs.html', sub=sub, flairs=formflairs,
                           createflair=CreateSubFlair())


@sub.route("/<sub>/edit")
@login_required
def edit_sub(sub):
    """ Here we can edit sub info and settings """
    try:
        sub = Sub.get(Sub.name == sub)
    except Sub.DoesNotExist:
        abort(404)

    if current_user.is_mod(sub.sid) or current_user.is_admin():
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
        sub = Sub.get(Sub.name == sub)
    except Sub.DoesNotExist:
        abort(404)

    logs = SubLog.select().where(SubLog.sid == sub.sid).order_by(SubLog.lid.desc()).paginate(page, 50)
    return engine.get_template('sub/log.html').render({'sub': sub, 'logs': logs, 'page': page})


@sub.route("/<sub>/mods")
@login_required
def edit_sub_mods(sub):
    """ Here we can edit moderators for a sub """
    try:
        sub = Sub.get(Sub.name == sub)
    except Sub.DoesNotExist:
        abort(404)

    if current_user.is_mod(sub.sid) or current_user.is_modinv(sub.sid) or current_user.is_admin():
        subdata = misc.getSubData(sub.sid, extra=True)
        return render_template('submods.html', sub=sub, subdata=subdata,
                               editmod2form=EditMod2Form(),
                               banuserform=BanUserSubForm())
    else:
        abort(403)


@sub.route("/<sub>/new.rss")
def sub_new_rss(sub):
    """ RSS feed for /sub/new """
    try:
        sub = Sub.get(Sub.name == sub)
    except Sub.DoesNotExist:
        abort(404)

    feed = AtomFeed('New posts from ' + sub.name,
                    title_type='text',
                    generator=('Throat', 'https://phuks.co', 1),
                    feed_url=request.url,
                    url=request.url_root)
    posts = misc.getPostList(misc.postListQueryBase(noAllFilter=True).where(Sub.sid == sub.sid),
                             'new', 1).dicts()
    
    return misc.populate_feed(feed, posts).get_response()


@sub.route("/<sub>/new", defaults={'page': 1})
@sub.route("/<sub>/new/<int:page>")
def view_sub_new(sub, page):
    """ The index page, all posts sorted as most recent posted first """
    if sub.lower() == "all":
        return redirect(url_for('all_new', page=1))

    try:
        sub = Sub.select().where(Sub.name == sub).dicts().get()
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
                                                   'posts': posts, 'page': page, 'sort_type': 'sub.view_sub_new'})


@sub.route("/<sub>/bannedusers")
def view_sub_bans(sub):
    """ See banned users for the sub """
    try:
        sub = Sub.get(Sub.name == sub)
    except Sub.DoesNotExist:
        abort(404)

    banned = SubMetadata.select(SubMetadata.value, User.name).join(User, on=(SubMetadata.value == User.uid))
    banned = banned.where(SubMetadata.sid == sub.sid).where(SubMetadata.key == 'ban').dicts()

    xbans = SubMetadata.select(SubMetadata.value, User.name).join(User, on=(SubMetadata.value == User.uid))
    xbans = xbans.where(SubMetadata.sid == sub.sid).where(SubMetadata.key == 'xban').dicts()

    return render_template('subbans.html', sub=sub, banned=banned,
                           xbans=xbans, banuserform=BanUserSubForm())


@sub.route("/<sub>/top", defaults={'page': 1})
@sub.route("/<sub>/top/<int:page>")
def view_sub_top(sub, page):
    """ The index page, /top sorting """
    if sub.lower() == "all":
        return redirect(url_for('all_top', page=1))

    try:
        sub = Sub.select().where(Sub.name == sub).dicts().get()
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
                                                   'posts': posts, 'page': page, 'sort_type': 'sub.view_sub_top'})


@sub.route("/<sub>/hot", defaults={'page': 1})
@sub.route("/<sub>/hot/<int:page>")
def view_sub_hot(sub, page):
    """ The index page, /hot sorting """
    if sub.lower() == "all":
        return redirect(url_for('all_hot', page=1))
    try:
        sub = Sub.select().where(Sub.name == sub).dicts().get()
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
                                                   'posts': posts, 'page': page, 'sort_type': 'sub.view_sub_hot'})


@sub.route("/<sub>/<int:pid>")
def view_post(sub, pid, comments=False, highlight=None):
    """ View post and comments (WIP) """
    try:
        post = misc.getSinglePost(pid)
    except SubPost.DoesNotExist:
        abort(403)
    if post['sub'].lower() != sub.lower():
        abort(404)
    editflair = EditPostFlair()

    editflair.flair.choices = []
    if post['uid'] == current_user.uid or current_user.is_mod(post['sid']) or current_user.is_admin():
        flairs = SubFlair.select().where(SubFlair.sid == post['sid'])
        for flair in flairs:
            editflair.flair.choices.append((flair.xid, flair.text))

    txtpedit = EditSubTextPostForm()
    txtpedit.content.data = post['content']
    if not comments:
        comments = misc.get_post_comments(post['pid'])

    ksub = Sub.get(Sub.sid == post['sid'])
    ncomments = SubPostComment.select().where(SubPostComment.pid == post['pid']).count()

    postmeta = misc.metadata_to_dict(SubPostMetadata.select().where(SubPostMetadata.pid == pid))

    options, total_votes, has_voted, voted_for, poll_open, poll_closes = ([], 0, None, None, True, None)
    if post['ptype'] == 3:
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
                poll_closes = datetime.datetime.utcfromtimestamp(int(postmeta['poll_closes_time'])).isoformat()
                if int(postmeta['poll_closes_time']) < time.time():
                    poll_open = False

    return render_template('post.html', post=post, subInfo=misc.getSubData(post['sid']),
                           edittxtpostform=txtpedit, sub=ksub,
                           editlinkpostform=EditSubLinkPostForm(),
                           comments=comments, ncomments=ncomments,
                           editpostflair=editflair, highlight=highlight, 
                           poll_options=options, votes=total_votes, has_voted=has_voted, voted_for=voted_for,
                           poll_open=poll_open, postmeta=postmeta, poll_closes=poll_closes)


@sub.route("/<sub>/<pid>/<cid>")
def view_perm(sub, pid, cid):
    """ Permalink to comment """
    # We get the comment...
    try:
        the_comment = SubPostComment.select().where(SubPostComment.cid == cid).dicts()[0]
    except (SubPostComment.DoesNotExist, IndexError):
        abort(404)
    tc = cid if not the_comment['parentcid'] else the_comment['parentcid']
    tq = SubPostComment.select(SubPostComment.cid).where(SubPostComment.parentcid == cid).alias('jq')
    cmskel = SubPostComment.select(SubPostComment.cid, SubPostComment.parentcid)
    cmskel = cmskel.join(tq, on=((tq.c.cid == SubPostComment.parentcid) | (SubPostComment.parentcid == cid)))
    cmskel = cmskel.group_by(SubPostComment.cid)
    cmskel = cmskel.order_by(SubPostComment.score.desc()).dicts()

    cmskel = list(cmskel)
    cmskel.append({'cid': cid, 'parentcid': the_comment['parentcid']})
    if the_comment['parentcid']:
        cmskel.append({'cid': the_comment['parentcid'], 'parentcid': ''})
    if len(cmskel) > 1:
        cmxk = misc.build_comment_tree(cmskel, tc)
    else:
        cmxk = ([{'cid': cid, 'children': []}], [cid])
    if the_comment['parentcid']:
        cmxk[1].append(the_comment['parentcid'])
        cmxk = ([{'cid': the_comment['parentcid'], 'children': cmxk[0]}], cmxk[1])
    elif len(cmskel) > 1:
        cmxk[1].append(the_comment['cid'])
        cmxk = ([{'cid': the_comment['cid'], 'children': cmxk[0]}], cmxk[1])
    return view_post(sub, pid, misc.expand_comment_tree(cmxk), cid)
