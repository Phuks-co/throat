""" Uhh... Here we import stuff """
from flask_wtf import FlaskForm

from .user import RegistrationForm, LoginForm, LogOutForm, PasswordResetForm
from .user import CreateUserMessageForm, EditUserForm, PasswordRecoveryForm
from .user import ChangePasswordForm, DeleteAccountForm
from .sub import CreateSubForm, EditSubForm, EditSubTextPostForm, EditSubFlair, EditSubRule
from .sub import CreateSubPostForm, EditCommentForm
from .sub import PostComment, DeletePost, EditSubLinkPostForm, SearchForm
from .sub import BanUserSubForm, EditPostFlair, EditSubCSSForm, EditMod2Form
from .sub import CreateSubFlair, DeleteSubFlair, VoteForm, DeleteCommentForm, CreateSubRule, DeleteSubRule
from .admin import EditModForm
from .admin import BanDomainForm, UseInviteCodeForm, AssignUserBadgeForm
from .admin import SecurityQuestionForm, TOTPForm, WikiForm, CreateInviteCodeForm


class DummyForm(FlaskForm):
    """ This is here only for the csrf token. """
    pass
