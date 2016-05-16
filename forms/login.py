from flask_wtf import Form
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Length

class LoginForm(Form):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=32)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=7, max=256)])
