from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, BooleanField, IntegerField, SearchField
from wtforms.validators import DataRequired, Length, EqualTo, Optional
from inventory.models import User, Shop
from flask import session
from flask_login import current_user


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
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remembe Me')
    submit = SubmitField('Sign in')


class ShopNewItemForm(FlaskForm):
    item_name = SearchField('Search Item Name')
    item_quantity = IntegerField('Quantity', validators=[DataRequired()])
    submit = SubmitField('Add Item')


class ShopStockReceivedForm(FlaskForm):
    item_name = SearchField('Search Item Name')
    item_quantity = IntegerField('Quantity Received', validators=[DataRequired()])
    submit = SubmitField('Receive Stock')


payment_methods_list = ['Cash', 'Orange Money', 'Credit', 'Bank']


class ShopStockSoldForm(FlaskForm):
    item_name = SearchField('Search Item Name')
    item_quantity = IntegerField('Quantity Sold', validators=[DataRequired()])
    item_discount = IntegerField('Discount', validators=[Optional()])
    submit = SubmitField('Add')


class SaleForm(FlaskForm):
    sale_discount = IntegerField('Sale Discount', validators=[Optional()])
    payment_method = SelectField('Payment Method', choices=payment_methods_list, default=None)
    transaction_id = StringField('Transaction ID', validators=[Optional()])
    submit = SubmitField('Record Sale')


class StoreRegistrationForm(FlaskForm):
    store_name = StringField('Store Name', validators=[DataRequired(), Length(min=4)])
    location = StringField('Location', validators=[DataRequired()])
    submit = SubmitField('Register')


class StoreNewItemForm(FlaskForm):
    item_name = StringField('Item Name', validators=[DataRequired()])
    item_cost_price = IntegerField('Cost Price', validators=[DataRequired()])
    item_selling_price = IntegerField('Selling Price', validators=[DataRequired()])
    submit = SubmitField('Add Item')


class StoreStockInForm(FlaskForm):
    item_name = SearchField('Search Item Name')
    item_quantity = IntegerField('Quantity Received', validators=[DataRequired()])
    submit = SubmitField('Receive Stock')


class StoreStockOutForm(FlaskForm):
    item_name = SearchField('Search Item Name')
    item_quantity = IntegerField('Quantity Received', validators=[DataRequired()])
    shop = SelectField('Select Shop', choices=[])
    submit = SubmitField('Send Stock')

    def populate_shop_choices(self):
        self.shop.choices = [(shop.id, shop.shop_name) for shop in Shop.query.all()]

    def get_selected_shop_id(self):
        selected_shop_id = self.shop.data
        if selected_shop_id is not None:
            return int(selected_shop_id)
        else:
            return 0


class DebtorRegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=4)])
    company_name = StringField('Company Name', validators=[DataRequired(), Length(min=4)])
    phone_number = StringField('Phone Number', validators=[DataRequired()])
    amount_paid = IntegerField('Amount Paid', validators=[Optional()])
    submit = SubmitField('Save')


class ShopKeeperRegistrationForm(FlaskForm):
    shopkeeper = SelectField('Select a shopkeeper', choices=[])
    submit = SubmitField('Assign')

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


class AccountRegistrationForm(FlaskForm):
    account_name = StringField('Account Name', validators=[DataRequired(), Length(min=4)])
    submit = SubmitField('Add')