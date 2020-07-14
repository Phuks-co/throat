""" admin-related forms """

from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, TextField, TextAreaField
from wtforms import IntegerField
from wtforms.validators import DataRequired, Length, Regexp
from flask_babel import lazy_gettext as _l


class SecurityQuestionForm(FlaskForm):
    """ Create security question """
    question = TextField(_l('Question'), validators=[DataRequired()])
    answer = TextField('Answer', validators=[DataRequired()])


class EditModForm(FlaskForm):
    """ Edit owner of sub (admin) """
    sub = StringField(_l('Sub'),
                      validators=[DataRequired(), Length(min=2, max=128)])
    user = StringField(_l('New owner username'),
                       validators=[DataRequired(), Length(min=1, max=128)])


class AssignUserBadgeForm(FlaskForm):
    """ Assign user badge to user (admin) """
    badge = StringField(_l('Badge nick'),
                      validators=[DataRequired(), Length(min=1, max=128)])
    user = StringField(_l('Username'),
                       validators=[DataRequired(), Length(min=1, max=128)])


class BanDomainForm(FlaskForm):
    """ Add banned domain """
    domain = StringField(_l('Enter Domain'))


class UseInviteCodeForm(FlaskForm):
    """ Enable/Use an invite code to register """
    enableinvitecode = BooleanField(_l('Enable invite code to register'))
    minlevel = IntegerField(_l("Minimum level to create invite codes"))
    maxcodes = IntegerField(_l("Max amount of invites per user"))


class TOTPForm(FlaskForm):
    """ TOTP form for admin 2FA """
    totp = StringField(_l('Enter one-time password'))


class WikiForm(FlaskForm):
    """ Form creation/editing form """
    slug = StringField(_l("Slug (URL)"), validators=[DataRequired(), Length(min=1, max=128), Regexp('[a-z0-9]+')])
    title = StringField(_l("Page title"), validators=[DataRequired(), Length(min=1, max=255)])

    content = TextAreaField(_l("Content"), validators=[DataRequired(), Length(min=1, max=16384)])


class CreateInviteCodeForm(FlaskForm):
    code = StringField(_l("Code (empty to generate random)"))
    uses = IntegerField(_l("Uses"), validators=[DataRequired()])
    expires = StringField(_l("Expiration date"))
