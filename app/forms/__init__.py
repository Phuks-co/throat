""" Uhh... Here we import stuff """
from flask_wtf import FlaskForm, RecaptchaField

from .user import RegistrationForm, LoginForm, LogOutForm, PasswordResetForm
from .user import CreateUserMessageForm, EditUserForm, PasswordRecoveryForm
from .sub import CreateSubForm, EditSubForm, EditSubTextPostForm, EditSubFlair
from .sub import CreateSubTextPost, CreateSubLinkPost, EditCommentForm
from .sub import PostComment, DeletePost, EditSubLinkPostForm, SearchForm
from .sub import BanUserSubForm, EditPostFlair, EditSubCSSForm, EditMod2Form
from .sub import CreateSubFlair, DeleteSubFlair, VoteForm, DeleteCommentForm
from .admin import CreateUserBadgeForm, EditModForm, UseBTCdonationForm
from .admin import BanDomainForm


class DummyForm(FlaskForm):
    """ This is here only for the csrf token. """
    pass


class CaptchaForm(FlaskForm):
    """ Captcha form. """
    recaptcha = RecaptchaField('Captcha')
