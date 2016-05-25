""" Sub-related forms """

from flask_wtf import Form
from wtforms import StringField, TextAreaField, BooleanField, HiddenField
from wtforms.validators import DataRequired, Length


class CreateSubForm(Form):
    """ Sub creation form """
    subname = StringField('Sub name',
                          validators=[DataRequired(), Length(min=2, max=32)])
    title = StringField('Title',
                        validators=[DataRequired(), Length(min=2, max=128)])

    nsfw = BooleanField('NSFW?')


class CreateSubTextPost(Form):
    """ Sub content submission form """
    title = StringField('Post title',
                        validators=[DataRequired(), Length(min=4, max=128)])
    content = TextAreaField('Post content',
                            validators=[DataRequired(),
                                        Length(min=1, max=16384)])


class PostComment(Form):
    """ Comment submission form """
    sub = HiddenField()
    post = HiddenField()
    parent = HiddenField()

    comment = TextAreaField('Your comment',
                            validators=[DataRequired(),
                                        Length(min=1, max=2048)])
