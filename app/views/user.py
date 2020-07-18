""" Profile and settings endpoints """
import time
from peewee import fn, JOIN
from flask import Blueprint, render_template, abort, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_babel import _, Locale
from .do import uid_from_recovery_token, info_from_email_confirmation_token
from .. import misc, config
from ..auth import auth_provider, email_validation_is_required
from ..misc import engine, send_email
from ..forms import EditUserForm, CreateUserMessageForm, EditAccountForm, DeleteAccountForm, PasswordRecoveryForm
from ..forms import PasswordResetForm
from ..models import User, UserStatus, UserMetadata
from ..models import Sub, SubMod, SubPost, SubPostComment, UserSaved, InviteCode

bp = Blueprint('user', __name__)


@bp.route("/u/<user>")
def view(user):
    """ WIP: View user's profile, posts, comments, badges, etc """
    try:
        user = User.get(fn.lower(User.name) == user.lower())
    except User.DoesNotExist:
        abort(404)

    if user.status == 10:
        abort(404)

    modsquery = SubMod.select(Sub.name, SubMod.power_level).join(Sub).where(
        (SubMod.uid == user.uid) & (SubMod.invite == False))
    owns = [x.sub.name for x in modsquery if x.power_level == 0]
    mods = [x.sub.name for x in modsquery if 1 <= x.power_level <= 2]
    invitecodeinfo = misc.getInviteCodeInfo(user.uid)
    badges = misc.getUserBadges(user.uid)
    pcount = SubPost.select().where(SubPost.uid == user.uid).count()
    ccount = SubPostComment.select().where(SubPostComment.uid == user.uid).count()

    habit = Sub.select(Sub.name, fn.Count(SubPost.pid).alias('count')).join(SubPost, JOIN.LEFT_OUTER,
                                                                            on=(SubPost.sid == Sub.sid))
    habit = habit.where(SubPost.uid == user.uid).group_by(Sub.sid).order_by(fn.Count(SubPost.pid).desc()).limit(10)

    level, xp = misc.get_user_level(user.uid)

    if xp > 0:
        currlv = (level ** 2) * 10
        nextlv = ((level + 1) ** 2) * 10

        required_xp = nextlv - currlv
        progress = ((xp - currlv) / required_xp) * 100
    else:
        progress = 0

    givenScore = misc.getUserGivenScore(user.uid)

    return engine.get_template('user/profile.html').render(
        {'user': user, 'level': level, 'progress': progress, 'postCount': pcount, 'commentCount': ccount,
         'givenScore': givenScore, 'invitecodeinfo': invitecodeinfo, 'badges': badges, 'owns': owns, 'mods': mods, 'habits': habit,
         'msgform': CreateUserMessageForm()})


@bp.route("/u/<user>/posts", defaults={'page': 1})
@bp.route("/u/<user>/posts/<int:page>")
def view_user_posts(user, page):
    """ WIP: View user's recent posts """
    try:
        user = User.get(fn.Lower(User.name) == user.lower())
    except User.DoesNotExist:
        abort(404)
    if user.status == 10:
        abort(404)

    if current_user.is_admin():
        posts = misc.getPostList(misc.postListQueryBase(adminDetail=True).where(User.uid == user.uid),
                                 'new', page).dicts()
    else:
        posts = misc.getPostList(misc.postListQueryBase(noAllFilter=True).where(User.uid == user.uid),
                                 'new', page).dicts()
    return render_template('userposts.html', page=page, sort_type='user.view_user_posts',
                           posts=posts, user=user)


@bp.route("/u/<user>/savedposts", defaults={'page': 1})
@bp.route("/u/<user>/savedposts/<int:page>")
@login_required
def view_user_savedposts(user, page):
    """ WIP: View user's saved posts """
    if current_user.name.lower() == user.lower():
        posts = misc.getPostList(
            misc.postListQueryBase(noAllFilter=True).join(UserSaved, on=(UserSaved.pid == SubPost.pid)).where(
                UserSaved.uid == current_user.uid),
            'new', page).dicts()
        return render_template('userposts.html', page=page,
                               sort_type='user.view_user_savedposts',
                               posts=posts, user=current_user)
    else:
        abort(403)


