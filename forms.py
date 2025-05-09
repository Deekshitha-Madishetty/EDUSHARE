# EDUSHARE/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, DecimalField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, NumberRange, Optional
from models import User # Assuming your User model is in models.py

# --- Custom Validator for Institutional Email ---
def institutional_email(form, field):
    if not field.data.lower().endswith('@gnits.ac.in'):
        raise ValidationError('Only institutional email addresses (@gnits.ac.in) are allowed.')

class RegistrationForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email(), institutional_email]) # Add custom validator here
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        # The institutional_email validator handles the domain check.
        # This one still checks for overall uniqueness.
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered. Please choose a different one or login.')

class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()]) # No need for institutional_email here if registration enforces it
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class AddBookForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=100)])
    author = StringField('Author', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description (Optional)', validators=[Optional(), Length(max=1000)])
    price = DecimalField('Price (USD, leave 0 or empty for donation)',
                         validators=[Optional(), NumberRange(min=0)],
                         places=2, rounding=None, default=0.00)
    is_donation = BooleanField('This is a Donation')
    submit = SubmitField('List Book')