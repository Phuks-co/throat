""" Mod endpoints """
import time
import re
from peewee import fn, JOIN, Value
from flask import Blueprint, abort, redirect, url_for, session, render_template, jsonify
from flask_login import login_required, current_user
from flask_babel import _
from .. import misc
from ..models import UserMetadata, User, Sub, SubPost, SubPostComment
from ..models import User, Sub, SubMod, SubPost, SubPostComment, UserMetadata, SubPostReport, SubPostCommentReport
from ..misc import engine, getSubReports, getModSubs

bp = Blueprint('mod', __name__)


@bp.route("/")
@login_required
def index():
    """ WIP: Mod Dashboard """

    if not (SubMod.select().where(SubMod.user == current_user.uid) or current_user.can_admin):
        abort(404)

    subs = getModSubs(current_user.uid, 1)

    updated_subs = []

    for sub in subs:
        # get the sub sid
        this_sub = Sub.select().where(Sub.sid == sub.sid).get()
        sid = str(this_sub.sid)
        # use sid to getSubReports
        reports = getSubReports(sid)
        # count open and closed reports
        open_reports_count = reports['open'].count()
        closed_reports_count = reports['closed'].count()
        # add open_report_count and closed_report_count as properties on sub

        updated_sub = {
            'name': str(this_sub.name) ,
            'subscribers': str(this_sub.subscribers),
            'open_reports_count': open_reports_count,
            'closed_reports_count': closed_reports_count
        }

        updated_subs = updated_subs + [updated_sub]
    return render_template('mod/mod.html', subs=updated_subs)


@bp.route("/reports", defaults={'page': 1})
@bp.route("/reports/<int:page>")
@login_required
def reports(page):
    """ WIP: Open Report Queue """

    if not (SubMod.select().where(SubMod.user == current_user.uid) or current_user.can_admin):
        abort(404)

    mod_subs = getModSubs(current_user.uid, 1)

    # Get all reports on posts and comments, filter by "open",
    # then filter by subs current user can Mod
    # also returns count of all open reports
    Reported = User.alias()
    posts_q = SubPostReport.select(
        Value('post').alias('type'),
        SubPostReport.id,
        SubPostReport.pid,
        Value(None).alias('cid'),
        User.name.alias('reporter'),
        Reported.name.alias('reported'),
        SubPostReport.datetime,
        SubPostReport.reason,
        SubPostReport.open,
        Sub.name.alias('sub')
    ).join(User, on=User.uid == SubPostReport.uid) \
        .switch(SubPostReport).join(SubPost).join(Sub).join(SubMod) \
        .where(SubMod.user == current_user.uid) \
        .join(Reported, on=Reported.uid == SubPost.uid)

    open_posts_q = posts_q.where(SubPostReport.open == True)
    closed_posts_q = posts_q.where(SubPostReport.open == False)


    comments_q = SubPostCommentReport.select(
        Value('comment').alias('type'),
        SubPostCommentReport.id,
        SubPostComment.pid,
        SubPostCommentReport.cid,
        User.name.alias('reporter'),
        Reported.name.alias('reported'),
        SubPostCommentReport.datetime,
        SubPostCommentReport.reason,
        SubPostCommentReport.open,
        Sub.name.alias('sub')
    ).join(User, on=User.uid == SubPostCommentReport.uid) \
        .switch(SubPostCommentReport).join(SubPostComment).join(SubPost).join(Sub).join(SubMod) \
        .where(SubMod.user == current_user.uid) \
        .join(Reported, on=Reported.uid == SubPostComment.uid)

    open_comments_q = comments_q.where(SubPostCommentReport.open == True)
    closed_comments_q = comments_q.where(SubPostCommentReport.open == False)

    open_query = open_posts_q | open_comments_q
    open_query = open_query.order_by(open_query.c.datetime.desc())
    open_report_count = open_query.count()

    closed_query = closed_posts_q | closed_comments_q
    closed_query = closed_query.order_by(closed_query.c.datetime.desc())
    closed_report_count = closed_query.count()

    open_query = open_query.paginate(page, 50)

    return engine.get_template('mod/reports.html').render(
        {'open_reports': list(open_query.dicts()), 'open_report_count': str(open_report_count), 'closed_report_count': str(closed_report_count)})


