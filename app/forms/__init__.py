""" Uhh... Here we import stuff """
from flask_wtf import FlaskForm

from .user import RegistrationForm, LoginForm, LogOutForm, PasswordResetForm
from .user import CreateUserMessageForm, EditUserForm, PasswordRecoveryForm
from .user import ChangePasswordForm, DeleteAccountForm
from .sub import CreateSubForm, EditSubForm, EditSubTextPostForm, EditSubFlair
from .sub import CreateSubTextPost, CreateSubLinkPost, EditCommentForm
from .sub import PostComment, DeletePost, EditSubLinkPostForm, SearchForm
from .sub import BanUserSubForm, EditPostFlair, EditSubCSSForm, EditMod2Form
from .sub import CreateSubFlair, DeleteSubFlair, VoteForm, DeleteCommentForm
from .sub import CreteSubPostCaptcha
from .admin import EditModForm
from .admin import BanDomainForm, UseInviteCodeForm, AssignUserBadgeForm
from .admin import SecurityQuestionForm, TOTPForm


class DummyForm(FlaskForm):
    """ This is here only for the csrf token. """
    pass
