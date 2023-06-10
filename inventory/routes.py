from flask import Flask, render_template, url_for, flash, redirect, session, request, abort
from inventory import app, bcrypt, db
from inventory.models import User, Shop, Stock, StockReceived, StockSold
from inventory.forms import (UserRegistrationForm, ShopRegistrationForm, LoginForm, ShopNewItemForm,
                             ShopStockReceivedForm, ShopStockSoldForm)
from flask_login import current_user, login_user, logout_user, login_required
from datetime import datetime
from sqlalchemy import func


def today_date():
    date_today = datetime.today().strftime('%d-%m-%Y')
    return date_today


@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    date = today_date()
    return render_template('home.html', date=date)


@app.route('/register_user', methods=['GET', 'POST'])
def register_user():
    form = UserRegistrationForm()
    user = User.query.filter_by(username=form.username.data).first()
    if user:
        flash("A user with this username exist. Try another name", "warning")
    else:
        if form.validate_on_submit():
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user = User(username=form.username.data, password=hashed_password, user_role=form.user_role.data)
            db.session.add(user)
            db.session.commit()
            flash(f"{user.username} was registered successfully")
            return redirect(url_for('view_users'))
    return render_template('register_user.html', form=form)


@app.route('/view_users', methods=['GET'])
def view_users():
    users = User.query.all()
    return render_template('view_users.html', users=users)


@app.route('/register_shop', methods=['GET', 'POST'])
def register_shop():
    form = ShopRegistrationForm()
    shop = Shop.query.filter_by(shop_name=form.shop_name.data).first()
    if shop:
        flash("This already exist. Try another name", "warning")
    else:
        form.populate_shopkeeper_choices()
        selected_staff_id = form.get_selected_shopkeeper_id()
        if form.validate_on_submit():
            shop = Shop(shop_name=form.shop_name.data, location=form.location.data, user_id=selected_staff_id,
                        shopkeeper=form.shopkeeper.data)
            db.session.add(shop)
            db.session.commit()
            flash(f"{shop.shop_name} at {shop.location} was successfully registered.")
            return redirect(url_for('view_shops'))
    return render_template('register_shop.html', form=form)


@app.route('/view_shops', methods=['GET', 'POST'])
def view_shops():
    shops = Shop.query.all()
    date = today_date()
    shop_stock_lookup = {}
    for shop in shops:
        stock_value_list = []
        for product in shop.stock:
            stock_value_list.append(product.item_value)
        total_stock_value = sum(stock_value_list)
        shop_stock_lookup[shop.id] = total_stock_value
    return render_template('view_shops.html', shop_stock_lookup=shop_stock_lookup, shops=shops, date=date)


@app.route('/view_shops/<int:shop_id>', methods=['GET'])
def view_shop(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    date = today_date()
    stock_value_list = []
    for product in shop.stock:
        stock_value_list.append(product.item_value)
    total_stock_value = sum(stock_value_list)
    return render_template('view_shop.html', shop=shop, total_stock_value=total_stock_value, date=date)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated and current_user.user_role == 'Admin':
        return redirect(url_for('home'))
    elif current_user.is_authenticated and current_user.user_role != 'Admin':
        return redirect(url_for('shop'))
    else:
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            print(user.password, form.password.data)
            if user and bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                if user.user_role == 'Admin':
                    return redirect(url_for('home'))
                else:
                    return redirect(url_for('stock_sold'))
            else:
                flash('Please check your username and password.', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/stock', methods=['GET','POST'])
def stock():
    shop = Shop.query.filter_by(shopkeeper=current_user.id).first()
    if shop:
        return render_template('stock.html', shop=shop)
    else:
        return "This user has no shop assigned"


@app.route('/add_new_stock', methods=['GET', 'POST'])
@login_required
def add_new_stock():
    shop = Shop.query.filter_by(shopkeeper=current_user.id).first()
    if current_user.user_role == 'Admin':
        shop_id = [shop.id for shop in Shop.query.all()]
    else:
        shop_id = shop.id
    form = ShopNewItemForm()
    if form.validate_on_submit():
        stock = Stock(item_name=form.item_name.data, item_price=form.item_price.data,
                      item_quantity=form.item_quantity.data, shop_id=shop.id)
        if stock.item_quantity <= 20:
            stock.stock_status = "Running Out"
        stock.item_value = stock.item_price * stock.item_quantity
        print(stock.item_value)
        db.session.add(stock)
        db.session.commit()
        if current_user.user_role == 'Admin':
            return redirect(url_for('view_shop', shop_id=shop.id))
        else:
            return redirect(url_for('stock_sold'))
    return render_template('add_stock.html', form=form)


@app.route('/stock_received', methods=['GET', 'POST'])
def stock_received():
    form = ShopStockReceivedForm()
    form.populate_item_name_choices()
    selected_item_id = form.get_selected_item_id()
    item = Stock.query.filter_by(id=selected_item_id).first()
    if form.validate_on_submit():
        item_received = StockReceived(item_name=item.item_name, item_quantity=form.item_quantity.data)
        db.session.add(item_received)
        db.session.commit()
        if item.item_name == item_received.item_name:
            item.item_quantity = item.item_quantity + item_received.item_quantity
            item.item_value = item.item_quantity * item.item_price
            db.session.commit()
        if current_user.user_role == 'Admin':
            return redirect(url_for('view_shop', shop_id=item.shop.id))
        return redirect(url_for('stock_sold'))
    return render_template('stock_received.html', form=form)


@app.route('/shop', methods=['GET', 'POST'])
def stock_sold():
    shop = Shop.query.filter_by(shopkeeper=current_user.id).first()
    form = ShopStockSoldForm()
    form.populate_item_name_choices()
    selected_item_id = form.get_selected_item_id()
    item = Stock.query.filter_by(id=selected_item_id).first()
    if form.validate_on_submit():
        item_sold = StockSold(item_name=item.item_name, item_quantity=form.item_quantity.data,
                              item_discount=form.item_discount.data, item_price=item.item_price)
        selling_price = item_sold.item_price - item_sold.item_discount
        item_sold.item_value = item_sold.item_quantity * selling_price
        db.session.add(item_sold)
        db.session.commit()
        if item.item_name == item_sold.item_name:
            item.item_quantity = item.item_quantity - item_sold.item_quantity
            item.item_value = item.item_quantity * item.item_price
            db.session.commit()
        return redirect(url_for('stock_sold'))

    sales_dates = []
    sales_lookup = {}

    date = today_date()
    current_date = datetime.utcnow()
    sales_entries = StockSold.query.filter(StockSold.date_sold<=current_date).order_by(StockSold.date_sold.desc()).all()
    for entry in sales_entries:
        entry_date = entry.date_sold.date()
        if entry_date not in sales_dates:
            sales_dates.append(entry_date)
    for date in sales_dates:
        sales_lookup[date] = []
        sales = StockSold.query.filter(func.date(StockSold.date_sold) == date).all()
        for sale in sales:
            sales_lookup[date].append(sale)
    return render_template('stock_sold.html', form=form, sales_lookup=sales_lookup, date=date, shop=shop, sales_dates=sales_dates)


