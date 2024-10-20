from inventory import db, login_manager
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy.ext.associationproxy import association_proxy


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Users Model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    user_role = db.Column(db.String(30), nullable=False)
    date_registered = db.Column(db.DateTime, default=datetime.now)
    shops = db.relationship('Shop', backref='staff', lazy=True)
    stores = db.relationship('Store', backref='staff', lazy=True)
    shopkeepers = db.relationship('Shopkeeper', backref='user_details', lazy=True)
    stock_selected = db.relationship('StockSold', backref='seller_details', lazy=True)
    sale = db.relationship('Sale', backref='seller_details', lazy=True)


# Shop Model
class Shop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_name = db.Column(db.String(100), nullable=False, unique=True)
    location = db.Column(db.String(100), nullable=False)
    date_registered = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    sale = db.relationship('Sale', backref='shop', lazy=True)
    stock_received = db.relationship('StockReceived', backref='shop', lazy=True)
    stock_sold = db.relationship('StockSold', backref='shop', lazy=True)
    stock_in = db.relationship('StockOut', backref='shop', lazy=True)
    item_association = db.relationship('ShopItem', back_populates='shop')
    items = association_proxy("item_association", "item")
    shopkeepers = db.relationship('Shopkeeper', backref='shop_details', lazy=True)
    daily_shop_count = db.relationship('DailyCount', backref='shop', lazy=True)
    movements_from = db.relationship('TransferStock', foreign_keys='TransferStock.transfer_from_id',
                                     backref='transfer_from', lazy=True)
    movements_to = db.relationship('TransferStock', foreign_keys='TransferStock.transfer_to_id',
                                   backref='transfer_to', lazy=True)
    count_difference = db.relationship('CountDifference', backref='difference_item', lazy=True)


# Model for shop items
class ShopItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column('shop_id', db.Integer, db.ForeignKey('shop.id'))
    item_id = db.Column('item_id', db.Integer, db.ForeignKey('item.id'))
    item_quantity = db.Column(db.Integer, nullable=False)
    item_value = db.Column(db.Integer, nullable=False)
    item_status = db.Column(db.String(20), nullable=False, default='In Stock')
    date_added = db.Column(db.DateTime, default=datetime.now)
    daily_count = db.relationship('DailyCount', backref='daily_count_item', lazy=True)
    count_difference = db.relationship('CountDifference', backref='shop_item', lazy=True)

    shop = db.relationship('Shop', back_populates='item_association')
    item = db.relationship('Item', back_populates='shops')


# Model for items received in a shop
class StockReceived(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    date_received = db.Column(db.DateTime, default=datetime.now)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))


# Model for items transfer between shops
class TransferStock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    date_sent = db.Column(db.DateTime, default=datetime.now)
    transfer_from_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    transfer_to_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    is_received = db.Column(db.Boolean, nullable=False, default=False)


# Model for sales in shops
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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


# Model for items added to cart
class StockSold(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    item_discount = db.Column(db.Integer, nullable=False)
    item_value = db.Column(db.Integer, nullable=False)
    item_cost_price = db.Column(db.Float, nullable=False)
    item_selling_price = db.Column(db.Float, nullable=False)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'))
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


# Model for store
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
    movements_from = db.relationship('StoreStockTransfer', foreign_keys='StoreStockTransfer.transfer_from_id',
                                     backref='transfer_from', lazy=True)
    movements_to = db.relationship('StoreStockTransfer', foreign_keys='StoreStockTransfer.transfer_to_id',
                                   backref='transfer_to', lazy=True)


# Model for items in a store
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


# Model for items
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_cost_price = db.Column(db.Float, nullable=False)
    item_selling_price = db.Column(db.Float, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.now)
    stores = db.relationship('StoreItem', back_populates='item')
    shops = db.relationship('ShopItem', back_populates='item')


# Model for items received in a store
class StockIn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    date_received = db.Column(db.DateTime, default=datetime.now)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'))


# Model for stock sent from a store to a shop
class StockOut(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    date_sent = db.Column(db.DateTime, default=datetime.now)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'))
    is_received = db.Column(db.Boolean, nullable=False, default=False)


# Model for debtors
class Debtor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    company_name = db.Column(db.String(80), nullable=False)
    phone_number = db.Column(db.String(80), nullable=False, unique=True)
    amount_paid = db.Column(db.Integer, nullable=False)
    unpaid_amount = db.Column(db.Integer, nullable=False)
    account_symbol = db.Column(db.String(20), nullable=False, default='GNF')
    purchases = db.relationship('Sale', backref='debtor', lazy=True)


# Model for shopkeepers
class Shopkeeper(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_assigned = db.Column(db.DateTime, default=datetime.now)


# Model for physical count items submitted from shops
class DailyCount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_item_id = db.Column(db.Integer, db.ForeignKey('shop_item.id'))
    count = db.Column(db.Integer, nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    base_count = db.Column(db.Integer)  # Quantity of the item as per the system at the time of sending the daily count
    date = db.Column(db.DateTime, default=datetime.now)


# Model for accounts used for payment
class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(50), unique=True, nullable=False)
    balance = db.Column(db.Float, default=0.0)
    movements_from = db.relationship('AccountMovement', foreign_keys='AccountMovement.transfer_from_id',
                                     backref='transfer_from', lazy=True)
    movements_to = db.relationship('AccountMovement', foreign_keys='AccountMovement.transfer_to_id',
                                   backref='transfer_to', lazy=True)
    balance_logs = db.relationship('AccountBalanceLog', backref='account', lazy=True)


# Model for movement of money between accounts
class AccountMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    rate = db.Column(db.Float)  # dollar against shilling rate
    transfer_from_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    transfer_to_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)


# Model to keep track of daily account balance
class AccountBalanceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)
    balance = db.Column(db.Float, nullable=False)


# Model for payments made to people
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(50))
    amount = db.Column(db.Integer, nullable=False)
    account = db.Column(db.String(40))
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)


# Model for item differences in daily count submitted by shops. if an item count sent by a shopkeeper is less than
# or more than the item count in the system, an admin must harmonize the count. This model will keep track of the count
# differences
class CountDifference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    shop_item_id = db.Column(db.Integer, db.ForeignKey('shop_item.id'))
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    date = db.Column(db.DateTime, default=datetime.now)


class TrashLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    item_cost_price = db.Column(db.Float, nullable=False)
    item_selling_price = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.now)


class PriceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_cost_price = db.Column(db.Float, nullable=False)
    item_selling_price = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.now)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account = db.Column(db.String(40), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(140), nullable=False)
    date = db.Column(db.DateTime, default=datetime.now)


# Model for transferring stock from one store to another
class StoreStockTransfer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    date_sent = db.Column(db.DateTime, default=datetime.now)
    transfer_from_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    transfer_to_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    is_received = db.Column(db.Boolean, nullable=False, default=False)
