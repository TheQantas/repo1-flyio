from wtforms import StringField, PasswordField, SubmitField, validators
from flask_wtf import FlaskForm

class LoginForm(FlaskForm):
    username = StringField('Username Or Email Address', validators=[validators.input_required()])
    password  = PasswordField('Password', validators=[validators.input_required()])
    submit = SubmitField('Login')