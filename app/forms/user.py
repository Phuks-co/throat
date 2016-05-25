""" User-related forms """
from flask_wtf import Form, RecaptchaField
from wtforms import StringField, PasswordField, TextField, BooleanField
from wtforms.validators import DataRequired, Length, Email, Required, EqualTo
from wtforms.validators import Optional
from wtforms.fields.html5 import EmailField


class LoginForm(Form):
    """ Login form. """
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=32)])
    password = PasswordField('Password', validators=[DataRequired(),
                                                     Length(min=7, max=256)])


class OptionalIfFieldIsEmpty(Optional):
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


class RegistrationForm(Form):
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
    recaptcha = RecaptchaField()


class LogOutForm(Form):
    """ Logout form. This form has no fields.
        We only use it for the CSRF stuff"""
    pass
