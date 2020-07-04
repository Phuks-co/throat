""" Mod endpoints """
import time
import re
from peewee import fn, JOIN
from pyotp import TOTP
from flask import Blueprint, abort, redirect, url_for, session, render_template
from flask_login import login_required, current_user
from flask_babel import _
from .. import misc
from ..forms import TOTPForm, LogOutForm, UseInviteCodeForm, AssignUserBadgeForm, EditModForm, BanDomainForm
from ..models import UserMetadata, User, Sub, SubPost, SubPostComment, SubPostCommentVote, SubPostVote, SiteMetadata
from ..models import UserUploads
from ..misc import engine
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
    """ WIP: Mod View """

    if not current_user.is_mod:
        abort(404)

    return render_template('mod/mod.html')
