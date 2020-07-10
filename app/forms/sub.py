""" Sub-related forms """

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, HiddenField
from wtforms import RadioField, SelectField, FieldList
from wtforms.validators import DataRequired, Length, URL
from wtforms.validators import Optional
from flask_babel import lazy_gettext as _l


class SearchForm(FlaskForm):
    """ Search form """
    term = StringField(_l('Search'))


class CreateSubForm(FlaskForm):
    """ Sub creation form """
    subname = StringField(_l('Sub name'),
                          validators=[DataRequired(), Length(min=2, max=32)])
    title = StringField(_l('Title'),
                        validators=[DataRequired(), Length(min=2, max=50)])

    nsfw = BooleanField(_l('Sub is NSFW?'))


class EditSubCSSForm(FlaskForm):
    """ Edit sub stylesheet form. """
    css = TextAreaField(_l('Custom stylesheet'), validators=[Length(max=10000)])


class DeleteCommentForm(FlaskForm):
    """ Removes a comment in a post """
    cid = HiddenField()  # comment id
    reason = StringField()


class EditCommentForm(FlaskForm):
    """ Edits a comment in a post """
    cid = HiddenField()  # comment id
    text = TextAreaField(_l('Your comment'),
                         validators=[DataRequired(), Length(min=1, max=16384)])


class CreateSubFlair(FlaskForm):
    """ Creates a flair """
    text = StringField(_l('Flair text'), validators=[DataRequired(), Length(max=25)])


class EditSubFlair(FlaskForm):
    """ Edits ONE flair from a sub """
    flair = HiddenField()
    text = StringField(_l('Flair text'), validators=[DataRequired(), Length(max=22)])


class DeleteSubFlair(FlaskForm):
    """ Used to delete flairs """
    flair = HiddenField()


class CreateSubRule(FlaskForm):
    """ Creates a rule """
    text = StringField(_l('Rule text'), validators=[DataRequired(), Length(max=25)])


class EditSubRule(FlaskForm):
    """ Edits ONE rule from a sub """
    rule = HiddenField()
    text = StringField(_l('Rule text'), validators=[DataRequired(), Length(max=22)])


class DeleteSubRule(FlaskForm):
    """ Used to delete rules """
    rule = HiddenField()


class EditSubForm(FlaskForm):
    """ Edit sub form. """
    title = StringField(_l('Title'),
                        validators=[DataRequired(), Length(min=2, max=128)])

    nsfw = BooleanField(_l('Sub is NSFW'))
    restricted = BooleanField(_l('Only mods can post'))
    usercanflair = BooleanField(_l('Allow users to flair their own posts'))
    videomode = BooleanField(_l('Enable video player (youtube links only)'))
    polling = BooleanField(_l('Enable polls'))
    subsort = RadioField(_l('Default sub page post sorting'),
                         choices=[('v', 'Hot'), ('v_two', 'New'),
                                  ('v_three', 'Top')],
                         validators=[Optional()])
    sidebar = TextAreaField(_l('Sidebar text'), validators=[Length(max=8000)])
    sublogprivate = BooleanField(_l('Make the sub log private'))


class EditMod2Form(FlaskForm):
    """ Edit mod2 of sub (admin/owner) """
    user = StringField(_l('New mod username'), validators=[DataRequired(), Length(min=1, max=128)])
    level = SelectField(_l('Mod level'), choices=[('1', _l('Moderator')), ('2', _l('Janitor'))],
                        validators=[DataRequired()])


class CreateSubPostForm(FlaskForm):
    """ Sub content submission form """
    sub = StringField(_l('Sub'), validators=[DataRequired(), Length(min=2, max=32)])
    title = StringField(_l('Post title'), validators=[DataRequired(), Length(min=3, max=350)])
    content = TextAreaField(_l('Post content'), validators=[Length(max=16384)])
    link = StringField(_l('Post link'), validators=[Length(min=10, max=256), Optional(), URL(require_tld=True)])
    ptype = RadioField(_l('Post type'),
                       choices=[('text', _l('Text post')), ('link', _l('Link post'))],
                       validators=[DataRequired()])
    nsfw = BooleanField(_l('NSFW?'))
    # for polls.
    options = FieldList(StringField(_l('Option')), max_entries=6)
    hideresults = BooleanField(_l('Hide poll results until it closes'))
    closetime = StringField(_l('Poll closing time'))

    captcha = StringField(_l('Captcha'))
    ctok = HiddenField()


class EditSubTextPostForm(FlaskForm):
    """ Sub content edit form """
    content = TextAreaField(_l('Post content'), validators=[DataRequired(), Length(min=1, max=16384)])


class EditSubLinkPostForm(FlaskForm):
    """ Sub content edit form """
    nsfw = BooleanField(_l('NSFW?'))


class PostComment(FlaskForm):
    """ Comment submission form """
    post = HiddenField()
    parent = HiddenField()

    comment = TextAreaField(_l('Write your comment here. Styling with Markdown format is supported.'),
                            validators=[DataRequired(), Length(min=1, max=16384)])


class BanUserSubForm(FlaskForm):
    """ Edit ban user from posting """
    user = StringField(_l('Username to ban'), validators=[DataRequired(), Length(min=1, max=128)])
    reason = StringField(_l('Reason for the ban'), validators=[DataRequired(), Length(min=1, max=128)])
    expires = StringField(_l('ban expires'))


class EditPostFlair(FlaskForm):
    """ Post deletion form. """
    post = HiddenField()
    flair = RadioField(_l('Flair'), choices=[], validators=[DataRequired()])


class DeletePost(FlaskForm):
    """ Post deletion form. """
    post = HiddenField()
    reason = StringField()
    send_to_admin = BooleanField()


class VoteForm(FlaskForm):
    """ form for voting """
    post = HiddenField()  # Post PID
