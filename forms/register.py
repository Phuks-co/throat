from flask_wtf import Form
from wtforms import TextField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Length, Email, Required, EqualTo
from wtforms.fields.html5 import EmailField  


class RegistrationForm(Form):
    username = TextField('Username', [Length(min=2, max=32)])
    email = EmailField('Email Address', [Email("Please enter your email address.")])
    password = PasswordField('Password', [
        Required(),
        EqualTo('confirm', message='Passwords must match'),
        Length(min=7, max=256)
    ])
    confirm = PasswordField('Repeat Password')
    accept_tos = BooleanField('I accept the TOS', [Required()])