@bp.route("/u/<user>/comments", defaults={'page': 1})
@bp.route("/u/<user>/comments/<int:page>")
def view_user_comments(user, page):
    """ WIP: View user's recent comments """
    try:
        user = User.get(fn.Lower(User.name) == user.lower())
    except User.DoesNotExist:
        abort(404)
    if user.status == 10:
        abort(404)

    comments = misc.getUserComments(user.uid, page)
    return render_template('usercomments.html', user=user, page=page, comments=comments)


@bp.route("/settings/invite")
@login_required
def invite_codes():
    if not misc.enableInviteCode():
        return redirect('/settings')

    codes = InviteCode.select().where(InviteCode.user == current_user.uid)
    maxcodes = int(misc.getMaxCodes(current_user.uid))
    created = codes.count()
    avail = 0
    if (maxcodes - created) >= 0:
        avail = maxcodes - created
    return engine.get_template('user/settings/invitecode.html').render(
        {'codes': codes, 'created': created, 'max': maxcodes, 'avail': avail,
         'user': User.get(User.uid == current_user.uid)})


@bp.route('/settings/subs')
@login_required
def edit_subs():
    return engine.get_template('user/topbar.html').render({})


@bp.route("/settings")
@login_required
def edit_user():
    styles = 'nostyles' in current_user.prefs
    nsfw = 'nsfw' in current_user.prefs
    exp = 'labrat' in current_user.prefs
    noscroll = 'noscroll' in current_user.prefs
    nochat = 'nochat' in current_user.prefs
    form = EditUserForm(show_nsfw=nsfw,
                        disable_sub_style=styles, experimental=exp,
                        noscroll=noscroll, nochat=nochat, subtheme=current_user.subtheme,
                        language=current_user.language)
    languages = config.app.languages
    form.language.choices = [('', _('Auto detect'))]
    for i in languages:
        form.language.choices.append((i, Locale(*i.split("_")).display_name.capitalize()))
    return engine.get_template('user/settings/preferences.html').render({'edituserform': form, 'user': User.get(User.uid == current_user.uid)})


@bp.route("/settings/account")
@login_required
def edit_account():
    return engine.get_template('user/settings/account.html').render(
        {'form': EditAccountForm(),
         'user': User.get(User.uid == current_user.uid)})


@bp.route('/settings/account/confirm-email/<token>')
def confirm_email_change(token):
    info = info_from_email_confirmation_token(token)
    user = None
    try:
        user = User.get(User.uid == info['uid'])
    except (TypeError, User.DoesNotExist):
        flash(_('The link you used is invalid or has expired'), 'error')
        return redirect(url_for('user.edit_account'))

    if user.status == UserStatus.OK:
        auth_provider.confirm_pending_email(user, info['email'])
        flash(_('Your password recovery email address is now confirmed!'), 'message')
        return redirect(url_for('user.edit_account'))
    return redirect(url_for('home.index'))


@bp.route("/settings/delete")
@login_required
def delete_account():
    return engine.get_template('user/settings/delete.html').render({'form': DeleteAccountForm(), 'user': User.get(User.uid == current_user.uid)})


@bp.route("/recover")
def password_recovery():
    """ Endpoint for the password recovery form """
    if current_user.is_authenticated:
        return redirect(url_for('home.index'))
    form = PasswordRecoveryForm()
    form.cap_key, form.cap_b64 = misc.create_captcha()
    return engine.get_template('user/password_recovery.html').render({'lpform': form})


@bp.route('/reset/<token>')
def password_reset(token):
    """ The page that actually resets the password """
    user = None
    try:
        user = User.get(User.uid == uid_from_recovery_token(token))
    except User.DoesNotExist:
        pass
    if user == None or user.status != UserStatus.OK:
        flash(_('Password reset link was invalid or expired'), 'error')
        return redirect(url_for('user.password_recovery'))

    if current_user.is_authenticated:
        return redirect(url_for('home.index'))

    form = PasswordResetForm(key=token, user=user.uid)
    return engine.get_template('user/password_reset.html').render({'lpform': form})
