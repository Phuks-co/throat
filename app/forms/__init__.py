""" Uhh... Here we import stuff """
from flask_wtf import FlaskForm

from .user import RegistrationForm, LoginForm, LogOutForm
from .user import CreateUserMessageForm, EditUserForm, CreateUserBadgeForm
from .sub import CreateSubForm, EditSubForm, EditSubTextPostForm, EditSubFlair
from .sub import CreateSubTextPost, CreateSubLinkPost, EditModForm
from .sub import PostComment, DeletePost, EditSubLinkPostForm, SearchForm
from .sub import BanUserSubForm, EditPostFlair, EditSubCSSForm, EditMod2Form
from .sub import CreateSubFlair, DeleteSubFlair


class DummyForm(FlaskForm):
    """ This is here only for the csrf token. """
    pass
