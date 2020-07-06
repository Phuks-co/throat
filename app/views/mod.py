""" Mod endpoints """
import time
import re
from peewee import fn, JOIN, Value
from pyotp import TOTP
from flask import Blueprint, abort, redirect, url_for, session, render_template, jsonify
from flask_login import login_required, current_user
from flask_babel import _
from .. import misc
from ..forms import TOTPForm, LogOutForm, UseInviteCodeForm, AssignUserBadgeForm, EditModForm, BanDomainForm
from ..models import UserMetadata, User, Sub, SubPost, SubPostComment, SubPostCommentVote, SubPostVote, SiteMetadata
from ..models import User, Sub, SubMod, SubPost, SubPostComment, UserMetadata, SubPostReport, SubPostCommentReport
from ..misc import engine, getSubReports, getModSubs, engine
from ..badges import badges

bp = Blueprint('mod', __name__)


@bp.route('/mod/auth', methods=['GET', 'POST'])
@login_required
def auth():
    if not current_user.is_mod:
        abort(404)
    form = TOTPForm()
    try:
        user_secret = UserMetadata.get((UserMetadata.uid == current_user.uid) & (UserMetadata.key == 'totp_secret'))
    except UserMetadata.DoesNotExist:
        return engine.get_template('mod/totp.html').render({'authform': form, 'error': _('No TOTP secret found.')})
    if form.validate_on_submit():
        totp = TOTP(user_secret.value)
        if totp.verify(form.totp.data):
            session['apriv'] = time.time()
            return redirect(url_for('mod.index'))
        else:
            return engine.get_template('mod/totp.html').render(
                {'authform': form, 'error': _('Invalid or expired token.')})
    return engine.get_template('mod/totp.html').render({'authform': form, 'error': None})


@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    if not current_user.is_mod:
        abort(404)
    form = LogOutForm()
    if form.validate():
        del session['apriv']
    return redirect(url_for('mod.index'))


@bp.route("/")
@login_required
def index():
    """ WIP: Mod Dashboard """

    if not current_user.is_mod:
        abort(404)

    subs = getModSubs(current_user.uid)

    return render_template('mod/mod.html', subs=subs)


@bp.route("/reports", defaults={'page': 1})
@bp.route("/reports/<int:page>")
@login_required
def reports(page):
    """ WIP: Open Report Queue """

    if not current_user.is_mod:
        abort(404)

    mod_subs = getModSubs(current_user.uid)

    def isSubMod(sid, mod_subs):
        # return True if current user is Mod of sub given a post ID
        for sub in mod_subs:
            str(sid) in sub.sid
        return True

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
        .switch(SubPostReport).join(SubPost).join(Sub).where(isSubMod(Sub.sid, mod_subs) == True) \
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
        .switch(SubPostCommentReport).join(SubPostComment).join(SubPost).join(Sub).where(isSubMod(Sub.sid, mod_subs) == True) \
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
    """ WIP: Open Closed List """

    if not current_user.is_mod:
        abort(404)

    mod_subs = getModSubs(current_user.uid)

    def isSubMod(sid, mod_subs):
        # return True if current user is Mod of sub given a post ID
        for sub in mod_subs:
            str(sid) in sub.sid
        return True

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
        .switch(SubPostReport).join(SubPost).join(Sub).where(isSubMod(Sub.sid, mod_subs) == True) \
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
        .switch(SubPostCommentReport).join(SubPostComment).join(SubPost).join(Sub).where(isSubMod(Sub.sid, mod_subs) == True) \
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