@bp.route("/reports/closed", defaults={'page': 1})
@bp.route("/reports/closed/<int:page>")
@login_required
def closed(page):
    """ WIP: Closed Reports List """


    if not (SubMod.select().where(SubMod.user == current_user.uid) or current_user.can_admin):
        abort(404)

    mod_subs = getModSubs(current_user.uid, 1)

    # Get all reports on posts and comments, filter by "open",
    # then filter by subs current user can Mod
    # also returns count of all open reports
    Reported = User.alias()
    posts_q = SubPostReport.select(
        Value('post').alias('type'),
        SubPostReport.id,
        SubPostReport.pid,
        Value(None).alias('cid'),
        User.name.alias('reporter'),
        Reported.name.alias('reported'),
        SubPostReport.datetime,
        SubPostReport.reason,
        SubPostReport.open.alias('open'),
        Sub.name.alias('sub')
    ).join(User, on=User.uid == SubPostReport.uid) \
        .switch(SubPostReport).join(SubPost).join(Sub).join(SubMod) \
        .where(SubMod.user == current_user.uid) \
        .join(Reported, on=Reported.uid == SubPost.uid)

    open_posts_q = posts_q.where(SubPostReport.open == True)
    closed_posts_q = posts_q.where(SubPostReport.open == False)


    comments_q = SubPostCommentReport.select(
        Value('comment').alias('type'),
        SubPostCommentReport.id,
        SubPostComment.pid,
        SubPostCommentReport.cid,
        User.name.alias('reporter'),
        Reported.name.alias('reported'),
        SubPostCommentReport.datetime,
        SubPostCommentReport.reason,
        SubPostCommentReport.open.alias('open'),
        Sub.name.alias('sub')
    ).join(User, on=User.uid == SubPostCommentReport.uid) \
        .switch(SubPostCommentReport).join(SubPostComment).join(SubPost).join(Sub).join(SubMod) \
        .where(SubMod.user == current_user.uid) \
        .join(Reported, on=Reported.uid == SubPostComment.uid)

    open_comments_q = comments_q.where(SubPostCommentReport.open == True)
    closed_comments_q = comments_q.where(SubPostCommentReport.open == False)

    open_query = open_posts_q | open_comments_q
    open_query = open_query.order_by(open_query.c.datetime.desc())
    open_report_count = open_query.count()

    closed_query = closed_posts_q | closed_comments_q
    closed_query = closed_query.order_by(closed_query.c.datetime.desc())
    closed_report_count = closed_query.count()

    closed_query = closed_query.paginate(page, 50)

    return engine.get_template('mod/closed.html').render(
        {'closed_reports': list(closed_query.dicts()), 'open_report_count': str(open_report_count), 'closed_report_count': str(closed_report_count)})


@bp.route("/reports/sub/<sid>", defaults={'page': 1})
@bp.route("/reports/sub/<sid>/<int:page>")
@login_required
def reports_sub(page):
    """ WIP: Open Report Queue """

    if not (SubMod.select().where(SubMod.user == current_user.uid) or current_user.can_admin):
        abort(404)

    mod_subs = getModSubs(current_user.uid, 1)

    # Get all reports on posts and comments, filter by "open",
    # then filter by subs current user can Mod
    # also returns count of all open reports
    Reported = User.alias()
    posts_q = SubPostReport.select(
        Value('post').alias('type'),
        SubPostReport.id,
        SubPostReport.pid,
        Value(None).alias('cid'),
        User.name.alias('reporter'),
        Reported.name.alias('reported'),
        SubPostReport.datetime,
        SubPostReport.reason,
        SubPostReport.open,
        Sub.name.alias('sub')
    ).join(User, on=User.uid == SubPostReport.uid) \
        .switch(SubPostReport).join(SubPost).join(Sub).join(SubMod) \
        .where(SubMod.user == current_user.uid) \
        .join(Reported, on=Reported.uid == SubPost.uid)

    open_posts_q = posts_q.where(SubPostReport.open == True)
    closed_posts_q = posts_q.where(SubPostReport.open == False)


    comments_q = SubPostCommentReport.select(
        Value('comment').alias('type'),
        SubPostCommentReport.id,
        SubPostComment.pid,
        SubPostCommentReport.cid,
        User.name.alias('reporter'),
        Reported.name.alias('reported'),
        SubPostCommentReport.datetime,
        SubPostCommentReport.reason,
        SubPostCommentReport.open,
        Sub.name.alias('sub')
    ).join(User, on=User.uid == SubPostCommentReport.uid) \
        .switch(SubPostCommentReport).join(SubPostComment).join(SubPost).join(Sub).join(SubMod) \
        .where(SubMod.user == current_user.uid) \
        .join(Reported, on=Reported.uid == SubPostComment.uid)

    open_comments_q = comments_q.where(SubPostCommentReport.open == True)
    closed_comments_q = comments_q.where(SubPostCommentReport.open == False)

    open_query = open_posts_q | open_comments_q
    open_query = open_query.order_by(open_query.c.datetime.desc())
    open_report_count = open_query.count()

    closed_query = closed_posts_q | closed_comments_q
    closed_query = closed_query.order_by(closed_query.c.datetime.desc())
    closed_report_count = closed_query.count()

    open_query = open_query.paginate(page, 50)

    return engine.get_template('mod/reports.html').render(
        {'open_reports': list(open_query.dicts()), 'open_report_count': str(open_report_count), 'closed_report_count': str(closed_report_count)})
