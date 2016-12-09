""" Uhh... Here we import stuff """
from flask_wtf import FlaskForm

from .user import RegistrationForm, LoginForm, LogOutForm, PasswordResetForm
from .user import CreateUserMessageForm, EditUserForm, PasswordRecoveryForm
from .sub import CreateSubForm, EditSubForm, EditSubTextPostForm, EditSubFlair
from .sub import CreateSubTextPost, CreateSubLinkPost
from .sub import PostComment, DeletePost, EditSubLinkPostForm, SearchForm
from .sub import BanUserSubForm, EditPostFlair, EditSubCSSForm, EditMod2Form
from .sub import CreateSubFlair, DeleteSubFlair, VoteForm
from .admin import CreateUserBadgeForm, EditModForm


class DummyForm(FlaskForm):
    """ This is here only for the csrf token. """
    pass
