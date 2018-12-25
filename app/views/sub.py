from flask import Blueprint, redirect, url_for, abort, render_template, request
from flask_login import login_required, current_user
from werkzeug.contrib.atom import AtomFeed
from ..misc import engine
from ..models import Sub, SubMetadata, SubStylesheet, SubUploads, SubPostComment, SubPost
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
    if sub.lower() == "live":
        return redirect(url_for('view_live_sub', page=1))
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
    sub = db.get_sub_from_name(sub)
    if not sub:
        abort(404)

    if not current_user.is_mod(sub['sid']) and not current_user.is_admin():
        abort(403)

    c = db.query('SELECT * FROM `sub_flair` WHERE `sid`=%s', (sub['sid'], ))
    flairs = c.fetchall()
    formflairs = []
    for flair in flairs:
        formflairs.append(EditSubFlair(flair=flair['xid'], text=flair['text']))
    return render_template('editflairs.html', sub=sub, flairs=formflairs,
                           createflair=CreateSubFlair())


@sub.route("/<sub>/edit")
@login_required
def edit_sub(sub):
    """ Here we can edit sub info and settings """
    sub = db.get_sub_from_name(sub)
    if not sub:
        abort(404)

    if current_user.is_mod(sub['sid']) or current_user.is_admin():
        form = EditSubForm()
        pp = db.get_sub_metadata(sub['sid'], 'sort')
        form.subsort.data = pp.get('value') if pp else ''
        form.sidebar.data = sub['sidebar']
        return render_template('editsub.html', sub=sub, editsubform=form)
    else:
        abort(403)


@sub.route("/<sub>/sublog", defaults={'page': 1})
@sub.route("/<sub>/sublog/<int:page>")
def view_sublog(sub, page):
    """ Here we can see a log of mod/admin activity in the sub """
    sub = db.get_sub_from_name(sub)
    if not sub:
        abort(404)

    logs = db.query('SELECT * FROM `sub_log` WHERE `sid`=%s ORDER BY `lid` '
                    'DESC LIMIT 50 OFFSET %s ',
                    (sub['sid'], ((page - 1) * 50)))
    logs = logs.fetchall()
    return render_template('sublog.html', sub=sub, logs=logs, page=page)


@sub.route("/<sub>/mods")
@login_required
def edit_sub_mods(sub):
    """ Here we can edit moderators for a sub """
    try:
        sub = Sub.get(Sub.name == sub)
    except Sub.DoesNotExist:
        abort(404)

    if current_user.is_mod(sub.sid) or current_user.is_modinv(sub.sid) or current_user.is_admin():
        subdata = misc.getSubData(sub.sid)
        xmods = db.get_sub_metadata(sub.sid, 'xmod2', _all=True)
        modinvs = db.get_sub_metadata(sub.sid, 'mod2i', _all=True)
        return render_template('submods.html', sub=sub,
                               modinvs=modinvs, xmods=xmods, subdata=subdata,
                               editmod2form=EditMod2Form(),
                               banuserform=BanUserSubForm())
    else:
        abort(403)


@sub.route("/<sub>/new.rss")
def sub_new_rss(sub):
    """ RSS feed for /sub/new """
    sub = db.get_sub_from_name(sub)
    if not sub:
        abort(404)

    feed = AtomFeed('New posts from ' + sub['name'],
                    title_type='text',
                    generator=('Throat', 'https://phuks.co', 1),
                    feed_url=request.url,
                    url=request.url_root)
    posts = misc.getPostList(misc.postListQueryBase(noAllFilter=True).where(Sub.sid == sub['sid']),
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
    sub = db.get_sub_from_name(sub)
    if not sub:
        abort(404)

    banned = db.get_sub_metadata(sub['sid'], 'ban', _all=True)
    xbans = db.get_sub_metadata(sub['sid'], 'xban', _all=True)
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
    if post['uid'] == current_user.get_id() or current_user.is_mod(post['sid']) \
       or current_user.is_admin():
        flairs = db.query('SELECT `xid`, `text` FROM `sub_flair` '
                          'WHERE `sid`=%s', (post['sid'], )).fetchall()
        for flair in flairs:
            editflair.flair.choices.append((flair['xid'], flair['text']))

    mods = db.get_sub_metadata(post['sid'], 'mod2', _all=True)
    txtpedit = EditSubTextPostForm()
    txtpedit.content.data = post['content']
    if not comments:
        comments = misc.get_post_comments(post['pid'])

    ksub = db.get_sub_from_sid(post['sid'])
    ncomments = SubPostComment.select().where(SubPostComment.pid == post['pid']).count()
    return render_template('post.html', post=post, mods=mods,
                           edittxtpostform=txtpedit, sub=ksub,
                           editlinkpostform=EditSubLinkPostForm(),
                           comments=comments, ncomments=ncomments,
                           editpostflair=editflair, highlight=highlight)


@sub.route("/<sub>/<pid>/<cid>")
def view_perm(sub, pid, cid):
    """ Permalink to comment """
    # We get the comment...
    the_comment = db.get_comment_from_cid(cid)
    if not the_comment:
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
