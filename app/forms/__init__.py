""" Uhh... Here we import stuff """
from flask_wtf import Form

from .user import RegistrationForm, LoginForm, LogOutForm
from .user import CreateUserMessageForm, EditUserForm
from .sub import CreateSubForm, EditSubForm
from .sub import CreateSubTextPost, CreateSubLinkPost
from .sub import PostComment


class DummyForm(Form):
    """ This is here only for the csrf token. """
    pass
