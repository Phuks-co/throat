""" User-related forms """
from flask import request, redirect, url_for
from urllib.parse import urlparse, urljoin
from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, PasswordField, TextField, TextAreaField
from wtforms import BooleanField, HiddenField
from wtforms.validators import DataRequired, Length, Email, Required, EqualTo
from wtforms.validators import Optional, Regexp
from wtforms.fields.html5 import EmailField


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def get_redirect_target():
    for target in request.args.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return target


class RedirectForm(FlaskForm):
    next = HiddenField()

    def __init__(self, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        if not self.next.data:
            self.next.data = get_redirect_target() or ''

    def redirect(self, endpoint='index', **values):
        if is_safe_url(self.next.data):
            return redirect(self.next.data)
        target = get_redirect_target()
        return redirect(target or url_for(endpoint, **values))


class LoginForm(RedirectForm):
    """ Login form. """
    username = StringField('Username',
                           validators=[DataRequired(), Length(max=32)])
    password = PasswordField('Password', validators=[DataRequired(),
                                                     Length(min=7, max=256)])
    remember = BooleanField('Remember me')


class OptionalIfFieldIsEmpty(Optional):
    """ A custom field validator. """
    def __init__(self, field_name, *args, **kwargs):
        self.field_name = field_name
        super(OptionalIfFieldIsEmpty, self).__init__(*args, **kwargs)

    def __call__(self, form, field):
        other_field = form._fields.get(self.field_name)
        if other_field is None:
            raise Exception('no field named "{0}" in form'
                            .format(self.field_name))
        if other_field.data == '':
            super(OptionalIfFieldIsEmpty, self).__call__(form, field)


class RegistrationForm(FlaskForm):
    """ Registration form. """
    username = TextField('Username', [Length(min=2, max=32),
                                      Regexp(r'[a-zA-Z0-9_-]+')])
    email = EmailField('Email Address (optional)',
                       validators=[OptionalIfFieldIsEmpty('email'),
                                   Email("Invalid email address.")])
    password = PasswordField('Password', [
        Required(),
        EqualTo('confirm', message='Passwords must match'),
        Length(min=7, max=256)
    ])
    confirm = PasswordField('Repeat Password')
    invitecode = TextField('Invite Code')
    accept_tos = BooleanField('I accept the TOS', [Required()])
    captcha = TextField('Captcha')
    ctok = HiddenField()
    securityanswer = TextField('Security question')


class EditUserForm(FlaskForm):
    """ Edit User info form. """
    # username = TextField('Username', [Length(min=2, max=32)])
    email = EmailField('Email Address (optional)',
                       validators=[OptionalIfFieldIsEmpty('email'),
                                   Email("Invalid email address.")])
    external_links = BooleanField('Open external links in a new window')
    disable_sub_style = BooleanField('Disable custom sub styles')
    show_nsfw = BooleanField('Show NSFW content')
    password = PasswordField('New password', [
        OptionalIfFieldIsEmpty('password'),
        EqualTo('confirm', message='Passwords must match'),
        Length(min=7, max=256),
    ])
    confirm = PasswordField('Repeat Password', [
        OptionalIfFieldIsEmpty('password')
    ])

    oldpassword = PasswordField('Your current password', [
        Required(),
        Length(min=7, max=256)
    ])

    delete_account = BooleanField('DELETE THIS ACCOUNT')
    experimental = BooleanField('Enable experimental features')
    noscroll = BooleanField('Disable infinite scroll')
    nochat = BooleanField('Disable chat')


class CreateUserMessageForm(FlaskForm):
    """ CreateUserMessage form. """
    to = TextField('to', [Length(min=2, max=32), Regexp(r'[a-zA-Z0-9_-]+')])
    subject = StringField('subject',
                          validators=[DataRequired(), Length(min=1, max=400)])

    content = TextAreaField('message',
                            validators=[DataRequired(),
                                        Length(min=1, max=16384)])


class PasswordRecoveryForm(FlaskForm):
    """ the 'forgot your password?' form """
    email = EmailField('Email Address',
                       validators=[Email("Invalid email address.")])
    recaptcha = RecaptchaField('Captcha')


class PasswordResetForm(FlaskForm):
    """ the 'forgot your password?' form """
    user = HiddenField()
    key = HiddenField()
    password = PasswordField('Password', [
        Required(),
        EqualTo('confirm', message='Passwords must match'),
        Length(min=7, max=256)
    ])
    confirm = PasswordField('Repeat Password')


class CreateMulti(FlaskForm):
    """ Creates a Multi """
    name = StringField('Nickname', validators=[DataRequired(), Length(max=40)])
    subs = StringField('sub1+sub2+sub3+sub4', validators=[DataRequired(), Length(max=255)])


class EditMulti(FlaskForm):
    """ Edits ONE Multi """
    multi = HiddenField()
    name = StringField('Nickname', validators=[DataRequired(), Length(max=40)])
    subs = StringField('sub1+sub2+sub3+sub4', validators=[DataRequired(), Length(max=255)])


class DeleteMulti(FlaskForm):
    """ Used to delete Multis """
    multi = HiddenField()


class LogOutForm(FlaskForm):
    """ Logout form. This form has no fields.
        We only use it for the CSRF stuff"""
    pass
