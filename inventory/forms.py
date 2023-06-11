from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Length, EqualTo
from inventory.models import User, Stock
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
    remember = BooleanField('Remembe Me')
    submit = SubmitField('Sign in')


class ShopNewItemForm(FlaskForm):
    item_name = StringField('Item Name', validators=[DataRequired()])
    item_price = IntegerField('Price', validators=[DataRequired()])
    item_quantity = IntegerField('Quantity', validators=[DataRequired()])
    submit = SubmitField('Add Item')


class ShopStockReceivedForm(FlaskForm):
    item_name = SelectField('Select Item Name', choices=[])
    item_quantity = IntegerField('Quantity Received', validators=[DataRequired()])
    submit = SubmitField('Receive Stock')

    def populate_item_name_choices(self):
        self.item_name.choices = [(item.id, item.item_name) for item in Stock.query.all()]

    def get_selected_item_id(self):
        selected_item_id = self.item_name.data
        if selected_item_id is not None:
            return int(selected_item_id)
        else:
            return 0


class ShopStockSoldForm(FlaskForm):
    item_name = SelectField('Select Item Name', choices=[])
    item_quantity = IntegerField('Quantity Sold', validators=[DataRequired()])
    item_discount = IntegerField('Discount', validators=[DataRequired()])
    submit = SubmitField('Record Sales')

    def populate_item_name_choices(self):
        self.item_name.choices = [(item.id, item.item_name) for item in Stock.query.all()]

    def get_selected_item_id(self):
        selected_item_id = self.item_name.data
        if selected_item_id is not None:
            return int(selected_item_id)
        else:
            return 0

