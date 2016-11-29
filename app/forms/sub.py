""" Sub-related forms """

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, HiddenField
from wtforms import RadioField
from wtforms.validators import DataRequired, Length, URL, Optional


class SearchForm(FlaskForm):
    """ Search form """
    term = StringField('Search')


class CreateSubForm(FlaskForm):
    """ Sub creation form """
    subname = StringField('Sub name',
                          validators=[DataRequired(), Length(min=2, max=32)])
    title = StringField('Title',
                        validators=[DataRequired(), Length(min=2, max=128)])

    nsfw = BooleanField('Sub is NSFW?')


class EditSubCSSForm(FlaskForm):
    """ Edit sub stylesheet form. """
    css = TextAreaField('Custom stylesheet', validators=[Length(max=10000)])

class EditSubFlair(FlaskForm):
    """ Edits ONE flair from a sub """
    flair = HiddenField()
    text = StringField('Flair text', validators=[DataRequired(),
                                                 Length(max=64)])

class CreateSubFlair(FlaskForm):
    """ Creates a flair """
    text = StringField('Flair text', validators=[DataRequired(),
                                                 Length(max=64)])

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
    subsort = RadioField('Default sub page post sorting',
                         choices=[('v', 'Hot'), ('v_two', 'New'),
                                  ('v_three', 'Top')],
                         validators=[Optional()])


class EditModForm(FlaskForm):
    """ Edit owner of sub (admin) """
    sub = StringField('Sub',
                      validators=[DataRequired(), Length(min=2, max=128)])
    user = StringField('New owner username',
                       validators=[DataRequired(), Length(min=1, max=128)])


class EditMod2Form(FlaskForm):
    """ Edit mod2 of sub (admin/owner) """
    user = StringField('New mod username',
                       validators=[DataRequired(), Length(min=1, max=128)])


class CreateSubTextPost(FlaskForm):
    """ Sub content submission form """
    sub = StringField('Sub', validators=[DataRequired(),
                                         Length(min=2, max=32)])
    title = StringField('Post title',
                        validators=[DataRequired(), Length(min=4, max=128)])
    content = TextAreaField('Post content',
                            validators=[DataRequired(),
                                        Length(min=1, max=16384)])

    def __init__(self, *args, **kwargs):
        super(CreateSubTextPost, self).__init__(*args, **kwargs)
        try:
            self.sub.data = kwargs['sub']
        except KeyError:
            pass


class CreateSubLinkPost(FlaskForm):
    """ Sub content submission form """
    sub = StringField('Sub', validators=[DataRequired(),
                                         Length(min=2, max=32)])
    title = StringField('Post title',
                        validators=[DataRequired(), Length(min=4, max=128)])
    link = StringField('Post link',
                       validators=[DataRequired(), Length(min=10, max=128),
                                   URL(require_tld=True)])

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
    nsfw = BooleanField('NSFW?')


class EditSubLinkPostForm(FlaskForm):
    """ Sub content edit form """
    nsfw = BooleanField('NSFW?')


class PostComment(FlaskForm):
    """ Comment submission form """
    sub = HiddenField()
    post = HiddenField()
    parent = HiddenField()

    comment = TextAreaField('Your comment',
                            validators=[DataRequired(),
                                        Length(min=1, max=2048)])


class BanUserSubForm(FlaskForm):
    """ Edit ban user from posting """
    user = StringField('username to ban',
                       validators=[DataRequired(), Length(min=1, max=128)])


class EditPostFlair(FlaskForm):
    """ Post deletion form. """
    post = HiddenField()
    flair = RadioField('Flair',
                       choices=[],
                       validators=[DataRequired()])


class DeletePost(FlaskForm):
    """ Post deletion form. """
    post = HiddenField()
