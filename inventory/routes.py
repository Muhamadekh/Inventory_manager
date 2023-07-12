from flask import render_template, url_for, flash, redirect, session, request, jsonify
from inventory import app, bcrypt, db
from inventory.models import (User, Shop, StockReceived, StockSold, Debtor, Store, Item, StockOut, Sale,
                              StockIn, ShopItem, StoreItem, Shopkeeper, DailyCount, Account, AccountMovement,
                              AccountBalanceLog, Payment)
from inventory.forms import (UserRegistrationForm, ShopRegistrationForm, LoginForm, ShopNewItemForm,
                             ShopStockReceivedForm, ShopStockSoldForm, DebtorRegistrationForm, StoreRegistrationForm,
                             StoreNewItemForm, StoreStockInForm, StoreStockOutForm, SaleForm, ShopKeeperRegistrationForm,
                             AccountRegistrationForm, PaymentForm, UpdateDebtorForm)
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
        for item in ShopItem.query.filter_by(shop_id=shop.id).all():
            shop_stock_value_list.append(item.item_value)
        stock_value_list.append(sum(shop_stock_value_list))
    total_stock_value = sum(stock_value_list)

    # Finding total store stck value
    store_stock = []
    stores = Store.query.all()
    for store in stores:
        for item in StoreItem.query.filter_by(store_id=store.id).all():
            store_stock.append(item.item_value)
    total_store_stock = sum(store_stock)

    # Finding total net sales and discount
    sales_value_list = []
    discount_list = []
    sales = Sale.query.filter(func.date(Sale.date_sold == current_date)).all()
    for sale in sales:
        sales_value_list.append(sale.sales_value)
        discount_list.append(sale.sales_discount)
        for item in sale.sale_items:
            if item.item_discount > 0:
                discount_list.append(item.item_discount)
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
        shop_sales_lookup[shop.shop_name] = 0  # Initialize the list for each shop
        weekly_sales = Sale.query.filter(Sale.date_sold >= time_range).all()
        if weekly_sales:
            for sale in weekly_sales:
                if sale.shop_id == shop.id:  # Check if the sale belongs to the current shop
                    if shop.shop_name in shop_sales_lookup:
                        shop_sales_lookup[shop.shop_name] += sum(item.item_quantity for item in sale.sale_items)
                    else:
                        shop_sales_lookup[shop.shop_name] = sum(item.item_quantity for item in sale.sale_items)
    sorted_total_shop_sales_lookup = dict(sorted(shop_sales_lookup.items(), key=lambda x: x[1], reverse=True))

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

    if form.validate_on_submit():
        shop = Shop(shop_name=form.shop_name.data, location=form.location.data, user_id=current_user.id)
        db.session.add(shop)
        db.session.commit()
        flash(f"{shop.shop_name} at {shop.location} was successfully registered.", "success")
        return redirect(url_for('view_shops'))

    return render_template('register_shop.html', form=form, shop=shop)


@app.route('/view_shops', methods=['GET', 'POST'])
def view_shops():
    shops = Shop.query.all()
    users = User.query.all()
    date = today_date()
    shop_stock_lookup = {}
    for shop in shops:
        stock_value_list = []
        for product in ShopItem.query.filter_by(shop_id=shop.id).all():
            stock_value_list.append(product.item_value)
        total_stock_value = sum(stock_value_list)
        shop_stock_lookup[shop.id] = total_stock_value
    return render_template('view_shops.html', shop_stock_lookup=shop_stock_lookup, shops=shops, date=date, users=users)


