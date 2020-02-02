""" admin-related forms """

from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, TextField
from wtforms import IntegerField
from wtforms.validators import DataRequired, Length


class SecurityQuestionForm(FlaskForm):
    """ Create security question """
    question = TextField('Question', validators=[DataRequired()])
    answer = TextField('Answer', validators=[DataRequired()])


class EditModForm(FlaskForm):
    """ Edit owner of sub (admin) """
    sub = StringField('Sub',
                      validators=[DataRequired(), Length(min=2, max=128)])
    user = StringField('New owner username',
                       validators=[DataRequired(), Length(min=1, max=128)])


class CreateUserBadgeForm(FlaskForm):
    """ CreateUserBadge form. """
    badge = StringField('fa-xxxx-x fa-xxxx',
                        validators=[DataRequired(), Length(min=2, max=32)])
    name = StringField('Badge name',
                       validators=[DataRequired(), Length(min=2, max=128)])
    text = StringField('Badge description',
                       validators=[DataRequired(), Length(min=2, max=128)])
    value = IntegerField('XP value')


class AssignUserBadgeForm(FlaskForm):
    """ Assign user badge to user (admin) """
    badge = StringField('Badge nick',
                      validators=[DataRequired(), Length(min=1, max=128)])
    user = StringField('Username',
                       validators=[DataRequired(), Length(min=1, max=128)])


class BanDomainForm(FlaskForm):
    """ Add banned domain """
    domain = StringField('Enter Domain')


class UseInviteCodeForm(FlaskForm):
    """ Enable/Use an invite code to register """
    enableinvitecode = BooleanField('Enable invite code to register')
    minlevel = IntegerField("Minimum level to create invite codes")
    maxcodes = IntegerField("Max amount of invites per user")

class TOTPForm(FlaskForm):
    """ TOTP form for admin 2FA """
    totp = StringField('Enter one-time password')
