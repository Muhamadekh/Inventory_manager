from flask import Flask, render_template, url_for, flash, redirect, session, request, abort
from inventory import app, bcrypt, db
from inventory.models import User, Shop, Stock, StockReceived, StockSold, Debtor, Store, StoreStock, StockOut, StockIn
from inventory.forms import (UserRegistrationForm, ShopRegistrationForm, LoginForm, ShopNewItemForm,
                             ShopStockReceivedForm, ShopStockSoldForm, DebtorRegistrationForm, StoreRegistrationForm,
                             StoreNewItemForm, StoreStockInForm, StoreStockOutForm)
from flask_login import current_user, login_user, logout_user, login_required
from datetime import datetime, timedelta
from sqlalchemy import func
import csv
from flask import make_response
import io
import itertools
from sqlalchemy.exc import IntegrityError


def today_date():
    date_today = datetime.today().strftime('%d-%m-%Y')
    return date_today


@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    current_date = datetime.now().date()
    # Finding total shops stck value
    shops = Shop.query.all()
    stock_value_list = []
    for shop in shops:
        shop_stock_value_list = []
        for item in shop.stock:
            shop_stock_value_list.append(item.item_value)
        stock_value_list.append(sum(shop_stock_value_list))
    total_stock_value = sum(stock_value_list)

    # Finding total store stck value
    store_stock = []
    stores = Store.query.all()
    for store in stores:
        for item in store.store_stock:
            store_stock.append(item.item_value)
    total_store_stock = sum(store_stock)

    # Finding total net sales and discount
    sales_value_list = []
    discount_list = []
    sales = StockSold.query.filter(func.date(StockSold.date_sold == current_date)).all()
    print(sales)
    for sale in sales:
        sales_value_list.append(sale.item_value)
        discount_list.append(sale.item_discount)
    total_sales_value = sum(sales_value_list)
    total_discount = sum(discount_list)

    # Finding total top 5 most sold items
    top_items_sold = StockSold.query.order_by(StockSold.item_quantity.desc()).all()
    top_items_sold_lookup = {}
    for item in top_items_sold:
        if item not in top_items_sold_lookup:
            top_items_sold_lookup[item.item_name] = item.item_quantity
        else:
            new_quantity = top_items_sold_lookup[item.item_name] + item.item_quantity
            top_items_sold_lookup[item.item_name] = new_quantity
    top_5_items_sold = dict(itertools.islice(top_items_sold_lookup.items(), 5))
    print(top_5_items_sold)

    return render_template('home.html', current_date=current_date, total_stock_value=total_stock_value, total_store_stock=total_store_stock,
                           total_sales_value=total_sales_value, total_discount=total_discount, top_5_items_sold=top_5_items_sold)


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
            flash(f"{user.username} was registered successfully", "success")
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
            flash(f"{shop.shop_name} at {shop.location} was successfully registered.", "success")
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

    # Request reports download
    if request.args.get('download'):
        time_range = request.args.get('time_range')  # Get the specified time range from the request arguments

        # Define the start date based on the specified time range
        if time_range == '7':  # 7 days
            start_date = datetime.now() - timedelta(days=7)
        elif time_range == '30':  # 30 days
            start_date = datetime.now() - timedelta(days=30)
        elif time_range == '6m':  # 6 months
            start_date = datetime.now() - timedelta(days=30 * 6)
        else:
            # Handle invalid time range here, e.g., redirect to an error page or display an error message
            flash("Range does not exist", "warning")

        # Get the sales entries within the specified time range
        sales_entries = StockSold.query.filter(StockSold.date_sold >= start_date,
                                               StockSold.shop_id == shop.id
                                               ).order_by(StockSold.date_sold.desc()).all()

        # Prepare the CSV file data
        headers = ['Date Sold', 'Item Name', 'Quantity', 'Discount', 'Value']
        rows = []
        for entry in sales_entries:
            row = [
                entry.date_sold.strftime('%d-%m-%Y'),
                entry.item_name,
                entry.item_quantity,
                entry.item_discount,
                entry.item_value
            ]
            rows.append(row)

        # Create a CSV file
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(rows)

        # Prepare the response with the CSV file
        filename = f"{shop.shop_name.replace(' ', '_')}_Sales.csv"
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        response.headers['Content-type'] = 'text/csv'
        return response
    return render_template('view_shop.html', shop=shop, total_stock_value=total_stock_value, date=date)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated and current_user.user_role == 'Admin':
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            if user.user_role == 'Admin':
                return redirect(url_for('home'))
            else:
                shop = Shop.query.filter_by(shopkeeper=current_user.id).first()
                return redirect(url_for('stock_sold', shop_id=shop.id))
        else:
            flash('Please check your username and password.', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/<int:shop_id>/add_new_stock', methods=['GET', 'POST'])
@login_required
def add_new_stock(shop_id):
    # shop = Shop.query.filter_by(shopkeeper=current_user.id).first()
    shop = Shop.query.get_or_404(shop_id)

    form = ShopNewItemForm()
    if form.validate_on_submit():
        stock = Stock(item_name=form.item_name.data, item_price=form.item_price.data,
                      item_quantity=form.item_quantity.data, shop_id=shop.id)
        if stock.item_quantity <= 20:
            stock.stock_status = "Running Out"
        stock.item_value = stock.item_price * stock.item_quantity
        try:
            db.session.add(stock)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('An error occurred while adding the item.', 'danger')
        if stock.item_selling_price < stock.item_cost_price:
            flash('Selling price is less than cost price.', 'warning')
        return redirect(url_for('add_new_stock', shop_id=shop.id))
    return render_template('add_stock.html', form=form, shop=shop)


@app.route('/<int:shop_id>/stock_received', methods=['GET', 'POST'])
def stock_received(shop_id):
    # shop = Shop.query.filter_by(shopkeeper=current_user.id).first()
    shop = Shop.query.get_or_404(shop_id)
    form = ShopStockReceivedForm()
    form.populate_item_name_choices()
    selected_item_id = form.get_selected_item_id()
    item = Stock.query.filter_by(id=selected_item_id).first()
    if form.validate_on_submit():
        item_received = StockReceived(item_name=item.item_name, item_quantity=form.item_quantity.data, shop_id=shop.id)
        db.session.add(item_received)
        db.session.commit()
        if item.item_name == item_received.item_name:
            item.item_quantity = item.item_quantity + item_received.item_quantity
            item.item_value = item.item_quantity * item.item_price
            db.session.commit()
        return redirect(url_for('stock_received', shop_id=shop.id))

    if request.args.get('download'):

        time_range = request.args.get('time_range')

        if time_range == '30':
            start_date = datetime.now() - timedelta(days=30)
        elif time_range == '6m':
            start_date = datetime.mow() - timedelta(days=30*6)
        else:
             flash("Range does not exit", "warning")

        sales_entries = StockReceived.query.filter(StockReceived.date_received >= start_date,
                                                   StockSold.shop_id == shop.id
                                                   ).order_by(StockReceived.date_received.desc()).all()

        headers = ['Date Received', 'Item Name', 'Quantity']
        rows = []
        for entry in sales_entries:
            row = [
                entry.date_received.strftime('%d-%m-%Y'),
                entry.item_name,
                entry.item_quantity
            ]
        rows.append(row)

        # Create a CSV file
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(rows)

        # Prepare the response with the CSV file
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=stock_received.csv'
        response.headers['Content-type'] = 'text/csv'
        return response
    return render_template('stock_received.html', form=form)


@app.route('/<int:shop_id>/shop', methods=['GET', 'POST'])
def stock_sold(shop_id):
    # shop = Shop.query.filter_by(shopkeeper=current_user.id).first()
    shop = Shop.query.get_or_404(shop_id)
    form = ShopStockSoldForm()
    form.populate_item_name_choices()
    selected_item_id = form.get_selected_item_id()
    item = Stock.query.filter_by(id=selected_item_id).first()
    if form.validate_on_submit():
        item_sold = StockSold(item_name=item.item_name, item_quantity=form.item_quantity.data,
                              item_discount=form.item_discount.data, payment_method=form.payment_method.data, shop_id=shop.id)
        selling_price = item.item_price - item_sold.item_discount
        item_sold.item_value = item_sold.item_quantity * selling_price
        db.session.add(item_sold)
        db.session.commit()
        if item.item_name == item_sold.item_name:
            item.item_quantity = item.item_quantity - item_sold.item_quantity
            item.item_value = item.item_quantity * item.item_price
            db.session.commit()
        if item_sold.payment_method == 'Credit':
            return redirect(url_for('debtor'))
        return redirect(url_for('stock_sold', shop_id=shop.id))

    sales_dates = []
    sales_lookup = {}

    Date = today_date()
    current_date = datetime.now()
    sales_entries = StockSold.query.filter(StockSold.date_sold <= current_date,
                                           StockSold.shop_id == shop.id
                                           ).order_by(StockSold.date_sold.desc()).all()
    for entry in sales_entries:
        entry_date = entry.date_sold.date()
        if entry_date not in sales_dates:
            sales_dates.append(entry_date)
    for date in sales_dates:
        sales_lookup[date] = []
        sales = StockSold.query.filter(func.date(StockSold.date_sold) == date, StockSold.shop_id == shop.id).all()
        for sale in sales:
            sales_lookup[date].append(sale)
    return render_template('stock_sold.html', form=form, sales_lookup=sales_lookup, Date=Date, shop=shop, sales_dates=sales_dates)


@app.route('/history', methods=['GET'])
def history():
    start_date = datetime.now() - timedelta(days=3)
    sales_entries = StockSold.query.filter(StockSold.date_sold >= start_date,
                                           StockSold.shop_id).order_by(StockSold.date_sold.desc()).all()
    sales_dates = []
    sales_lookup = {}
    for entry in sales_entries:
        entry_date = entry.date_sold.date()
        if entry_date not in sales_dates:
            sales_dates.append(entry_date)

    for date in sales_dates:
        sales_lookup[date] = []
        sales = StockSold.query.filter(func.date(StockSold.date_sold) == date).all()
        for sale in sales:
            sales_lookup[date].append(sale)
    return render_template('history.html', sales_dates=sales_dates, sales_lookup=sales_lookup)


@app.route('/add_debtor', methods=['GET', 'POST'])
def add_debtor():
    form = DebtorRegistrationForm()
    if form.validate_on_submit():
        debtor = Debtor(name=form.name.data, company_name=form.company_name.data, phone_number=form.phone_number.data)
        sale_time = datetime.now()
        item = StockSold.query.filter(StockSold.date_sold <= sale_time).order_by(StockSold.date_sold.desc()).first()
        debtor.item_bought = item.item_name
        debtor.item_quantity = item.item_quantity
        debtor.purchase_date = item.date_sold
        debtor.item_value = item.item_value
        db.session.add(debtor)
        db.session.commit()
        return redirect(url_for('stock_sold'))
    return render_template('add_debtor.html')


@app.route('/view_debtors', methods=['GET'])
def view_debtors():
    debtors = Debtor.query.all()
    return render_template('view_debtors.html', debtors=debtors)


@app.route('/register_store', methods=['GET', 'POST'])
def register_store():
    form = StoreRegistrationForm()
    if form.validate_on_submit():
        store = Store(store_name=form.store_name.data, location=form.location.data, user_id=current_user.id)
        db.session.add(store)
        db.session.commit()
        flash(f"{store.store_name} at {store.location} was successfully registered.", "success")
        return redirect(url_for('view_stores'))
    return render_template('register_store.html', form=form)


@app.route('/view_stores', methods=['GET', 'POST'])
def view_stores():
    stores = Store.query.all()
    date = today_date()
    store_stock_lookup = {}
    for store in stores:
        stock_value_list = []
        for product in store.store_stock:
            stock_value_list.append(product.item_value)
        total_stock_value = sum(stock_value_list)
        store_stock_lookup[store.id] = total_stock_value
    return render_template('view_stores.html', store_stock_lookup=store_stock_lookup, stores=stores, date=date)


@app.route('/view_stores/<int:store_id>', methods=['GET'])
def view_store(store_id):
    store = Store.query.get_or_404(store_id)
    date = today_date()
    stock_value_list = []
    for product in store.store_stock:
        stock_value_list.append(product.item_value)
    total_stock_value = sum(stock_value_list)
    return render_template('view_store.html', store=store, total_stock_value=total_stock_value, date=date)


@app.route('/view_stores/<int:store_id>/add_store_stock', methods=['GET', 'POST'])
@login_required
def add_store_stock(store_id):
    store = Store.query.get_or_404(store_id)
    form = StoreNewItemForm()
    if form.validate_on_submit():
        store_stock = StoreStock(item_name=form.item_name.data, item_cost_price=form.item_cost_price.data,
                                 item_selling_price=form.item_selling_price.data, item_quantity=form.item_quantity.data,
                                 store_id=store.id)
        if store_stock.item_quantity <= 20:
            store_stock.stock_status = "Running Out"
        store_stock.item_value = store_stock.item_selling_price * store_stock.item_quantity
        db.session.add(store_stock)
        db.session.commit()
        if store_stock.item_selling_price < store_stock.item_cost_price:
            flash('Selling price is less than cost price.', 'warning')
        return redirect(url_for('add_store_stock', store_id=store.id))
    return render_template('add_store_stock.html', form=form, store=store)


@app.route('/view_stores/<int:store_id>/stock_in', methods=['GET', 'POST'])
def stock_in(store_id):
    store = Store.query.get_or_404(store_id)
    form = StoreStockInForm()
    form.populate_item_name_choices()
    selected_item_id = form.get_selected_item_id()
    item = StoreStock.query.filter_by(id=selected_item_id).first()
    if form.validate_on_submit():
        item_received = StockIn(item_name=item.item_name, item_quantity=form.item_quantity.data, store_id=store.id,
                                item_cost_price=item.item_cost_price, item_selling_price=item.item_selling_price)
        db.session.add(item_received)
        db.session.commit()
        if item.item_name == item_received.item_name:
            item.item_quantity = item.item_quantity + item_received.item_quantity
            item.item_value = item.item_quantity * item.item_selling_price
            db.session.commit()
        return redirect(url_for('stock_in', store_id=store.id))
    return render_template('stock_in.html', form=form, store=store)


@app.route('/view_stores/<int:store_id>/stock_out', methods=['GET', 'POST'])
def stock_out(store_id):
    store = Store.query.get_or_404(store_id)
    form = StoreStockOutForm()
    form.populate_item_name_choices()
    form.populate_shop_choices()
    selected_item_id = form.get_selected_item_id()
    selected_shop_id = form.get_selected_shop_id()
    item = StoreStock.query.filter_by(id=selected_item_id).first()
    shop = Shop.query.filter_by(id=selected_shop_id).first()
    if form.validate_on_submit():
        stock_out = StockOut(item_name=item.item_name, item_quantity=form.item_quantity.data,
                             store_id=store.id, shop_id=shop.id)
        db.session.add(stock_out)
        db.session.commit()
        if item.item_name == stock_out.item_name:
            item.item_quantity = item.item_quantity - stock_out.item_quantity
            item.item_value = item.item_quantity * item.item_selling_price
            db.session.commit()
        return redirect(url_for('stock_out', store_id=store.id))

    stock_out_dates = []
    stock_out_lookup = {}

    current_date = datetime.now()
    sales_entries = StockOut.query.filter(StockOut.date_sent <= current_date,
                                          StockOut.store_id == store.id).order_by(StockOut.date_sent.desc()).all()
    for entry in sales_entries:
        entry_date = entry.date_sent.date()
        if entry_date not in stock_out_dates:
            stock_out_dates.append(entry_date)
    for date in stock_out_dates:
        stock_out_lookup[date] = []
        item_sent = StockOut.query.filter(func.date(StockOut.date_sent) == date).all()
        for item in item_sent:
            stock_out_lookup[date].append(item)
    return render_template('stock_out.html', form=form, stock_out_lookup=stock_out_lookup, shop=shop,
                           stock_out_dates=stock_out_dates, store=store)
