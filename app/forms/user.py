""" User-related forms """
from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, PasswordField, TextField, TextAreaField
from wtforms import BooleanField, HiddenField
from wtforms.validators import DataRequired, Length, Email, Required, EqualTo
from wtforms.validators import Optional
from wtforms.fields.html5 import EmailField


class LoginForm(FlaskForm):
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
    username = TextField('Username', [Length(min=2, max=32)])
    email = EmailField('Email Address (optional)',
                       validators=[OptionalIfFieldIsEmpty('email'),
                                   Email("Invalid email address.")])
    password = PasswordField('Password', [
        Required(),
        EqualTo('confirm', message='Passwords must match'),
        Length(min=7, max=256)
    ])
    confirm = PasswordField('Repeat Password')
    accept_tos = BooleanField('I accept the TOS', [Required()])
    recaptcha = RecaptchaField('Captcha')


class EditUserForm(FlaskForm):
    """ Edit User info form. """
    # username = TextField('Username', [Length(min=2, max=32)])
    email = EmailField('Email Address (optional)',
                       validators=[OptionalIfFieldIsEmpty('email'),
                                   Email("Invalid email address.")])
    external_links = BooleanField('Open external links in a new window')
    disable_sub_style = BooleanField('Disable custom sub styles')
    show_nsfw = BooleanField('Show NSFW content')
    recaptcha = RecaptchaField()
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


class CreateUserMessageForm(FlaskForm):
    """ CreateUserMessage form. """
    to = HiddenField()
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


class LogOutForm(FlaskForm):
    """ Logout form. This form has no fields.
        We only use it for the CSRF stuff"""
    pass
