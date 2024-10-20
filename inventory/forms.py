from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, BooleanField, IntegerField, \
    SearchField, FloatField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Length, EqualTo, Optional
from inventory.models import User, Shop, Account, Sale, Store
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
    item_name = SearchField('Search Item Name', validators=[DataRequired()])
    item_quantity = IntegerField('Quantity Received', validators=[DataRequired()])
    submit = SubmitField('Receive Stock')


payment_methods_list = ['Cash', 'Orange Money', 'Bank']


class ShopStockSoldForm(FlaskForm):
    user_id = HiddenField('User ID')
    item_name = SearchField('Search Item Name', validators=[DataRequired()])
    item_quantity = IntegerField('Quantity Sold', validators=[DataRequired()])
    item_discount = IntegerField('Discount', validators=[Optional()])
    submit = SubmitField('Add')


class SaleForm(FlaskForm):
    user_id = HiddenField('User ID')
    sale_discount = IntegerField('Sale Discount', validators=[Optional()])
    payment_method = SelectField('Payment Method', choices=payment_methods_list, default=None)
    transaction_id = StringField('Transaction ID', validators=[Optional()])
    credit_option = BooleanField('Credit Option')
    submit = SubmitField('Record Sale')


class StoreRegistrationForm(FlaskForm):
    store_name = StringField('Store Name', validators=[DataRequired(), Length(min=4)])
    location = StringField('Location', validators=[DataRequired()])
    submit = SubmitField('Register')


class StoreNewItemForm(FlaskForm):
    item_name = StringField('Item Name', validators=[DataRequired()])
    item_cost_price = FloatField('Cost Price', validators=[DataRequired()])
    item_selling_price = FloatField('Selling Price', validators=[DataRequired()])
    submit = SubmitField('Add Item')


class StoreStockInForm(FlaskForm):
    item_name = SearchField('Search Item Name', validators=[DataRequired()])
    item_quantity = IntegerField('Quantity Received', validators=[DataRequired()])
    new_price = FloatField('New Price', validators=[DataRequired()])
    submit = SubmitField('Receive Stock')


class StoreStockOutForm(FlaskForm):
    item_name = SearchField('Search Item Name', validators=[DataRequired()])
    item_quantity = IntegerField('Quantity Sending', validators=[DataRequired()])
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
    name = StringField('Name', validators=[DataRequired()])
    company_name = StringField('Company Name', validators=[DataRequired()])
    phone_number = StringField('Phone Number', validators=[DataRequired()])
    amount_paid = IntegerField('Amount Paid', validators=[Optional()])
    submit = SubmitField('Save')


class UpdateDebtorForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    company_name = StringField('Company Name', validators=[DataRequired(), Length(min=4)])
    phone_number = StringField('Phone Number', validators=[DataRequired()])
    amount_paid = IntegerField('Amount Paid', validators=[Optional()])
    payment_method = SelectField('Payment Method', choices=[])
    submit = SubmitField('Save')

    def populate_account_choices(self):
        self.payment_method.choices = [account.account_name for account in Account.query.all()]


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


class PaymentForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    phone_number = IntegerField('Phone Number', validators=[DataRequired()])
    amount = IntegerField('Amount', validators=[Optional()])
    account = SelectField('Choose Account', choices=[])
    submit = SubmitField('Save')

    def populate_account_choices(self):
        self.account.choices = [account.account_name for account in Account.query.filter(Account.balance > 0).all()]

    def get_selected_account_name(self):
        selected_account = self.account.data
        if selected_account is not None:
            return selected_account
        else:
            return None


class TransferStockForm(FlaskForm):
    item_name = SearchField('Search Item Name', validators=[DataRequired()])
    item_quantity = IntegerField('Transfer Quantity', validators=[DataRequired()])
    shop = SelectField('Select Shop', choices=[])
    submit = SubmitField('Transfer Stock')

    def populate_shop_choices(self):
        self.shop.choices = [(shop.id, shop.shop_name) for shop in Shop.query.all()]

    def get_selected_shop_id(self):
        selected_shop_id = self.shop.data
        if selected_shop_id is not None:
            return int(selected_shop_id)
        else:
            return 0


class StockFromShopForm(FlaskForm):
    item_name = SearchField('Search Item Name', validators=[DataRequired()])
    item_quantity = IntegerField('Quantity Received', validators=[DataRequired()])
    submit = SubmitField('Receive Stock')


class UpdateAccountForm(FlaskForm):
    account_name = StringField('Account Name', validators=[DataRequired()])
    balance = FloatField('Account Balance', validators=[DataRequired()])
    submit = SubmitField('Add')


class UpdateStoreStockOutForm(FlaskForm):
    item_name = StringField('Item Name', validators=[DataRequired()])
    item_quantity = IntegerField('Quantity', validators=[DataRequired()])
    shop = SelectField('Shop', coerce=int)
    submit = SubmitField('Submit')

    def populate_shop_choices(self):
        shops = Shop.query.all()
        self.shop.choices = [(shop.id, shop.shop_name) for shop in shops]

    def get_selected_shop_id(self):
        return self.shop.data


class UpdateTransferStockForm(FlaskForm):
    item_name = SearchField('Item Name', validators=[DataRequired()])
    item_quantity = IntegerField('Transfer Quantity', validators=[DataRequired()])
    shop = SelectField('Select Shop', coerce=int)
    submit = SubmitField('Transfer Stock')

    def populate_shop_choices(self):
        self.shop.choices = [(shop.id, shop.shop_name) for shop in Shop.query.all()]

    def get_selected_shop_id(self):
        return self.shop.data


class UpdateStoreStockForm(FlaskForm):
    item_name = SearchField('Search Item Name', validators=[DataRequired()])
    item_quantity = IntegerField('Quantity Received', validators=[DataRequired()])
    submit = SubmitField('Update Changes')


class UpdateDailyCountForm(FlaskForm):
    item_name = StringField('Item Name', validators=[DataRequired()])
    count = IntegerField('Item Count', validators=[DataRequired()])
    submit = SubmitField('Update Count')


class ExpenseForm(FlaskForm):
    account = SelectField('Choose Account', choices=[])
    amount = FloatField('Amount', validators=[Optional()])
    description = TextAreaField('Expense Description', validators=[DataRequired()])
    submit = SubmitField('Pay')

    def populate_account_choices(self):
        self.account.choices = [account.account_name for account in Account.query.filter(Account.balance > 0).all()]

    def get_selected_account_name(self):
        selected_account = self.account.data
        if selected_account is not None:
            return selected_account
        else:
            return None


class StoreStockTransferForm(FlaskForm):
    item_name = SearchField('Search Item Name', validators=[DataRequired()])
    item_quantity = IntegerField('Transfer Quantity', validators=[DataRequired()])
    store = SelectField('Select Store', choices=[])
    submit = SubmitField('Transfer Stock')

    def populate_store_choices(self):
        self.store.choices = [(store.id, store.store_name) for store in Store.query.all()]

    def get_selected_store_id(self):
        selected_store_id = self.store.data
        if selected_store_id is not None:
            return int(selected_store_id)
        else:
            return 0
