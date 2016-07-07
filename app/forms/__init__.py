""" Uhh... Here we import stuff """
from flask_wtf import Form

from .user import RegistrationForm, LoginForm, LogOutForm
from .user import CreateUserMessageForm, EditUserForm, CreateUserBadgeForm
from .sub import CreateSubForm, EditSubForm, EditSubTextPostForm
from .sub import CreateSubTextPost, CreateSubLinkPost, EditModForm, EditMod2Form
from .sub import PostComment, DeletePost, EditSubLinkPostForm, SearchForm
from .sub import BanUserSubForm


class DummyForm(Form):
    """ This is here only for the csrf token. """
    pass
