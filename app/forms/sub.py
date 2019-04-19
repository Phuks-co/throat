""" Sub-related forms """

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, HiddenField
from wtforms import RadioField, TextField
from wtforms.validators import DataRequired, Length, URL
from wtforms.validators import Optional


class SearchForm(FlaskForm):
    """ Search form """
    term = StringField('Search')


class CreateSubForm(FlaskForm):
    """ Sub creation form """
    subname = StringField('Sub name',
                          validators=[DataRequired(), Length(min=2, max=32)])
    title = StringField('Title',
                        validators=[DataRequired(), Length(min=2, max=50)])

    nsfw = BooleanField('Sub is NSFW?')


class EditSubCSSForm(FlaskForm):
    """ Edit sub stylesheet form. """
    css = TextAreaField('Custom stylesheet', validators=[Length(max=10000)])


class DeleteCommentForm(FlaskForm):
    """ Removes a comment in a post """
    cid = HiddenField()  # comment id
    reason = StringField()


class EditCommentForm(FlaskForm):
    """ Edits a comment in a post """
    cid = HiddenField()  # comment id
    text = TextAreaField('Your comment',
                         validators=[DataRequired(),
                                     Length(min=1, max=16384)])


class CreateSubFlair(FlaskForm):
    """ Creates a flair """
    text = StringField('Flair text', validators=[DataRequired(),
                                                 Length(max=25)])


class EditSubFlair(FlaskForm):
    """ Edits ONE flair from a sub """
    flair = HiddenField()
    text = StringField('Flair text', validators=[DataRequired(),
                                                 Length(max=22)])


class DeleteSubFlair(FlaskForm):
    """ Used to delete flairs """
    flair = HiddenField()


class EditSubForm(FlaskForm):
    """ Edit sub form. """
    title = StringField('Title',
                        validators=[DataRequired(), Length(min=2, max=128)])

    nsfw = BooleanField('Sub is NSFW')
    restricted = BooleanField('Only mods can post')
    usercanflair = BooleanField('Allow users to flair their own posts')
    videomode = BooleanField('Enable video player (youtube links only)')
    polling = BooleanField('Enable polls')
    subsort = RadioField('Default sub page post sorting',
                         choices=[('v', 'Hot'), ('v_two', 'New'),
                                  ('v_three', 'Top')],
                         validators=[Optional()])
    subtags = StringField('Tags')
    sidebar = TextAreaField('Sidebar text',
                            validators=[Length(max=8000)])


class EditMod2Form(FlaskForm):
    """ Edit mod2 of sub (admin/owner) """
    user = StringField('New mod username',
                       validators=[DataRequired(), Length(min=1, max=128)])


class CreateSubTextPost(FlaskForm):
    """ Sub content submission form """
    sub = StringField('Sub', validators=[DataRequired(),
                                         Length(min=2, max=32)])
    title = StringField('Post title',
                        validators=[DataRequired(), Length(min=4, max=350)])
    content = TextAreaField('Post content',
                            validators=[Length(max=16384)])
    link = StringField('Post link',
                       validators=[Length(min=10, max=256), Optional(),
                                   URL(require_tld=True)])
    ptype = RadioField('Post type',
                       choices=[('text', 'Text post'), ('link', 'Link post'), ('poll', 'Poll post')],
                       validators=[DataRequired()])
    nsfw = BooleanField('NSFW?')
    # for polls.
    hideresults = BooleanField('Hide poll results until it closes')
    closetime = StringField('Poll closing')

    def __init__(self, *args, **kwargs):
        super(CreateSubTextPost, self).__init__(*args, **kwargs)
        try:
            self.sub.data = kwargs['sub']
        except KeyError:
            pass


class CreteSubPostCaptcha(CreateSubTextPost):
    captcha = TextField('Captcha')
    ctok = HiddenField()


class CreateSubLinkPost(FlaskForm):
    """ Sub content submission form """
    sub = StringField('Sub', validators=[DataRequired(),
                                         Length(min=2, max=32)])
    title = StringField('Post title',
                        validators=[DataRequired(), Length(min=4, max=350)])
    link = StringField('Post link',
                       validators=[DataRequired(), Length(min=10, max=256),
                                   URL(require_tld=True)])
    nsfw = BooleanField('NSFW?')

    def __init__(self, *args, **kwargs):
        super(CreateSubLinkPost, self).__init__(*args, **kwargs)
        try:
            self.sub.data = kwargs['sub']
        except KeyError:
            pass


class EditSubTextPostForm(FlaskForm):
    """ Sub content edit form """
    content = TextAreaField('Post content',
                            validators=[DataRequired(),
                                        Length(min=1, max=16384)])


class EditSubLinkPostForm(FlaskForm):
    """ Sub content edit form """
    nsfw = BooleanField('NSFW?')


class PostComment(FlaskForm):
    """ Comment submission form """
    post = HiddenField()
    parent = HiddenField()

    comment = TextAreaField('Your comment',
                            validators=[DataRequired(),
                                        Length(min=1, max=16384)])


class BanUserSubForm(FlaskForm):
    """ Edit ban user from posting """
    user = StringField('username to ban',
                       validators=[DataRequired(), Length(min=1, max=128)])
    reason = StringField('reason for the ban', validators=[DataRequired(), Length(min=1, max=128)])


class EditPostFlair(FlaskForm):
    """ Post deletion form. """
    post = HiddenField()
    flair = RadioField('Flair',
                       choices=[],
                       validators=[DataRequired()])


class DeletePost(FlaskForm):
    """ Post deletion form. """
    post = HiddenField()
    reason = StringField()


class VoteForm(FlaskForm):
    """ form for voting """
    post = HiddenField()  # Post PID
