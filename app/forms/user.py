""" User-related forms """
from flask_wtf import Form, RecaptchaField
from wtforms import StringField, PasswordField, TextField, BooleanField
from wtforms.validators import DataRequired, Length, Email, Required, EqualTo
from wtforms.fields.html5 import EmailField


class LoginForm(Form):
    """ Login form. """
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=32)])
    password = PasswordField('Password', validators=[DataRequired(),
                                                     Length(min=7, max=256)])


class RegistrationForm(Form):
    """ Registration form. """
    username = TextField('Username', [Length(min=2, max=32)])
    email = EmailField('Email Address',
                       validators=[Email("Please enter your email address.")])
    password = PasswordField('Password', [
        Required(),
        EqualTo('confirm', message='Passwords must match'),
        Length(min=7, max=256)
    ])
    confirm = PasswordField('Repeat Password')
    accept_tos = BooleanField('I accept the TOS', [Required()])
    recaptcha = RecaptchaField()


class LogOutForm(Form):
    """ Logout form. This form has no fields.
        We only use it for the CSRF stuff"""
    pass
