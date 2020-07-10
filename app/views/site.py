""" Miscellaneous site endpoints """
from peewee import SQL
from flask import Blueprint, redirect, url_for, abort, render_template
from flask_login import login_required, current_user
from .. import misc
from ..models import SiteLog, SubPost, SubLog, Sub, SubPostComment
from ..misc import engine
from ..config import config

bp = Blueprint('site', __name__)


@bp.route('/chat')
@login_required
def chat():
    return engine.get_template('chat.html').render(
        {'subOfTheDay': misc.getSubOfTheDay(), 'changeLog': misc.getChangelog()})


@bp.route("/sitelog", defaults={'page': 1})
@bp.route("/sitelog/<int:page>")
@login_required
def view_sitelog(page):
    """ Here we can see a log of admin activity on the site """

    if not config.site.sitelog_public and not current_user.can_admin:
        abort(404)

    s1 = SiteLog.select(SiteLog.time, SiteLog.action, SiteLog.desc, SiteLog.link, SiteLog.uid, SQL("'' as sub"),
                        SiteLog.target)
    s2 = SubLog.select(SubLog.time, SubLog.action, SubLog.desc, SubLog.link, SubLog.uid, Sub.name.alias('sub'),
                       SubLog.target)
    s2 = s2.join(Sub).where(SubLog.admin == True)
    logs = (s1 | s2)
    logs = logs.order_by(logs.c.time.desc()).paginate(page, 50)

    return engine.get_template('site/log.html').render({'logs': logs, 'page': page})


@bp.route("/p/<pid>")
def view_post_inbox(pid):
    """ Gets route to post from just pid """
    try:
        post = SubPost.get(SubPost.pid == pid)
    except SubPost.DoesNotExist:
        return abort(404)
    return redirect(url_for('sub.view_post', sub=post.sid.name, pid=post.pid))


@bp.route("/c/<cid>")
def view_comment_inbox(cid):
    """ Gets route to post from just cid """
    try:
        comm = SubPostComment.get(SubPostComment.cid == cid)
    except SubPost.DoesNotExist:
        return abort(404)
    return redirect(url_for('sub.view_perm', sub=comm.pid.sid.name, pid=comm.pid_id, cid=comm.cid))


@bp.route("/m/<sublist>", defaults={'page': 1})
@bp.route("/m/<sublist>/<int:page>")
def view_multisub_new(sublist, page=1):
    """ The multi index page, sorted as most recent posted first """
    names = sublist.split('+')
    if len(names) > 20:
        names = names[20:]

    subs = Sub.select(Sub.sid, Sub.name, Sub.title).where(Sub.name << names)
    sids = [x.sid for x in subs]

    posts = misc.getPostList(misc.postListQueryBase().where(Sub.sid << sids),
                             'new', page).dicts()
    return render_template('indexmulti.html', page=page,
                           posts=posts, subs=subs, sublist=sublist,
                           sort_type='site.view_multisub_new', kw={'subs': sublist})
