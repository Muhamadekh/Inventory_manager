from inventory import db, login_manager, app
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    user_role = db.Column(db.String(30), nullable=False)
    shops = db.relationship('Shop', backref='shops', lazy=True)


class Shop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    stock = db.relationship('Stock', backref='shop', lazy=True)


class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_price = db.Column(db.Integer, nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    stock_status = db.Column(db.String(20), nullable=False, default='In Stock')
    shop_id = db.Column(db.String(100), db.ForeignKey('shop.id'))


