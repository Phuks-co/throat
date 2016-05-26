""" Uhh... Here we import stuff """
from flask_wtf import Form

from .user import RegistrationForm, LoginForm, LogOutForm
from .user import CreateUserMessageForm
from .sub import CreateSubForm, CreateSubTextPost, PostComment


class DummyForm(Form):
    """ This is here only for the csrf token. """
    pass
