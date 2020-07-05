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
    """ WIP: Report Queue """

    if not current_user.is_mod:
        abort(404)

    mod_subs = getModSubs(current_user.uid)

    def isSubMod(sid, mod_subs):
        # return True if current user is Mod of sub given a post ID
        for sub in mod_subs:
            str(sid) in sub.sid
        return True

    Reported = User.alias()
    posts_q = SubPostReport.select(
        Value('post').alias('type'),
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
        .join(Reported, on=Reported.uid == SubPost.uid) \
        .where(SubPostReport.open == True)

    comments_q = SubPostCommentReport.select(
        Value('comment').alias('type'),
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
        .join(Reported, on=Reported.uid == SubPostComment.uid) \
        .where(SubPostCommentReport.open == True)

    query = posts_q | comments_q
    query = query.order_by(query.c.datetime.desc())
    query = query.paginate(page, 50)

    return engine.get_template('mod/reports.html').render({'reports': list(query.dicts())})
