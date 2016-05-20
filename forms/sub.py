""" Sub-related forms """

from flask_wtf import Form
from wtforms import StringField
from wtforms.validators import DataRequired, Length


class CreateSubForm(Form):
    """ Sub creation form """
    subname = StringField('Sub name',
                          validators=[DataRequired(), Length(min=2, max=32)])

    title = StringField('Title',
                        validators=[DataRequired(), Length(min=2, max=128)])
