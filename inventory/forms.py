from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, EqualTo
from inventory.models import User, Shop


user_role_choices = ['Admin', 'Staff']


class UserRegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm password', validators=[DataRequired(), EqualTo('password')])
    user_role = SelectField('User Role', choices=user_role_choices)
    submit = SubmitField('Register')


class ShopRegistrationForm(FlaskForm):
    shop_name = StringField('Username', validators=[DataRequired(), Length(min=4)])
    location = StringField('Location', validators=[DataRequired()])
    submit = SubmitField('Register')



class LoginForm(FlaskForm):
    username = StringField('username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    shop_name = SelectField('Select your shop', choices=[])
    submit = SubmitField('Sign in')

    def populate_shop_choices(self):
        # This method will be called from a route to populate the shop choices dynamically
        self.shop_name.choices = [(shop.id, shop.shop_name) for shop in Shop.query.all()]
