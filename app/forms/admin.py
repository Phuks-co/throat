""" admin-related forms """

from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, TextAreaField, FileField
from wtforms import IntegerField, RadioField, FieldList, SelectField
from wtforms import HiddenField
from wtforms.validators import DataRequired, InputRequired, Length, Regexp
from flask_babel import lazy_gettext as _l


class SecurityQuestionForm(FlaskForm):
    """Create security question"""

    question = StringField(_l("Question"), validators=[DataRequired()])
    answer = StringField("Answer", validators=[DataRequired()])


class EditModForm(FlaskForm):
    """Edit owner of sub (admin)"""

    sub = StringField(_l("Sub"), validators=[DataRequired(), Length(min=2, max=128)])
    user = StringField(
        _l("New owner username"), validators=[DataRequired(), Length(min=1, max=128)]
    )


class AssignUserBadgeForm(FlaskForm):
    """Assign user badge to user (admin)"""

    badge = SelectField(_l("Badge"))
    user = StringField(
        _l("Username"), validators=[DataRequired(), Length(min=1, max=128)]
    )


class NewBadgeForm(FlaskForm):
    icon = FileField(_l("Badge Icon"), validators=[DataRequired()])
    name = StringField(
        _l("Badge Name"), validators=[DataRequired(), Length(min=1, max=34)]
    )
    alt = TextAreaField(_l("Badge Description"), validators=[Length(min=0, max=255)])
    score = IntegerField(_l("Score Adjustment"), validators=[DataRequired()])
    rank = IntegerField(_l("Sort"), validators=[DataRequired()])
    trigger = SelectField(_l("Trigger"))


class EditBadgeForm(FlaskForm):
    icon = FileField(_l("Badge Icon"))
    name = StringField(_l("Badge Name"), validators=[Length(min=1, max=34)])
    alt = TextAreaField(_l("Badge Description"), validators=[Length(min=0, max=255)])
    score = IntegerField(_l("Score Adjustment"))
    rank = IntegerField(_l("Sort"))
    trigger = SelectField(_l("Trigger"))


class BanDomainForm(FlaskForm):
    """Add banned domain"""

    domain = StringField(_l("Enter Domain"))


class UseInviteCodeForm(FlaskForm):
    """Enable/Use an invite code to register"""

    enableinvitecode = BooleanField(_l("Enable invite code to register"))
    invitations_visible_to_users = BooleanField(
        _l("Allow users to see who they invited and who invited them")
    )
    minlevel = IntegerField(_l("Minimum level to create invite codes"))
    maxcodes = IntegerField(_l("Max amount of invites per user"))


class UpdateInviteCodeForm(FlaskForm):
    """Update the expiration dates of selected invitecodes."""

    codes = FieldList(BooleanField(default=False))
    etype = RadioField(
        _l("Change selected codes to expire:"),
        choices=[("never", _l("Never")), ("now", _l("Now")), ("at", _l("At:"))],
        default="now",
        validators=[DataRequired()],
    )
    expires = StringField(_l("Expiration date"))


class TOTPForm(FlaskForm):
    """TOTP form for admin 2FA"""

    totp = StringField(_l("Enter one-time password"))


class WikiForm(FlaskForm):
    """Form creation/editing form"""

    slug = StringField(
        _l("Slug (URL)"),
        validators=[DataRequired(), Length(min=1, max=128), Regexp("[a-z0-9]+")],
    )
    title = StringField(
        _l("Page title"), validators=[DataRequired(), Length(min=1, max=255)]
    )

    content = TextAreaField(
        _l("Content"), validators=[DataRequired(), Length(min=1, max=16384)]
    )


class CreateInviteCodeForm(FlaskForm):
    code = StringField(_l("Code (empty to generate random)"))
    uses = IntegerField(_l("Uses"), validators=[DataRequired()])
    expires = StringField(_l("Expiration date"))


class SetSubOfTheDayForm(FlaskForm):
    sub = StringField(_l("Sub"))


class ChangeConfigSettingForm(FlaskForm):
    setting = HiddenField()
    value = StringField()


class LiteralBooleanField(SelectField):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            choices=["True", "False"],
            coerce=self._literally_true_or_false,
            validators=[InputRequired()],
            **kwargs,
        )

    @staticmethod
    def _literally_true_or_false(value: str) -> bool:
        if value == "True":
            return True
        elif value == "False":
            return False
        raise ValueError("Value is not either 'True' or 'False'.")


class LiteralBooleanForm(FlaskForm):
    value = LiteralBooleanField()
