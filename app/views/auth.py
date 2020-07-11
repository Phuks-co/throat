""" Authentication endpoints and functions """
from urllib.parse import urlparse
from datetime import datetime
import uuid
import bcrypt
from peewee import fn
from flask import Blueprint, request, redirect, abort, url_for, session
from flask_login import current_user, login_user
from flask_babel import _
from .. import misc, config
from ..forms import LoginForm, RegistrationForm
from ..misc import engine
from ..models import User, UserMetadata, InviteCode, SubSubscriber, rconn, SiteMetadata

bp = Blueprint('auth', __name__)


def sanitize_serv(serv):
    serv = serv.replace("%253A", "%3A")
    return serv.replace("%252F", "%2F")


def handle_cas_ok(uid):
    # Create Session Ticket and store it in Redis
    token = str(uuid.uuid4())
    rconn.setex(name='cas-' + token, value=uid, time=30)
    # 2 - Send the ticket over to `service` with the ticket parameter
    return redirect(sanitize_serv(request.args.get('service')) + '&ticket=' + token)


@bp.route("/proxyValidate", methods=['GET'])
def sso_proxy_validate():
    if not request.args.get('ticket') or not request.args.get('service'):
        abort(400)

    red_c = rconn.get('cas-' + request.args.get('ticket'))

    if red_c:
        try:
            user = User.get((User.uid == red_c.decode()) & (User.status << (0, 100)))
        except User.DoesNotExist:
            return "<cas:serviceResponse xmlns:cas='http://www.yale.edu/tp/cas'><cas:authenticationFailure code=\"INVALID_TICKET\">" + _(
                'User not found or invalid ticket') + "</cas:authenticationFailure></cas:serviceResponse>", 401

        return "<cas:serviceResponse xmlns:cas='http://www.yale.edu/tp/cas'><cas:authenticationSuccess><cas:user>{0}</cas:user></cas:authenticationSuccess></cas:serviceResponse>".format(
            user.name.lower()), 200
    else:
        return "<cas:serviceResponse xmlns:cas='http://www.yale.edu/tp/cas'><cas:authenticationFailure code=\"INVALID_TICKET\">" + _(
            'User not found or invalid ticket') + "</cas:authenticationFailure></cas:serviceResponse>", 401


@bp.route("/register", methods=['GET', 'POST'])
def register():
    """ Endpoint for the registration form """
    if current_user.is_authenticated:
        return redirect(url_for('home.index'))
    form = RegistrationForm()
    form.cap_key, form.cap_b64 = misc.create_captcha()

    try:
        enable_registration = SiteMetadata.get(SiteMetadata.key == 'enable_registration')
        if enable_registration.value in ('False', '0'):
            return engine.get_template('user/registeration_disabled.html').render({'test': 'test'})
    except SiteMetadata.DoesNotExist:
        pass

    if not form.validate():
        return engine.get_template('user/register.html').render({'error': misc.get_errors(form, True), 'regform': form})

    if not misc.validate_captcha(form.ctok.data, form.captcha.data):
        return engine.get_template('user/register.html').render({'error': _("Invalid captcha."), 'regform': form})

    if not misc.allowedNames.match(form.username.data):
        return engine.get_template('user/register.html').render(
            {'error': _("Username has invalid characters."), 'regform': form})
    # check if user or email are in use
    try:
        User.get(fn.Lower(User.name) == form.username.data.lower())
        return engine.get_template('user/register.html').render(
            {'error': _("Username is not available."), 'regform': form})
    except User.DoesNotExist:
        pass

    if form.email.data:
        try:
            User.get(User.email == form.email.data)
            return engine.get_template('user/register.html').render(
                {'error': _("E-mail address is already in use."), 'regform': form})
        except User.DoesNotExist:
            pass

    if config.site.enable_security_question:
        if form.securityanswer.data.lower() != session['sa'].lower():
            return engine.get_template('user/register.html').render(
                {'error': _("Incorrect answer for security question."), 'regform': form})

    if misc.enableInviteCode():
        if not form.invitecode.data:
            return engine.get_template('user/register.html').render(
                {'error': _("Invalid invite code."), 'regform': form})
        # Check if there's a valid invite code in the database
        try:
            invcode = InviteCode.get((InviteCode.code == form.invitecode.data) &
                                     (InviteCode.expires.is_null() | (
                                             InviteCode.expires > datetime.utcnow())))
            if invcode.uses >= invcode.max_uses:
                return engine.get_template('user/register.html').render(
                    {'error': _("Invalid invite code."), 'regform': form})
        except InviteCode.DoesNotExist:
            return engine.get_template('user/register.html').render(
                {'error': _("Invalid invite code."), 'regform': form})

        invcode.uses += 1
        invcode.save()

    password = bcrypt.hashpw(form.password.data.encode('utf-8'), bcrypt.gensalt())

    user = User.create(uid=str(uuid.uuid4()), name=form.username.data, crypto=1, password=password,
                       email=form.email.data, joindate=datetime.utcnow())
    if misc.enableInviteCode():
        UserMetadata.create(uid=user.uid, key='invitecode', value=form.invitecode.data)
    # defaults
    defaults = misc.getDefaultSubs()
    subs = [{'uid': user.uid, 'sid': x['sid'], 'status': 1, 'time': datetime.utcnow()} for x in defaults]
    SubSubscriber.insert_many(subs).execute()
    theuser = misc.load_user(user.uid)
    login_user(theuser, remember=True)
    return redirect(url_for('wiki.welcome'))


@bp.route("/login", methods=['GET', 'POST'])
def login():
    """ Endpoint for the login form """
    if request.args.get('service'):
        # CAS login. Verify that we trust the initiator.
        url = urlparse(request.args.get('service'))
        if url.netloc not in config.site.cas_authorized_hosts:
            abort(403)

        if current_user.is_authenticated:
            # User is auth'd. Return ticket.
            return handle_cas_ok(uid=current_user.uid)

    if current_user.is_authenticated:
        return redirect(url_for('home.index'))
    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = User.get(fn.Lower(User.name) == form.username.data.lower())
        except User.DoesNotExist:
            return engine.get_template('user/login.html').render(
                {'error': _("Invalid username or password."), 'loginform': form})

        if user.status != 0:
            return engine.get_template('user/login.html').render(
                {'error': _("Invalid username or password."), 'loginform': form})

        if user.crypto == 1:  # bcrypt
            thash = bcrypt.hashpw(form.password.data.encode('utf-8'),
                                  user.password.encode('utf-8'))
            if thash == user.password.encode('utf-8'):
                theuser = misc.load_user(user.uid)
                login_user(theuser, remember=form.remember.data)
                if request.args.get('service'):
                    return handle_cas_ok(uid=user.uid)
                else:
                    return form.redirect('index')
            else:
                return engine.get_template('user/login.html').render(
                    {'error': _("Invalid username or password."), 'loginform': form})
        else:  # Unknown hash
            return engine.get_template('user/login.html').render(
                {'error': _("Something went really really wrong here."), 'loginform': form})
    return engine.get_template('user/login.html').render({'error': misc.get_errors(form, True), 'loginform': form})
