from inventory import db, login_manager
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy.ext.associationproxy import association_proxy


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    user_role = db.Column(db.String(30), nullable=False)
    date_registered = db.Column(db.DateTime, default=datetime.now)
    shops = db.relationship('Shop', backref='staff', lazy=True)
    stores = db.relationship('Store', backref='staff', lazy=True)
    shopkeepers = db.relationship('Shopkeeper', backref='user_details', lazy=True)


class Shop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_name = db.Column(db.String(100), nullable=False, unique=True)
    location = db.Column(db.String(100), nullable=False)
    date_registered = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    sale = db.relationship('Sale', backref='shop', lazy=True)
    stock_received = db.relationship('StockReceived', backref='shop', lazy=True)
    stock_in = db.relationship('StockOut', backref='shop', lazy=True)
    item_association = db.relationship('ShopItem', back_populates='shop')
    items = association_proxy("item_association", "item")
    shopkeepers = db.relationship('Shopkeeper', backref='shop_details', lazy=True)
    daily_shop_count = db.relationship('DailyCount', backref='shop', lazy=True)


class ShopItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column('shop_id', db.Integer, db.ForeignKey('shop.id'))
    item_id = db.Column('item_id', db.Integer, db.ForeignKey('item.id'))
    item_quantity = db.Column(db.Integer, nullable=False)
    item_value = db.Column(db.Integer, nullable=False)
    item_status = db.Column(db.String(20), nullable=False, default='In Stock')
    date_added = db.Column(db.DateTime, default=datetime.now)
    daily_count = db.relationship('DailyCount', backref='daily_count_item', lazy=True)

    shop = db.relationship('Shop', back_populates='item_association')
    item = db.relationship('Item', back_populates='shops')


class StockReceived(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    date_received = db.Column(db.DateTime, default=datetime.now)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))


class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sales_value = db.Column(db.Integer, nullable=False)
    sales_discount = db.Column(db.Integer, nullable=False)
    payment_method = db.Column(db.String(80), nullable=False)
    transaction_id = db.Column(db.String(60))
    date_sold = db.Column(db.DateTime, default=datetime.now)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    debtor_id = db.Column(db.Integer, db.ForeignKey('debtor.id'))
    credit_option = db.Column(db.Boolean)
    amount_paid = db.Column(db.Integer)
    sale_items = db.relationship('StockSold', backref='sale_group', lazy=True)


class StockSold(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    item_discount = db.Column(db.Integer, nullable=False)
    item_value = db.Column(db.Integer, nullable=False)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'))


class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_name = db.Column(db.String(60), nullable=False, unique=True)
    location = db.Column(db.String(60), nullable=False)
    date_registered = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    stock_in = db.relationship('StockIn', backref='store', lazy=True)
    stock_out = db.relationship('StockOut', backref='store', lazy=True)
    item_association = db.relationship('StoreItem', back_populates='store')
    items = association_proxy("item_association", "item")


class StoreItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column('store_id', db.Integer, db.ForeignKey('store.id'))
    item_id = db.Column('item_id', db.Integer, db.ForeignKey('item.id'))
    item_quantity = db.Column(db.Integer, nullable=False)
    item_value = db.Column(db.Integer, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.now)
    stock_status = db.Column(db.String(20), nullable=False, default='In Stock')

    store = db.relationship('Store', back_populates='item_association')
    item = db.relationship('Item', back_populates='stores')


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_cost_price = db.Column(db.Integer, nullable=False)
    item_selling_price = db.Column(db.Integer, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.now)
    stores = db.relationship('StoreItem', back_populates='item')
    shops = db.relationship('ShopItem', back_populates='item')


class StockIn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    date_received = db.Column(db.DateTime, default=datetime.now)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'))


class StockOut(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    date_sent = db.Column(db.DateTime, default=datetime.now)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'))
    is_received = db.Column(db.Boolean, nullable=False, default=False)


class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(80), nullable=False)
    phone_number = db.Column(db.String(80), nullable=False, unique=True)
    amount_paid = db.Column(db.Integer, nullable=False)
    unpaid_amount = db.Column(db.Integer, nullable=False)
    supply_date = db.Column(db.DateTime, default=datetime.now)


class Debtor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    company_name = db.Column(db.String(80), nullable=False)
    phone_number = db.Column(db.String(80), nullable=False, unique=True)
    amount_paid = db.Column(db.Integer, nullable=False)
    unpaid_amount = db.Column(db.Integer, nullable=False)
    purchases = db.relationship('Sale', backref='debtor', lazy=True)


class Shopkeeper(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class DailyCount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_item_id = db.Column(db.Integer, db.ForeignKey('shop_item.id'))
    count = db.Column(db.Integer, nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    date = db.Column(db.DateTime, default=datetime.now)


class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(50), unique=True, nullable=False)
    balance = db.Column(db.Float, default=0.0)
    movements_from = db.relationship('AccountMovement', foreign_keys='AccountMovement.transfer_from_id',
                                     backref='transfer_from', lazy=True)
    movements_to = db.relationship('AccountMovement', foreign_keys='AccountMovement.transfer_to_id',
                                   backref='transfer_to', lazy=True)
    balance_logs = db.relationship('AccountBalanceLog', backref='account', lazy=True)


class AccountMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    transfer_from_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    transfer_to_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)


class AccountBalanceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)
    balance = db.Column(db.Float, nullable=False)


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(50))
    amount = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)
