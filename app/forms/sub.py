""" Sub-related forms """

from flask_wtf import Form
from wtforms import StringField, TextAreaField, BooleanField, HiddenField
from wtforms.validators import DataRequired, Length, URL


class CreateSubForm(Form):
    """ Sub creation form """
    subname = StringField('Sub name',
                          validators=[DataRequired(), Length(min=2, max=32)])
    title = StringField('Title',
                        validators=[DataRequired(), Length(min=2, max=128)])

    nsfw = BooleanField('NSFW?')


class EditSubForm(Form):
    """ Edit sub. form. """
    title = StringField('Title',
                        validators=[DataRequired(), Length(min=2, max=128)])


class CreateSubTextPost(Form):
    """ Sub content submission form """
    title = StringField('Post title',
                        validators=[DataRequired(), Length(min=4, max=128)])
    content = TextAreaField('Post content',
                            validators=[DataRequired(),
                                        Length(min=1, max=16384)])


class EditSubTextPostForm(Form):
    """ Sub content edit form """
    content = TextAreaField('Post content',
                            validators=[DataRequired(),
                                        Length(min=1, max=16384)])


class CreateSubLinkPost(Form):
    """ Sub content submission form """
    title = StringField('Post title',
                        validators=[DataRequired(), Length(min=4, max=128)])
    link = StringField('Post link',
                       validators=[DataRequired(), Length(min=10, max=128),
                                   URL(require_tld=True)])


class PostComment(Form):
    """ Comment submission form """
    sub = HiddenField()
    post = HiddenField()
    parent = HiddenField()

    comment = TextAreaField('Your comment',
                            validators=[DataRequired(),
                                        Length(min=1, max=2048)])


class DeletePost(Form):
    """ Post deletion form. """
    post = HiddenField()
