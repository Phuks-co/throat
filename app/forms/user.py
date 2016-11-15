""" User-related forms """
from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, PasswordField, TextField, TextAreaField
from wtforms import BooleanField
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


class CreateUserMessageForm(FlaskForm):
    """ CreateUserMessage form. """
    subject = StringField('subject',
                          validators=[DataRequired(), Length(min=2, max=32)])

    content = TextAreaField('message',
                            validators=[DataRequired(),
                                        Length(min=2, max=128)])


class CreateUserBadgeForm(FlaskForm):
    """ CreateUserBadge form. """
    badge = StringField('fa-xxxx-x fa-xxxx',
                        validators=[DataRequired(), Length(min=2, max=32)])
    name = StringField('Badge name',
                       validators=[DataRequired(), Length(min=2, max=128)])
    text = StringField('Badge description',
                       validators=[DataRequired(), Length(min=2, max=128)])


class LogOutForm(FlaskForm):
    """ Logout form. This form has no fields.
        We only use it for the CSRF stuff"""
    pass
