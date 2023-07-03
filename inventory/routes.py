from flask import render_template, url_for, flash, redirect, session, request, abort, jsonify
from inventory import app, bcrypt, db
from inventory.models import (User, Shop, Stock, StockReceived, StockSold, Debtor, Store, StoreStock, StockOut, Sale,
                              StockIn, DailyCount, ShopStock)
from inventory.forms import (UserRegistrationForm, ShopRegistrationForm, LoginForm, ShopNewItemForm,
                             ShopStockReceivedForm, ShopStockSoldForm, DebtorRegistrationForm, StoreRegistrationForm,
                             StoreNewItemForm, StoreStockInForm, StoreStockOutForm, DailyCountForm, SaleForm,
                             )
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
        for shop_stock in shop.stocks:
            item = shop_stock.stock
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
    sales = Sale.query.filter(func.date(Sale.date_sold == current_date)).all()
    for sale in sales:
        sales_value_list.append(sale.sales_value)
        discount_list.append(sale.sales_discount)
    total_sales_value = sum(sales_value_list)
    total_discount = sum(discount_list)

    # Finding total top 5 most sold items
    top_items_sold = StockSold.query.order_by(StockSold.item_quantity.desc(), StockSold.item_name).all()
    top_items_sold_lookup = {}
    for item in top_items_sold:
        if item.item_name not in top_items_sold_lookup:
            top_items_sold_lookup[item.item_name] = item.item_quantity
        else:
            new_quantity = top_items_sold_lookup[item.item_name] + item.item_quantity
            top_items_sold_lookup[item.item_name] = new_quantity
    sorted_top_items_sold_lookup = dict(sorted(top_items_sold_lookup.items(), key=lambda x:x[1], reverse=True))
    top_5_items_sold = dict(itertools.islice(sorted_top_items_sold_lookup.items(), 5))

    # Listing shop-based weekly sales
    shop_sales_lookup = {}
    time_range = datetime.now() - timedelta(days=7)

    for shop in shops:
        shop_sales_lookup[shop.shop_name] = []  # Initialize the list for each shop
        weekly_sales = Sale.query.filter(Sale.date_sold >= time_range).all()
        if weekly_sales:
            for sale in weekly_sales:
                if sale.shop_id == shop.id:  # Check if the sale belongs to the current shop
                    if shop.shop_name in shop_sales_lookup:
                        shop_sales_lookup[shop.shop_name].append(sum([item.item_quantity for item in sale.sale_items]))
                    else:
                        shop_sales_lookup[shop.shop_name] = sum([item.item_quantity for item in sale.sale_items])
    sorted_total_shop_sales_lookup = dict(sorted(shop_sales_lookup.items(), key=lambda x:x[1], reverse=True))

    return render_template('home.html', current_date=current_date, total_stock_value=total_stock_value, total_store_stock=total_store_stock,
                           total_sales_value=total_sales_value, total_discount=total_discount, top_5_items_sold=top_5_items_sold,
                           sorted_total_shop_sales_lookup=sorted_total_shop_sales_lookup)


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
            return redirect(url_for('login'))
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
        user = User.query.filter_by(id=selected_staff_id).first()
        if form.validate_on_submit():
            shop = Shop(shop_name=form.shop_name.data, location=form.location.data, user_id=current_user.id,
                        shopkeeper=user.username)
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
        for shop_stock in shop.stocks:
            product = shop_stock.stock
            stock_value_list.append(product.item_value)
        total_stock_value = sum(stock_value_list)
        shop_stock_lookup[shop.id] = total_stock_value
    return render_template('view_shops.html', shop_stock_lookup=shop_stock_lookup, shops=shops, date=date)


@app.route('/view_shops/<int:shop_id>', methods=['GET'])
def view_shop(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    date = today_date()
    stock_value_list = []
    for shop_stock in shop.stocks:
        product = shop_stock.stock
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
                shop = Shop.query.filter_by(shopkeeper=current_user.username).first()
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
                      item_quantity=form.item_quantity.data)
        shop_stock = ShopStock(shop=shop, stock=stock)
        if stock.item_quantity <= 20:
            stock.stock_status = "Running Out"
        stock.item_value = stock.item_price * stock.item_quantity
        try:
            db.session.add(stock)
            db.session.add(shop_stock)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('An error occurred while adding the item.', 'danger')
        return redirect(url_for('add_new_stock', shop_id=shop.id))
    return render_template('add_stock.html', form=form, shop=shop)


@app.route('/<int:shop_id>/stock_received', methods=['GET', 'POST'])
def stock_received(shop_id):
    # shop = Shop.query.filter_by(shopkeeper=current_user.id).first()
    shop = Shop.query.get_or_404(shop_id)
    form = ShopStockReceivedForm()
    # form.populate_item_name_choices()
    # selected_item_id = form.get_selected_item_id()
    # item = Stock.query.filter_by(id=selected_item_id).first()
    if form.validate_on_submit():
        item = Stock.query.filter_by(item_name=form.item_name.data).first()
        item_received = StockReceived(item_name=form.item_name.data, item_quantity=form.item_quantity.data, shop_id=shop.id)
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
    return render_template('stock_received.html', form=form, shop=shop)


