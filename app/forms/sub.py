""" Sub-related forms """

from flask_wtf import Form
from wtforms import StringField, TextAreaField, BooleanField, HiddenField
from wtforms.validators import DataRequired, Length, URL


class SearchForm(Form):
    """ Search form """
    term = StringField('Search')


class CreateSubForm(Form):
    """ Sub creation form """
    subname = StringField('Sub name',
                          validators=[DataRequired(), Length(min=2, max=32)])
    title = StringField('Title',
                        validators=[DataRequired(), Length(min=2, max=128)])

    nsfw = BooleanField('NSFW?')


class EditSubForm(Form):
    """ Edit sub form. """
    title = StringField('Title',
                        validators=[DataRequired(), Length(min=2, max=128)])

    css = TextAreaField('Custom stylesheet', validators=[Length(max=10000)])
    nsfw = BooleanField('NSFW?')

class EditModForm(Form):
    """ Edit mod of sub (admin) """
    sub = StringField('Sub',
                        validators=[DataRequired(), Length(min=2, max=128)])
    user = StringField('New mod username',
                        validators=[DataRequired(), Length(min=1, max=128)])

class EditMod2Form(Form):
    """ Edit mod2 of sub (admin/owner) """
    user = StringField('New mod username',
                        validators=[DataRequired(), Length(min=1, max=128)])

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
    nsfw = BooleanField('NSFW?')


class CreateSubLinkPost(Form):
    """ Sub content submission form """
    title = StringField('Post title',
                        validators=[DataRequired(), Length(min=4, max=128)])
    link = StringField('Post link',
                       validators=[DataRequired(), Length(min=10, max=128),
                                   URL(require_tld=True)])


class EditSubLinkPostForm(Form):
    """ Sub content edit form """
    nsfw = BooleanField('NSFW?')


class PostComment(Form):
    """ Comment submission form """
    sub = HiddenField()
    post = HiddenField()
    parent = HiddenField()

    comment = TextAreaField('Your comment',
                            validators=[DataRequired(),
                                        Length(min=1, max=2048)])

class BanUserSubForm(Form):
    """ Edit ban user from posting """
    user = StringField('username to ban',
                        validators=[DataRequired(), Length(min=1, max=128)])




class DeletePost(Form):
    """ Post deletion form. """
    post = HiddenField()
