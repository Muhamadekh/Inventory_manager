from flask import Flask, render_template, url_for, flash, redirect, session, request, abort
from inventory import app, bcrypt, db
from inventory.models import User, Shop, Stock
from inventory.forms import (UserRegistrationForm, ShopRegistrationForm, LoginForm, ShopNewSTockForm)
from flask_login import current_user, login_user, logout_user, login_required
from datetime import datetime


@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    date_today = datetime.today().strftime('%d-%m-%Y')
    return render_template('home.html', date_today=date_today)


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
            return redirect(url_for('view_shop'))
    return render_template('register_shop.html', form=form)


@app.route('/view_shops', methods=['GET'])
def view_shop():
    shops = Shop.query.all()
    date_today = datetime.today().strftime('%d-%m-%Y')
    total_shop_stock_value = {}
    for shop in shops:
        stock_value_list = []
        for product in shop.stock:
            stock_value_list.append(product.item_value)
        total_stock_value = sum(stock_value_list)
        total_shop_stock_value[shop.id] = total_stock_value
    return render_template('view_shops.html', shops=shops, date_today=date_today,
                           total_shop_stock_value=total_shop_stock_value)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    else:
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user:
                # and bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                if user.user_role == 'Admin':
                    # next_page = request.args.get("next")
                    return redirect(url_for('home'))
                else:
                    return redirect(url_for('shop'))
            else:
                flash('Please check your username and password.')
        return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/shop', methods=['GET','POST'])
def shop():
    shop = Shop.query.filter_by(shopkeeper=current_user.id).first()
    if shop:
        return render_template('shop.html', shop=shop)
    else:
        return "This user has no shop assigned"


@app.route('/add_new_stock', methods=['GET', 'POST'])
@login_required
def add_new_stock():
    shop = Shop.query.filter_by(shopkeeper=current_user.id).first()
    shop_id = shop.id
    form = ShopNewSTockForm()
    if form.validate_on_submit():
        stock = Stock(item_name=form.item_name.data, item_price=form.item_price.data,
                      item_quantity=form.item_quantity.data, shop_id=shop_id)
        if stock.item_quantity <= 20:
            stock.stock_status = "Attention Needed"
        stock.item_value = stock.item_price * stock.item_quantity
        print(stock.item_value)
        db.session.add(stock)
        db.session.commit()
        return redirect(url_for('shop'))
    else:
        flash("Please check the product details.")
    return render_template('add_stock.html', form=form)