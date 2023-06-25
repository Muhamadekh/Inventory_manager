from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Length, EqualTo
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
        shop_stock_list = []
        if current_user.user_role == 'Admin':
            for shop in current_user.shops:
                for stock in shop.stock:
                    shop_stock_list.append(stock)
        else:
            shop = Shop.query.filter_by(id=current_user.id)
            for stock in shop.stock:
                shop_stock_list.append(stock)
        self.item_name.choices = [(item.id, item.item_name) for item in shop_stock_list]

    def get_selected_item_id(self):
        selected_item_id = self.item_name.data
        if selected_item_id is not None:
            return int(selected_item_id)
        else:
            return 0


payment_methods_list = ['Cash', 'Orange Money', 'Credit', 'Bank']


class ShopStockSoldForm(FlaskForm):
    item_name = SelectField('Select Item Name', choices=[])
    item_quantity = IntegerField('Quantity Sold', validators=[DataRequired()])
    item_discount = IntegerField('Discount', validators=[DataRequired()])
    payment_method = SelectField('Payment Method', choices=payment_methods_list)
    submit = SubmitField('Record Sales')

    def populate_item_name_choices(self):
        shop_stock_list = []
        for shop in current_user.shops:
            for stock in shop.stock:
                shop_stock_list.append(stock)
        self.item_name.choices = [(item.id, item.item_name) for item in shop_stock_list]

    def get_selected_item_id(self):
        selected_item_id = self.item_name.data
        if selected_item_id is not None:
            return int(selected_item_id)
        else:
            return 0


class StoreRegistrationForm(FlaskForm):
    store_name = StringField('Store Name', validators=[DataRequired(), Length(min=4)])
    location = StringField('Location', validators=[DataRequired()])
    submit = SubmitField('Register')


class StoreNewItemForm(FlaskForm):
    item_name = StringField('Item Name', validators=[DataRequired()])
    item_cost_price = IntegerField('Cost Price', validators=[DataRequired()])
    item_selling_price = IntegerField('Selling Price', validators=[DataRequired()])
    item_quantity = IntegerField('Quantity', validators=[DataRequired()])
    submit = SubmitField('Add Item')


class StoreStockInForm(FlaskForm):
    item_name = SelectField('Select Item', choices=[])
    item_quantity = IntegerField('Quantity Received', validators=[DataRequired()])
    item_cost_price = IntegerField('Cost Price', validators=[DataRequired()])
    item_selling_price = IntegerField('Selling Price', validators=[DataRequired()])
    submit = SubmitField('Receive Stock')

    def populate_item_name_choices(self):
        store_stock_list = []
        for store in current_user.stores:
            print(store.store_name)
            for stock in store.store_stock:
                print(store.store_stock)
                store_stock_list.append(stock)
        self.item_name.choices = [(item.id, item.item_name) for item in store_stock_list]

    def get_selected_item_id(self):
        selected_item_id = self.item_name.data
        if selected_item_id is not None:
            return int(selected_item_id)
        else:
            return 0


class StoreStockOutForm(FlaskForm):
    item_name = SelectField('Select Item', choices=[])
    item_quantity = IntegerField('Quantity Received', validators=[DataRequired()])
    shop = SelectField('Select Shop', choices=[])
    submit = SubmitField('Send Stock')

    def populate_item_name_choices(self):
        store_stock_list = []
        for store in current_user.stores:
            for stock in store.store_stock:
                store_stock_list.append(stock)
        self.item_name.choices = [(item.id, item.item_name) for item in store_stock_list]

    def populate_shop_choices(self):
        self.shop.choices = [(shop.id, shop.shop_name) for shop in Shop.query.all()]

    def get_selected_item_id(self):
        selected_item_id = self.item_name.data
        if selected_item_id is not None:
            return int(selected_item_id)
        else:
            return 0

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
    submit = SubmitField('Save')
