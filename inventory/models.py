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
    restock = db.relationship('Restock', backref='shop', lazy=True)
    sale = db.relationship('Sale', backref='shop', lazy=True)
    stock_in = db.relationship('StockOut', backref='shop', lazy=True)
    daily_count = db.relationship('DailyCount', backref='shop', lazy=True)
    stock_association = db.relationship('ShopStock', back_populates='shop')
    stocks = association_proxy("stock_association", "stock")


class ShopStock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column('shop_id', db.Integer, db.ForeignKey('shop.id'))
    stock_id = db.Column('stock_id', db.Integer, db.ForeignKey('stock.id'))

    shop = db.relationship('Shop', back_populates='stock_association')
    stock = db.relationship('Stock', back_populates='shops')


class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    item_price = db.Column(db.Integer, nullable=False)
    stock_status = db.Column(db.String(20), nullable=False, default='In Stock')
    date_added = db.Column(db.DateTime, default=datetime.now())
    item_value = db.Column(db.Integer, nullable=False)
    daily_count = db.relationship('DailyCount', backref='stock', lazy=True)
    shops = db.relationship('ShopStock', back_populates='stock')


stock_restock = db.Table('stock_restock',
    db.Column('restock_id', db.Integer, db.ForeignKey('restock.id')),
    db.Column('stock_received_id', db.Integer, db.ForeignKey('stock_received.id'))
)


class Restock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    restock_value = db.Column(db.Integer, nullable=False)
    date_received = db.Column(db.DateTime, default=datetime.now())
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    restock_items = db.relationship('StockReceived', secondary=stock_restock, backref='restock_group')


class StockReceived(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)


# stock_sale = db.Table('stock_sale',
#     db.Column('sale_id', db.Integer, db.ForeignKey('sale.id')),
#     db.Column('stock_sold_id', db.Integer, db.ForeignKey('stock_sold.id'))
# )


class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sales_value = db.Column(db.Integer, nullable=False)
    sales_discount = db.Column(db.Integer, nullable=False)
    payment_method = db.Column(db.String(80), nullable=False)
    transaction_id = db.Column(db.String(60))
    date_sold = db.Column(db.DateTime, default=datetime.now())
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    debtor_id = db.Column(db.Integer, db.ForeignKey('debtor.id'))
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
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'))


class StockOut(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    date_sent = db.Column(db.DateTime, default=datetime.now())
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'))


class StoreStock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_cost_price = db.Column(db.Integer, nullable=False)
    item_selling_price = db.Column(db.Integer, nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    stock_status = db.Column(db.String(20), nullable=False, default='In Stock')
    date_added = db.Column(db.DateTime, default=datetime.now())
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'))
    item_value = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('item_name', 'store_id'),
    )


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
    phone_number = db.Column(db.String(80), nullable=False, unique=True)
    amount_paid = db.Column(db.Integer, nullable=False)
    unpaid_amount = db.Column(db.Integer, nullable=False)
    purchases = db.relationship('Sale', backref='debtor', lazy=True)


class DailyCount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'))
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))