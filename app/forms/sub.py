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

    nsfw = BooleanField('Sub is NSFW?')


class EditSubForm(Form):
    """ Edit sub form. """
    title = StringField('Title',
                        validators=[DataRequired(), Length(min=2, max=128)])

    css = TextAreaField('Custom stylesheet', validators=[Length(max=10000)])
    nsfw = BooleanField('Sub is NSFW')
    restricted = BooleanField('Only mods can post')
    usercanflair = BooleanField('Allow users to flair their own posts')
    flair1 = StringField('Flair 1')
    flair2 = StringField('Flair 2')
    flair3 = StringField('Flair 3')
    flair4 = StringField('Flair 4')
    flair5 = StringField('Flair 5')
    flair6 = StringField('Flair 6')
    flair7 = StringField('Flair 7')
    flair8 = StringField('Flair 8')


class EditModForm(Form):
    """ Edit owner of sub (admin) """
    sub = StringField('Sub',
                      validators=[DataRequired(), Length(min=2, max=128)])
    user = StringField('New owner username',
                       validators=[DataRequired(), Length(min=1, max=128)])


class EditMod2Form(Form):
    """ Edit mod2 of sub (admin/owner) """
    user = StringField('New mod username',
                       validators=[DataRequired(), Length(min=1, max=128)])


class CreateSubTextPost(Form):
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


class CreateSubLinkPost(Form):
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


class EditSubTextPostForm(Form):
    """ Sub content edit form """
    content = TextAreaField('Post content',
                            validators=[DataRequired(),
                                        Length(min=1, max=16384)])
    nsfw = BooleanField('NSFW?')


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
