from inventory import db, login_manager, app
from flask_login import UserMixin
from datetime import datetime


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    user_role = db.Column(db.String(30), nullable=False)
    date_registered = db.Column(db.DateTime, default=datetime.now())
    shops = db.relationship('Shop', backref='staff', lazy=True)
    stores = db.relationship('Store', backref='staff', lazy=True)


class Shop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_name = db.Column(db.String(100), nullable=False, unique=True)
    location = db.Column(db.String(100), nullable=False)
    shopkeeper = db.Column(db.String(100), nullable=False)
    date_registered = db.Column(db.DateTime, default=datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    stock = db.relationship('Stock', backref='shop', lazy=True)
    stock_received = db.relationship('StockReceived', backref='shop', lazy=True)
    stock_sold = db.relationship('StockSold', backref='shop', lazy=True)
    stock_in = db.relationship('StockOut', backref='shop', lazy=True)


class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False, unique=True)
    item_quantity = db.Column(db.Integer, nullable=False)
    stock_status = db.Column(db.String(20), nullable=False, default='In Stock')
    date_added = db.Column(db.DateTime, default=datetime.now())
    shop_id = db.Column(db.String(100), db.ForeignKey('shop.id'))
    item_value = db.Column(db.Integer, nullable=False)


class StockReceived(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    date_received = db.Column(db.DateTime, default=datetime.now())
    shop_id = db.Column(db.String(100), db.ForeignKey('shop.id'))


class StockSold(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    item_discount = db.Column(db.Integer, nullable=False)
    item_value = db.Column(db.Integer, nullable=False)
    date_sold = db.Column(db.DateTime, default=datetime.now())
    payment_method = db.Column(db.String(80), nullable=False)
    shop_id = db.Column(db.String(100), db.ForeignKey('shop.id'))


class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_name = db.Column(db.String(60), nullable=False, unique=True)
    location = db.Column(db.String(60), nullable=False)
    date_registered = db.Column(db.DateTime, default=datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    store_stock = db.relationship('StoreStock', backref='store', lazy=True)
    stock_in = db.relationship('StockIn', backref='store', lazy=True)
    stock_out = db.relationship('StockOut', backref='store', lazy=True)


class StockIn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    date_received = db.Column(db.DateTime, default=datetime.now())
    item_cost_price = db.Column(db.Integer, nullable=False)
    item_selling_price = db.Column(db.Integer, nullable=False)
    store_id = db.Column(db.String(100), db.ForeignKey('store.id'))


class StockOut(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    date_sent = db.Column(db.DateTime, default=datetime.now())
    shop_id = db.Column(db.String(100), db.ForeignKey('shop.id'))
    store_id = db.Column(db.String(100), db.ForeignKey('store.id'))


class StoreStock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False, unique=True)
    item_cost_price = db.Column(db.Integer, nullable=False)
    item_selling_price = db.Column(db.Integer, nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    stock_status = db.Column(db.String(20), nullable=False, default='In Stock')
    date_added = db.Column(db.DateTime, default=datetime.now())
    store_id = db.Column(db.String(100), db.ForeignKey('store.id'))
    item_value = db.Column(db.Integer, nullable=False)


class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(80), nullable=False)
    item_supplied = db.Column(db.String(80), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    supply_date = db.Column(db.DateTime, default=datetime.now())


class Debtor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    company_name = db.Column(db.String(80), nullable=False)
    phone_number = db.Column(db.String(80), nullable=False)
    item_bought = db.Column(db.String(80), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    purchase_date = db.Column(db.DateTime, default=datetime.now())
