from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Length, EqualTo
from inventory.models import User, Shop
from flask import session


user_role_choices = ['Admin', 'Staff']


class UserRegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm password', validators=[DataRequired(), EqualTo('password')])
    user_role = SelectField('User Role', choices=user_role_choices)
    submit = SubmitField('Register')


class ShopRegistrationForm(FlaskForm):
    shop_name = StringField('Shop Name', validators=[DataRequired(), Length(min=4)])
    location = StringField('Location', validators=[DataRequired()])
    shopkeeper = SelectField('Select a shopkeeper', choices=[])
    submit = SubmitField('Register')

    def populate_shopkeeper_choices(self):
        # This method will be called from a route to populate the user choices dynamically
        self.shopkeeper.choices = [(user.id, user.username) for user in User.query.all()]

    def get_selected_shopkeeper_id(self):
        selected_shopkeeper_id = self.shopkeeper.data
        if selected_shopkeeper_id is not None:
            return int(selected_shopkeeper_id)
        else:
            return 0

    def store_selected_shopkeeper_id_in_session(self):
        selected_shopkeeper_id = self.get_selected_shopkeeper_id()
        session['selected_shopkeeper_id'] = selected_shopkeeper_id
        print(selected_shopkeeper_id)


class LoginForm(FlaskForm):
    username = StringField('username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    # shop_name = SelectField('Select your shop', choices=[])
    submit = SubmitField('Sign in')



class ShopNewSTockForm(FlaskForm):
    item_name = StringField('Item Name', validators=[DataRequired()])
    item_price = IntegerField('Price', validators=[DataRequired()])
    item_quantity = IntegerField('Quantity', validators=[DataRequired()])
    submit = SubmitField('Add Item')