@app.route('/get_item_name', methods=['GET', 'POST'])
def get_item_name():
    item_name = request.json["item_name"]
    shop_id = request.json["shop_id"]
    shop = Shop.query.get_or_404(shop_id)
    for shop_stock in shop.stocks:
        item = shop_stock.stock
        response = {
            "item_name": item.item_name
        }
    return jsonify(response)


@app.route('/<int:shop_id>/shop', methods=['GET', 'POST'])
def stock_sold(shop_id):
    # shop = Shop.query.filter_by(shopkeeper=current_user.id).first()
    shop = Shop.query.get_or_404(shop_id)
    selection_form = ShopStockSoldForm()
    sales_form = SaleForm()
    # selection_form.populate_item_name_choices()
    # selected_item_id = selection_form.get_selected_item_id()
    # item = Stock.query.filter_by(id=selected_item_id).first()

    if selection_form.validate_on_submit() and selection_form.submit.data:
        item = Stock.query.filter_by(item_name=selection_form.item_name.data).first()
        discount = selection_form.item_discount.data if selection_form.item_discount.data else 0
        item_sold = StockSold(item_name=selection_form.item_name.data, item_quantity=selection_form.item_quantity.data,
                              item_discount=discount)
        selling_price = item.item_price - discount
        item_sold.item_value = item_sold.item_quantity * selling_price
        db.session.add(item_sold)
        db.session.commit()
        item.item_quantity = item.item_quantity - item_sold.item_quantity
        item.item_value = item.item_quantity * item.item_price
        db.session.commit()
        return redirect(url_for('stock_sold', shop_id=shop.id))
    cart_items = StockSold.query.filter_by(sale_id=None).all()
    total_amount = 0
    for item in cart_items:
        total_amount += item.item_value
    if sales_form.validate_on_submit() and sales_form.submit.data:
        discount = sales_form.sale_discount.data if sales_form.sale_discount.data else 0
        print(sales_form.payment_method)
        if sales_form.payment_method.data == 'Credit':
            session["payment_method"] = sales_form.payment_method.data
            session["sales_discount"] = discount
            session["shop_id"] = shop.id
            return redirect(url_for("debt_registration"))
        sale = Sale(sales_discount=discount, payment_method=sales_form.payment_method.data,
                    shop_id=shop.id)
        sale.sales_value = total_amount - discount
        db.session.add(sale)
        db.session.commit()
        print("hello")
        for item in cart_items:
            item.sale_id = sale.id
            db.session.commit()
        return redirect(url_for('stock_sold', shop_id=shop.id))

    sales_lookup = {}
    total_discount = {}
    Date = today_date()
    current_date = datetime.now()
    sales_entries = Sale.query.filter(Sale.date_sold <= current_date, Sale.shop_id == shop.id
                                           ).order_by(Sale.date_sold.desc()).all()
    for entry in sales_entries:
        entry_id = entry.id
        total_discount[entry_id] = sum([(item.item_discount*item.item_quantity) for item in entry.sale_items]) + entry.sales_discount
        date = entry.date_sold.strftime("%d-%m-%Y")
        if date in sales_lookup:
            sales_lookup[date].append(entry)
        else:
            sales_lookup[date] = [entry]

    return render_template('stock_sold.html', selection_form=selection_form, sales_lookup=sales_lookup, Date=Date, shop=shop,
                           sales_form=sales_form, cart_items=cart_items, total_amount=total_amount,
                           sales_entries=sales_entries, total_discount=total_discount)


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


@app.route('/search_debtor', methods=['GET', 'POST'])
def search_debtor():
    phone_number = request.json["phone_number"]

    debtor = Debtor.query.filter_by(phone_number=phone_number).first()
    response = {}
    if debtor:
        response = {
            "id": debtor.id,
            "name": debtor.name,
            "company_name": debtor.company_name,
            "balance": debtor.unpaid_amount,
            "phone_number": debtor.phone_number,
        }
    return jsonify(response)


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
        if store_stock.item_quantity <= 500:
            store_stock.stock_status = "Running Out"
        store_stock.item_value = store_stock.item_selling_price * store_stock.item_quantity
        try:
            db.session.add(store_stock)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('An error occurred while adding the item.', 'danger')
        if store_stock.item_selling_price < store_stock.item_cost_price:
            flash('Selling price is less than cost price.', 'warning')
        return redirect(url_for('add_store_stock', store_id=store.id))
    return render_template('add_store_stock.html', form=form, store=store)