@app.route('/view_shops/<int:shop_id>', methods=['GET'])
def view_shop(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    date = today_date()
    stock_value_list = []
    for product in ShopItem.query.filter_by(shop_id=shop.id).all():
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
    return render_template('view_shop.html', shop=shop, total_stock_value=total_stock_value, date=date, ShopItem=ShopItem)


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
                shopkeeper = Shopkeeper.query.filter_by(user_id=user.id).first()
                if shopkeeper:
                    shop = shopkeeper.shop_details
                    return redirect(url_for('stock_sold', shop_id=shop.id))
                else:
                    flash('Shopkeeper not found.', 'danger')
        else:
            flash('Please check your username and password.', 'danger')
    return render_template('login.html', form=form)



@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# Get items to be received in a store
@app.route('/get_items', methods=['GET', 'POST'])
def get_items():
    item_name = request.json["item_name"]
    items = Item.query.all()
    response = [{"name": item.item_name} for item in items if item_name.lower() in item.item_name.lower()]
    return jsonify(response)


@app.route('/<int:shop_id>/stock_received', methods=['GET', 'POST'])
def stock_received(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    form = ShopStockReceivedForm()
    if form.validate_on_submit():
        stock_sent = StockOut.query.filter_by(is_received=False).all()
        selected_name = form.item_name.data.split(" (")
        item_name = selected_name[0]
        item = Item.query.filter_by(item_name=item_name).first()
        item_received = StockReceived(item_name=item.item_name, item_quantity=form.item_quantity.data, shop_id=shop.id)
        item_sent = StockOut.query.filter_by(is_received=False, item_name=item.item_name,
                                             item_quantity=form.item_quantity.data).first()
        if item_sent and not item_sent.is_received:
            item_sent.is_received = True
            db.session.add(item_received)
            db.session.commit()
        else:
            flash("An error has occurred", "warning")
        if item in shop.items:
            shop_item = ShopItem.query.filter_by(item_id=item.id, shop_id=shop.id).first()
            shop_item.item_quantity = shop_item.item_quantity + item_received.item_quantity
            shop_item.item_value = shop_item.item_quantity * item.item_cost_price
            if shop_item.item_quantity < 500:
                shop_item.item_status = 'Running Out'
            db.session.commit()
        else:
            shop_item = ShopItem(shop=shop, item=item, item_quantity=form.item_quantity.data)
            shop_item.item_value = form.item_quantity.data * item.item_cost_price
            db.session.add(shop_item)
            db.session.commit()
            if shop_item.item_quantity < 500:
                shop_item.stock_status = 'Running Out'
            db.session.commit()

        return redirect(url_for('stock_received', shop_id=shop.id))

    restock_lookup = {}
    current_date = datetime.now()
    restock_entries = StockReceived.query.filter(StockReceived.date_received <= current_date,
                                                 StockReceived.shop_id == shop.id)\
        .order_by(StockReceived.date_received.desc()).all()
    for entry in restock_entries:
        date = entry.date_received.strftime("%d-%m-%Y")
        if date in restock_lookup:
            restock_lookup[date].append(entry)
        else:
            restock_lookup[date] = [entry]
    return render_template('stock_received.html', form=form, shop=shop, restock_lookup=restock_lookup)


# Get items in a shop to be sold
@app.route('/get_item_name', methods=['GET', 'POST'])
def get_item_name():
    item_name = request.json["item_name"]
    shop_id = request.json["shop_id"]
    shop = Shop.query.get_or_404(shop_id)
    response = [{"name": item.item_name} for item in shop.items if item_name.lower() in item.item_name.lower()]
    return jsonify(response)


@app.route('/<int:shop_id>/shop', methods=['GET', 'POST'])
def stock_sold(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    selection_form = ShopStockSoldForm()
    sales_form = SaleForm()

    if selection_form.validate_on_submit() and selection_form.submit.data:
        item_name = selection_form.item_name.data
        item = Item.query.filter_by(item_name=item_name).first()
        shop_item = ShopItem.query.filter_by(item_id=item.id, shop_id=shop_id).first()
        discount = selection_form.item_discount.data if selection_form.item_discount.data else 0
        if shop_item and shop_item.item_quantity >= selection_form.item_quantity.data:
            item_sold = StockSold(item_name=item_name, item_quantity=selection_form.item_quantity.data,
                                  item_discount=discount)
            item_sold.item_value = item_sold.item_quantity * (item.item_selling_price - discount)
            shop_item.item_quantity = shop_item.item_quantity - item_sold.item_quantity
            shop_item.item_value = shop_item.item_quantity * item.item_cost_price
            db.session.add(item_sold)
            db.session.commit()
            db.session.commit()
            return redirect(url_for('stock_sold', shop_id=shop.id))
    cart_items = StockSold.query.filter_by(sale_id=None).all()
    total_amount = 0
    for item in cart_items:
        total_amount += item.item_value
    if sales_form.validate_on_submit() and sales_form.submit.data:
        discount = sales_form.sale_discount.data if sales_form.sale_discount.data else 0
        if sales_form.credit_option.data is True:
            session["payment_method"] = sales_form.payment_method.data
            session["sales_discount"] = discount
            session["shop_id"] = shop.id
            return redirect(url_for("debt_registration"))
        sale = Sale(sales_discount=discount, payment_method=sales_form.payment_method.data,
                    shop_id=shop.id)
        sale.sales_value = total_amount - discount
        sale.amount_paid = sale.sales_value
        sale.transaction_id = sales_form.transaction_id.data if sales_form.transaction_id.data else None
        for account in Account.query.all():
            if sale.payment_method.lower() == account.account_name.lower():
                account.balance += sale.amount_paid
                balance_log = AccountBalanceLog(account_id=account.id, balance=account.balance)
                db.session.add(balance_log)
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
        date = entry.date_sold.date()
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


# Search debtor
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
    total_stock_value = []
    for store in stores:
        store_items = StoreItem.query.filter_by(store_id=store.id).all()
        stock_value_list = []
        for product in store_items:
            stock_value_list.append(product.item_value)
        total_stock_value = sum(stock_value_list)
        store_stock_lookup[store.id] = total_stock_value
    return render_template('view_stores.html', store_stock_lookup=store_stock_lookup, stores=stores, date=date,
                           total_stock_value=total_stock_value)


@app.route('/view_stores/<int:store_id>', methods=['GET'])
def view_store(store_id):
    store = Store.query.get_or_404(store_id)
    date = today_date()
    store_items = StoreItem.query.filter_by(store_id=store.id).all()
    stock_value_list = []
    for product in store_items:
        stock_value_list.append(product.item_value)
    total_stock_value = sum(stock_value_list)
    return render_template('view_store.html', store=store, total_stock_value=total_stock_value, date=date,
                           store_items=store_items)


@app.route('/add_items', methods=['GET', 'POST'])
@login_required
def add_items():
    form = StoreNewItemForm()
    if form.validate_on_submit():
        if form.item_selling_price.data > form.item_cost_price.data:
            item = Item(item_name=form.item_name.data, item_cost_price=form.item_cost_price.data,
                        item_selling_price=form.item_selling_price.data)
            try:
                db.session.add(item)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash('An error occurred while adding the item.', 'danger')
        else:
            flash('Selling price is less than cost price.', 'danger')
        return redirect(url_for('add_items'))
    return render_template('add_items.html', form=form)


@app.route('/view_items', methods=['GET', 'POST'])
def view_items():
    items = Item.query.all()
    return render_template('view_items.html', items=items)


@app.route('/view_stores/<int:store_id>/stock_in', methods=['GET', 'POST'])
def stock_in(store_id):
    store = Store.query.get_or_404(store_id)
    form = StoreStockInForm()
    if form.validate_on_submit():
        item = Item.query.filter_by(item_name=form.item_name.data).first()
        item_received = StockIn(item_name=form.item_name.data, item_quantity=form.item_quantity.data, store_id=store.id)
        db.session.add(item_received)
        db.session.commit()
        if item in store.items:
            print("yes")
            store_item = StoreItem.query.filter_by(item_id=item.id, store_id=store.id).first()
            store_item.item_quantity = store_item.item_quantity + item_received.item_quantity
            store_item.item_value = store_item.item_quantity * item.item_cost_price
            if store_item.item_quantity < 500:
                store_item.stock_status = 'Running Out'
            print("printing", store_item.item_quantity)
            db.session.commit()
        else:
            print("No")
            store_item = StoreItem(store=store, item=item, item_quantity=form.item_quantity.data)
            store_item.item_value = form.item_quantity.data * item.item_cost_price
            db.session.add(store_item)
            db.session.commit()
            if store_item.item_quantity < 500:
                store_item.stock_status = 'Running Out'
            db.session.commit()
        return redirect(url_for('stock_in', store_id=store.id))

    restock_lookup = {}
    current_date = datetime.now()
    restock_entries = StockIn.query.filter(StockIn.date_received <= current_date,
                                                 StockIn.store_id == store.id
                                                 ).order_by(StockIn.date_received.desc()).all()
    for entry in restock_entries:
        date = entry.date_received.date()
        if date in restock_lookup:
            restock_lookup[date].append(entry)
        else:
            restock_lookup[date] = [entry]

    return render_template('stock_in.html', form=form, store=store, restock_lookup=restock_lookup)


@app.route('/view_stores/<int:store_id>/stock_out', methods=['GET', 'POST'])
def stock_out(store_id):
    store = Store.query.get_or_404(store_id)
    form = StoreStockOutForm()
    form.populate_shop_choices()
    selected_shop_id = form.get_selected_shop_id()
    shop = Shop.query.filter_by(id=selected_shop_id).first()
    if form.validate_on_submit():
        selected_name = form.item_name.data.split(" (")
        item_name = selected_name[0]
        item = Item.query.filter_by(item_name=item_name).first()
        store_item = StoreItem.query.filter_by(item_id=item.id, store_id=store.id).first()
        if store_item and store_item.item_quantity >= form.item_quantity.data:
            stock_out = StockOut(item_name=item_name, item_quantity=form.item_quantity.data,
                                 store_id=store.id, shop_id=shop.id)
            store_item.item_quantity = store_item.item_quantity - form.item_quantity.data
            store_item.item_value = store_item.item_quantity * item.item_cost_price
            db.session.add(stock_out)
            db.session.commit()
            db.session.commit()
            return redirect(url_for('stock_out', store_id=store.id))
        else:
            flash("Quantity is more than available.", "warning")

    stock_out_lookup = {}

    current_date = datetime.now()
    stockout_entries = StockOut.query.filter(StockOut.date_sent <= current_date,
                                          StockOut.store_id == store.id).order_by(StockOut.date_sent.desc()).all()
    for entry in stockout_entries:
        date = entry.date_sent.date()
        if date in stock_out_lookup:
            stock_out_lookup[date].append(entry)
        else:
            stock_out_lookup[date] = [entry]

    return render_template('stock_out.html', form=form, stock_out_lookup=stock_out_lookup, shop=shop, store=store)


@app.route('/monthly_sales_data')
def monthly_sales_data():
    today = datetime.now().date()
    start_date = today - timedelta(days=31 * 6 + 30 * 5 + 29)
    sales_entries = Sale.query.filter(Sale.date_sold >= start_date).all()
    data = {}

    for entry in sales_entries:
        month = entry.date_sold.month
        month_name = datetime(2000, month, 1).strftime('%B')

        if month in data:
            data[month] += entry.sales_value
        else:
            data[month] = entry.sales_value

    sorted_data = sorted(data.items(), key=lambda x: x[0])
    sorted_months = [datetime(2000, month, 1).strftime('%B') for month, _ in sorted_data]
    sorted_values = [value for _, value in sorted_data]

    monthly_sales = {"labels": sorted_months, "data": sorted_values}
    return monthly_sales


@app.route('/<int:stock_id>/edit_shop_stock', methods=['GET', 'POST'])
def edit_shop_stock(stock_id):
    stock = ShopItem.query.get_or_404(stock_id)
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
    session["shop_id"] = shop.id
    all_stock = [item for item in ShopItem.query.filter_by(shop_id=shop.id).all()]
    return render_template('daily_count.html', all_stock=all_stock, shop=shop)


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
        sale.amount_paid = amount_paid
        sale.credit_option = True
        db.session.add(debtor)
        for account in Account.query.all():
            if sale.payment_method.lower() == account.account_name.lower():
                account.balance = account.balance + sale.amount_paid
                balance_log = AccountBalanceLog(account_id=account.id, balance=account.balance)
                db.session.add(balance_log)
        db.session.commit()
        for item in cart_items:
            item.sale_id = sale.id
            db.session.commit()
        return redirect(url_for('stock_sold', shop_id=shop_id))
    return render_template('debt_registration.html', form=form)


@app.route('/get_shops_stock', methods=['GET', 'POST'])
def get_shops_stock():
    searched_term = request.json["searched_term"]
    all_stock = ShopItem.query.all()
    response = []
    for item in all_stock:
        print(item.item_quantity, item.item.item_name)
        if item.item_quantity > 0 and searched_term.lower() in item.item.item_name.lower():
            shop_names = [shop.shop.shop_name for shop in item.item.shops]
            response.append({"name": f"{item.item.item_name} ({shop_names[:1]})"})
    return jsonify(response)


# Saving daily count of all items in the shop as submitted by the shopkeeper
@app.route('/save_daily_count', methods=['POST'])
def save_daily_count():
    shop_id = session.get("shop_id")
    daily_count_data = request.json
    for item_data in daily_count_data:
        item_id = item_data["item_id"]
        count = item_data["count"]
        shop_item = ShopItem.query.get_or_404(item_id)
        daily_count = DailyCount(count=count, shop_item_id=item_id, shop_id=shop_id)
        db.session.add(daily_count)
        db.session.commit()
    return jsonify({"shop_id": shop_id})


@app.route('/shop_daily_report', methods=['GET', 'POST'])
def shop_daily_report():
    shops = Shop.query.all()
    current_date = datetime.now().date()

    payment_methods_lookup = {}
    sales_cost_lookup = {}
    discount_lookup = {}
    total_sales_lookup = {}
    profit_lookup = {}
    total_profit = 0
    for shop in shops:
        shop_name = shop.shop_name
        payment_methods_lookup[shop_name] = {}
        sales_cost_lookup[shop_name] = 0
        discount_lookup[shop_name] = 0
        total_sales_lookup[shop_name] = 0

        sales = Sale.query.filter(func.date(Sale.date_sold == current_date), Sale.shop_id == shop.id).all()

        for sale in sales:
            payment_method = sale.payment_method
            stock_sold = StockSold.query.filter_by(sale_id=sale.id).all()

            for item in stock_sold:
                product = Item.query.filter_by(item_name=item.item_name).first()
                cost_price = product.item_cost_price
                item_cost = item.item_quantity * cost_price

                sales_cost_lookup[shop_name] += item_cost
                discount_lookup[shop_name] += item.item_discount * item.item_quantity

            discount_lookup[shop_name] += sale.sales_discount
            total_sales_lookup[shop_name] += sale.sales_value

            if payment_method in payment_methods_lookup[shop_name]:
                payment_methods_lookup[shop_name][payment_method] += sale.sales_value
            else:
                payment_methods_lookup[shop_name][payment_method] = sale.sales_value

        profit_lookup[shop_name] = total_sales_lookup[shop_name] - sales_cost_lookup[shop_name]
        total_profit += profit_lookup[shop_name]

    return render_template('reports.html', payment_methods_lookup=payment_methods_lookup,
                           total_sales_lookup=total_sales_lookup, sales_cost_lookup=sales_cost_lookup,
                           discount_lookup=discount_lookup, shops=shops, profit_lookup=profit_lookup,
                           total_profit=total_profit)


# Assign shopkeeper to a shop
@app.route('/<int:shop_id>/assign_shopkeeper', methods=['GET', 'POST'])
def assign_shopkeeper(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    form = ShopKeeperRegistrationForm()
    form.populate_shopkeeper_choices()
    selected_staff_id = form.get_selected_shopkeeper_id()
    user = User.query.filter_by(id=selected_staff_id).first()

    if form.validate_on_submit():
        shopkeeper = Shopkeeper.query.filter_by(user_id=user.id, shop_id=shop.id).first()
        if shopkeeper:
            flash("This staff is already attached to thi shop.", "danger")
        else:
            shopkeeper = Shopkeeper(user_id=user.id, shop_id=shop.id)
            db.session.add(shopkeeper)
            db.session.commit()
            return redirect(url_for('view_shops'))

    return render_template('assign_shopkeeper.html', shop=shop, form=form)


# Getting items in stores
@app.route('/get_store_items', methods=['GET', 'POST'])
def get_store_items():
    item_name = request.json["item_name"]
    store_id = request.json["store_id"]
    items = StoreItem.query.filter_by(store_id=store_id).all()
    response = [{"name": f"{item.item.item_name} ({item.item_quantity})"} for item in items if
                item_name.lower() in item.item.item_name.lower() and item.item_quantity > 0]
    return jsonify(response)


# Getting item in stock sent from a store to a shop (Stockout)
@app.route('/get_stock_sent_items', methods=['GET', 'POST'])
def get_stock_sent_items():
    item_name = request.json["item_name"]
    shop_id = request.json["shop_id"]
    shop = Shop.query.get_or_404(shop_id)
    stock_sent = StockOut.query.filter_by(is_received=False, shop_id=shop.id).all()
    response = [{"name": f"{item.item_name} ({item.item_quantity})"} for item in stock_sent if item_name.lower() in item.item_name.lower()]
    print(response[0])
    return jsonify(response)


# Remove unwanted item s from cart items list
@app.route('/<int:shop_id>/remove_cart_item/<int:item_id>', methods=['GET', 'POST'])
def remove_cart_item(shop_id, item_id):
    item = StockSold.query.filter_by(sale_id=None, id=item_id).first()
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('stock_sold', shop_id=shop_id))


# Register accounts
@app.route('/add_account', methods=['GET', 'POST'])
def add_account():
    form = AccountRegistrationForm()
    if form.validate_on_submit():
        account = Account(account_name=form.account_name.data)
        db.session.add(account)
        db.session.commit()
        flash(f"{account.account_name} was successfully registered.", "success")
        return redirect(url_for('view_accounts'))
    return render_template('add_account.html', form=form)


@app.route('/view_accounts', methods=['GET', 'POST'])
def view_accounts():
    date = today_date()
    accounts = Account.query.all()

    # Account The Last Daily Balance Log for every account
    balance_log_lookup = {}

    for account in accounts:
        account_name = account.account_name
        balance_logs = AccountBalanceLog.query.filter(AccountBalanceLog.account_id == account.id).order_by(
            AccountBalanceLog.timestamp.desc()).all()

        if balance_logs:
            for balance_log in balance_logs:
                date = balance_log.timestamp.date()

                if date in balance_log_lookup:
                    if account_name in balance_log_lookup[date]:
                        balance_log_lookup[date][account_name].append(balance_log.balance)
                    else:
                        balance_log_lookup[date][account_name] = [balance_log.balance]
                else:
                    balance_log_lookup[date] = {account_name: [balance_log.balance]}

    print(balance_log_lookup)

    return render_template('view_accounts.html', accounts=accounts, date=date, balance_log_lookup=balance_log_lookup)


# Transfer money between account
@app.route('/account_transfer', methods=['GET', 'POST'])
def account_transfer():
    accounts = Account.query.all()
    if request.method == 'POST':
        amount = float(request.form['amount'])
        transfer_from_id = int(request.form['transfer_from'])
        transfer_to_id = int(request.form['transfer_to'])

        transfer_from = Account.query.get_or_404(transfer_from_id)
        transfer_to = Account.query.get_or_404(transfer_to_id)

        if transfer_from.balance >= amount:
            # Deduct amount from transfer_from account
            transfer_from.balance -= amount
            balance_log = AccountBalanceLog(account_id=transfer_from.id, balance=transfer_from.balance)
            db.session.add(balance_log)
            db.session.commit()
            # Add amount to transfer_to account
            transfer_to.balance += amount
            balance_log = AccountBalanceLog(account_id=transfer_to.id, balance=transfer_to.balance)
            db.session.add(balance_log)
            db.session.commit()
            # Create an account movement record
            payment_movement = AccountMovement(amount=amount, transfer_from_id=transfer_from_id,
                                               transfer_to_id=transfer_to_id)
            db.session.add(payment_movement)
            db.session.commit()

            return redirect(url_for('view_accounts'))
        else:
            flash('Insufficient funds in the transfer_from account.', 'error')

    # Retrieve all account movements
    account_movement_lookup = {}
    account_movements = AccountMovement.query.all()
    for movement in account_movements:
        date = movement.timestamp.date()
        if date in account_movement_lookup:
            account_movement_lookup[date].append(movement)
        else:
            account_movement_lookup[date] = [movement]

    return render_template('account_transfer.html', accounts=accounts, account_movement_lookup=account_movement_lookup)


@app.route('/search_payee', methods=['GET', 'POST'])
def search_payee():
    phone_number = request.json["phone_number"]
    payee = Payment.query.filter_by(phone_number=phone_number).first()
    response = {}
    if payee:
        response = {
            "id": payee.id,
            "name": payee.name,
            "phone_number": payee.phone_number,
        }
    return jsonify(response)


@app.route('/make_payment', methods=['GET', 'POST'])
def make_payment():
    form = PaymentForm()
    if form.validate_on_submit():
        payment = Payment(name=form.name.data, phone_number=form.phone_number.data, amount=form.amount.data)
        db.session.add(payment)
        db.session.commit()
        return redirect(url_for('view_payments'))
    return render_template('make_payments.html', form=form)


@app.route('/view_payments', methods=['GET', 'POST'])
def view_payments():
    payees = Payment.query.all()
    return render_template('view_payments.html', payees=payees)


@app.route('/update_debtor/<int:debtor_id>', methods=['GET', 'POST'])
def update_debtor(debtor_id):
    debtor = Debtor.query.get_or_404(debtor_id)
    form = UpdateDebtorForm()
    if request.method == 'GET':
        form.name.data = debtor.name
        form.company_name.data = debtor.company_name
        form.phone_number.data = debtor.phone_number
    if request.method == 'POST':
        debtor.name = form.name.data
        debtor.company_name = form.company_name.data
        debtor.phone_number = form.phone_number.data
        if form.amount_paid.data <= debtor.unpaid_amount:
            debtor.unpaid_amount -= form.amount_paid.data
        else:
            flash("Amount is more than balance", "warning")
        db.session.commit()
        return redirect(url_for('view_debtors'))
    return render_template('update_debtor.html', form=form)


# Show daily count from each shop for the last 7 days
@app.route('/<int:shop_id>/view_daily_count', methods=['GET'])
def view_daily_count(shop_id):

    count_comparison_lookup = {}
    date_today = datetime.now().date()
    start_date = date_today - timedelta(days=7)

    daily_count = DailyCount.query.filter(func.date(DailyCount.date == date_today),
                                          DailyCount.shop_id == shop_id).order_by(DailyCount.date.desc()).all()

    for item in daily_count:
        item_name = item.daily_count_item.item.item_name
        item_id = item.daily_count_item.item.id
        shop_item = ShopItem.query.filter_by(item_id=item_id, shop_id=shop_id).first()
        date = item.date.strftime("%Y-%m-%d")
        if shop_item:
            print(shop_item)
            if date in count_comparison_lookup:
                print(item_name, date)
                if item_name in count_comparison_lookup[date]:
                    count_comparison_lookup[date][item_name].append(shop_item.item_quantity)
                    count_comparison_lookup[date][item_name].append(item.count)
                else:
                    count_comparison_lookup[date][item_name] = [shop_item.item_quantity, item.count]
            else:
                count_comparison_lookup[date] = {item_name: [shop_item.item_quantity, item.count]}
        else:
            flash("")
    print(count_comparison_lookup)
    return render_template('view_daily_count.html', count_comparison_lookup=count_comparison_lookup)
