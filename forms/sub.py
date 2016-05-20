from flask_wtf import Form
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Length

class CreateSubForm(Form):
    subname = StringField('Sub name', validators=[DataRequired(), Length(min=2, max=32)])
    title = PasswordField('Title', validators=[DataRequired(), Length(min=2, max=128)])