@app.route('/view_stores/<int:store_id>/stock_in', methods=['GET', 'POST'])
def stock_in(store_id):
    store = Store.query.get_or_404(store_id)
    form = StoreStockInForm()
    # form.populate_item_name_choices()
    # selected_item_id = form.get_selected_item_id()
    # item = StoreStock.query.filter_by(id=selected_item_id).first()
    if form.validate_on_submit():
        item = StoreStock.query.filter_by(item_name=form.item_name.data).first()
        item_received = StockIn(item_name=form.item_name.data, item_quantity=form.item_quantity.data, store_id=store.id,
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
    # form.populate_item_name_choices()
    form.populate_shop_choices()
    # selected_item_id = form.get_selected_item_id()
    selected_shop_id = form.get_selected_shop_id()
    # item = StoreStock.query.filter_by(id=selected_item_id).first()
    shop = Shop.query.filter_by(id=selected_shop_id).first()
    if form.validate_on_submit():
        item = StoreStock.query.filter_by(item_name=form.item.item_name).first()
        stock_out = StockOut(item_name=form.item.item_name, item_quantity=form.item_quantity.data,
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


# @app.route('/monthly_sales_data')
# def monthly_sales_data():
#     today = datetime.now().date()
#     start_date = today - timedelta(days=30*12)
#     sales_entries = Sale.query.filter(Sale.date_sold >= start_date).all()
#     data = {}
#     # for entry in sales_entries:
#     #     month = entry.date_sold.strftime("%B")
#     #     if month in data:
#     #         data[month] += entry.item_quantity
#     #     else:
#     #         data[month] = entry.item_quantity
#     # monthly_sales = {"labels": list(data.keys()), "data": list(data.values())}
#     return monthly_sales


@app.route('/<int:stock_id>/edit_shop_stock', methods=['GET', 'POST'])
def edit_shop_stock(stock_id):
    stock = Stock.query.get_or_404(stock_id)
    form = ShopNewItemForm()
    if request.method == 'GET':
        form.item_name.data = stock.item_name
        form.item_quantity.data = stock.item_quantity
        form.item_price.data = stock.item_price
    if form.validate_on_submit():
        stock.item_name = form.item_name.data
        stock.item_quantity = form.item_quantity.data
        stock.item_price = form.item_price.data
        db.session.commit()
        return redirect(url_for('view_shop', shop_id=stock.shop.id))
    return render_template('edit_shop_stock.html', form=form)


@app.route('/<int:stock_sold_id>/edit_shop_sale', methods=['GET', 'POST'])
def edit_stock_sold(stock_sold_id):
    stock_sold = StockSold.query.get_or_404(stock_sold_id)
    form = ShopStockSoldForm()
    if request.method == 'GET':
        form.item_name.data = stock_sold.item_name
        form.item_quantity.data = stock_sold.item_quantity
        form.item_discount.data = stock_sold.item_discount
        form.payment_method.data = stock_sold.payment_method
    if form.validate_on_submit():
        stock_sold.item_name = form.item_name.data
        stock_sold.item_quantity = form.item_quantity.data
        stock_sold.item_discount = form.item_discount.data
        stock_sold.payment_method = form.payment_method.data
        db.session.commit()
        return redirect(url_for('view_shop', shop_id=stock_sold.shop.id))
    return render_template('edit_shop_sales.html', form=form)


@app.route('/<int:shop_id>/shop/daily_count', methods=['GET', 'POST'])
def daily_count(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    items_list = [item for item in shop.stock]
    print(request.form)
    form = DailyCountForm()
    if form.validate_on_submit():
        daily_count = DailyCount(quantity=form.quantity.data, shop_id=shop.id, stock_id=item.id)
    return render_template('daily_count.html', form=form, items_list=items_list)


@app.route('/debt_registration/', methods=['GET', 'POST'])
def debt_registration():
    form = DebtorRegistrationForm()
    if form.validate_on_submit():
        total_amount = 0
        cart_items = StockSold.query.filter_by(sale_id=None)
        for item in cart_items:
            total_amount += item.item_value
        shop_id = session.get("shop_id")
        discount = session.get("sales_discount")
        payment_method = session.get("payment_method")
        sale = Sale(sales_discount=discount, payment_method=payment_method,
                    shop_id=shop_id)
        sale.sales_value = total_amount - discount
        db.session.add(sale)
        db.session.commit()
        amount_paid = form.amount_paid.data if form.amount_paid.data else 0
        debtor = Debtor.query.filter_by(phone_number=form.phone_number.data).first()
        if debtor:
            debtor.amount_paid = debtor.amount_paid + amount_paid
            debtor.unpaid_amount = debtor.unpaid_amount + (sale.sales_value - amount_paid)
        else:
            name = form.name.data
            company_name = form.company_name.data
            phone_number = form.phone_number.data
            amount_paid = amount_paid
            unpaid_amount = sale.sales_value - amount_paid
            debtor = Debtor(name=name, company_name=company_name, phone_number=phone_number,
                            amount_paid=amount_paid, unpaid_amount=unpaid_amount)
        sale.debtor_id = debtor.id
        db.session.add(debtor)
        db.session.commit()
        for item in cart_items:
            item.sale_id = sale.id
            db.session.commit()
        return redirect(url_for('stock_sold', shop_id=shop_id))
    return render_template('debt_registration.html', form=form)
