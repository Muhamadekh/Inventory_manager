from flask import render_template, url_for, flash, redirect, session, request, jsonify
from inventory import app, bcrypt, db
from inventory.models import (User, Shop, StockReceived, StockSold, Debtor, Store, Item, StockOut, Sale,
                              StockIn, ShopItem, StoreItem, Shopkeeper, DailyCount, Account, AccountMovement,
                              AccountBalanceLog, Payment, TransferStock, CountDifference, TrashLog, PriceLog, Expense)
from inventory.forms import (UserRegistrationForm, ShopRegistrationForm, LoginForm, ExpenseForm,
                             ShopStockReceivedForm, ShopStockSoldForm, DebtorRegistrationForm, StoreRegistrationForm,
                             StoreNewItemForm, StoreStockInForm, StoreStockOutForm, SaleForm,
                             ShopKeeperRegistrationForm,
                             AccountRegistrationForm, PaymentForm, UpdateDebtorForm, TransferStockForm,
                             StockFromShopForm, UpdateAccountForm, UpdateStoreStockOutForm,
                             UpdateTransferStockForm, UpdateStoreStockForm, UpdateDailyCountForm)
from flask_login import current_user, login_user, logout_user, login_required
from datetime import datetime, timedelta
from sqlalchemy import func
from flask import make_response
import itertools
from sqlalchemy.exc import IntegrityError
import xlsxwriter


def today_date():
    date_today = datetime.today().strftime('%Y-%m-%d')
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
    sales = Sale.query.order_by(Sale.date_sold.desc()).all()
    for sale in sales:
        today = today_date()
        if sale.date_sold.strftime("%Y-%m-%d") == today:
            sales_value_list.append(sale.sales_value)
            discount_list.append(sale.sales_discount)
            for item in sale.sale_items:
                if item.item_discount > 0:
                    discount_list.append(item.item_discount * item.item_quantity)
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
    sorted_top_items_sold_lookup = dict(sorted(top_items_sold_lookup.items(), key=lambda x: x[1], reverse=True))
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

    return render_template('home.html', current_date=current_date, total_stock_value=total_stock_value,
                           total_store_stock=total_store_stock,
                           total_sales_value=total_sales_value, total_discount=total_discount,
                           top_5_items_sold=top_5_items_sold,
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
    return render_template('view_shop.html', shop=shop, total_stock_value=total_stock_value, date=date,
                           ShopItem=ShopItem)


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
        selected_name = form.item_name.data.split(" (")
        item_name = selected_name[0]
        item = Item.query.filter_by(item_name=item_name).first()
        item_received = StockReceived(item_name=item.item_name, item_quantity=form.item_quantity.data, shop_id=shop.id)
        item_sent = StockOut.query.filter_by(is_received=False, item_name=item.item_name,
                                             item_quantity=form.item_quantity.data, shop_id=shop.id).first()
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
            if shop_item.item_quantity < 40:
                shop_item.item_status = 'Running Out'
            else:
                shop_item.item_status = 'In Stock'
            db.session.commit()
        else:
            shop_item = ShopItem(shop=shop, item=item, item_quantity=form.item_quantity.data)
            shop_item.item_value = form.item_quantity.data * item.item_cost_price
            db.session.add(shop_item)
            db.session.commit()
            if shop_item.item_quantity < 40:
                shop_item.stock_status = 'Running Out'
            else:
                shop_item.item_status = 'In Stock'
            db.session.commit()
        flash("Item added to stock", "success")
        return redirect(url_for('stock_received', shop_id=shop.id))

    restock_lookup = {}
    current_date = datetime.now()
    restock_entries = StockOut.query.filter(StockOut.date_sent <= current_date, StockOut.is_received is True,
                                            StockOut.shop_id == shop.id) \
        .order_by(StockOut.date_sent.desc()).all()
    for entry in restock_entries:
        date = entry.date_sent.strftime("%d-%m-%Y")
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
    # Form to add items to cart
    if selection_form.validate_on_submit() and selection_form.submit.data:
        item_name = selection_form.item_name.data
        item = Item.query.filter_by(item_name=item_name).first()  # query the item class using the item name selected
        shop_item = ShopItem.query.filter_by(item_id=item.id, shop_id=shop_id).first()  # get shop item
        discount = selection_form.item_discount.data if selection_form.item_discount.data else 0  # get the item discount
        if shop_item and shop_item.item_quantity >= selection_form.item_quantity.data:   # Check whether quantity in stock
            item_sold = StockSold(item_name=item_name, item_quantity=selection_form.item_quantity.data,
                                  item_discount=discount, item_cost_price=item.item_cost_price,
                                  item_selling_price=item.item_selling_price, shop_id=shop_id)
            item_sold.item_value = item_sold.item_quantity * (item.item_selling_price - discount)
            db.session.add(item_sold)
            db.session.commit()
            return redirect(url_for('stock_sold', shop_id=shop.id))
        else:
            flash("No enough quantity is stock", "warning")
    cart_items = StockSold.query.filter_by(sale_id=None, shop_id=shop_id).all()  # Grab cart items
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
        for cart_item in cart_items:
            cart_item.sale_id = sale.id
            item = Item.query.filter_by(item_name=cart_item.item_name).first()
            shop_item = ShopItem.query.filter_by(item_id=item.id, shop_id=shop_id).first()  # get shop item
            shop_item.item_quantity -= cart_item.item_quantity  # Deduct the quantity if item is sold/assigned sale id
            shop_item.item_value = shop_item.item_quantity * item.item_cost_price
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
        total_discount[entry_id] = sum(
            [(item.item_discount * item.item_quantity) for item in entry.sale_items]) + entry.sales_discount
        date = entry.date_sold.date()
        if date in sales_lookup:
            sales_lookup[date].append(entry)
        else:
            sales_lookup[date] = [entry]

    # Getting today's total sales
    today_sales = []
    sales = Sale.query.filter_by(shop_id=shop.id).all()
    for sale in sales:
        today = today_date()
        if sale.date_sold.strftime("%Y-%m-%d") == today:
            today_sales.append(sale.sales_value)
    today_total_sales = sum(today_sales)

    return render_template('stock_sold.html', selection_form=selection_form, sales_lookup=sales_lookup, Date=Date,
                           shop=shop,
                           sales_form=sales_form, cart_items=cart_items, total_amount=total_amount,
                           sales_entries=sales_entries, total_discount=total_discount, today_total_sales=today_total_sales)


@app.route('/<int:shop_id>/transfer_stock', methods=['GET', 'POST'])
def transfer_stock(shop_id):
    shop_from = Shop.query.get_or_404(shop_id)
    form = TransferStockForm()
    form.populate_shop_choices()
    selected_shop_id = form.get_selected_shop_id()
    shop_to = Shop.query.filter_by(id=selected_shop_id).first()
    if form.validate_on_submit():
        item_name = form.item_name.data
        item = Item.query.filter_by(item_name=item_name).first()
        shop_item = ShopItem.query.filter_by(item_id=item.id, shop_id=shop_from.id).first()
        if shop_item and shop_item.item_quantity >= form.item_quantity.data > 0:
            if shop_from.id != shop_to.id:
                stock_sent = TransferStock(item_name=item_name, item_quantity=form.item_quantity.data,
                                           transfer_from_id=shop_from.id, transfer_to_id=shop_to.id)
                shop_item.item_quantity -= form.item_quantity.data
                shop_item.item_value = shop_item.item_quantity * item.item_cost_price
                db.session.add(stock_sent)
                db.session.commit()
                db.session.commit()
                flash("Stock transferred successfully", "success")
                return redirect(url_for('transfer_stock', shop_id=shop_from.id))
            else:
                flash("Please select the right shop.", "warning")
        else:
            flash("Quantity is more than available.", "warning")

    stock_transfered_lookup = {}

    current_date = datetime.now()
    stock_sent_entries = TransferStock.query.filter(TransferStock.date_sent <= current_date,
                                                    TransferStock.transfer_from_id == shop_from.id) \
        .order_by(TransferStock.date_sent.desc()).all()
    for entry in stock_sent_entries:
        date = entry.date_sent.date()
        if date in stock_transfered_lookup:
            stock_transfered_lookup[date].append(entry)
        else:
            stock_transfered_lookup[date] = [entry]

    return render_template('transfer_stock.html', form=form, stock_transfered_lookup=stock_transfered_lookup,
                           shop=shop_from)


@app.route('/<int:shop_id>/stock_from_shop', methods=['GET', 'POST'])
def stock_from_shop(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    form = StockFromShopForm()
    if form.validate_on_submit():
        selected_name = form.item_name.data.split(" (")
        item_name = selected_name[0]
        item = Item.query.filter_by(item_name=item_name).first()
        item_received = StockReceived(item_name=item.item_name, item_quantity=form.item_quantity.data, shop_id=shop.id)
        item_sent = TransferStock.query.filter_by(is_received=False, item_name=item.item_name,
                                                  item_quantity=form.item_quantity.data, transfer_to_id=shop.id).first()
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
            if shop_item.item_quantity < 40:
                shop_item.item_status = 'Running Out'
            else:
                shop_item.item_status = 'In Stock'
            db.session.commit()
        else:
            shop_item = ShopItem(shop=shop, item=item, item_quantity=form.item_quantity.data)
            shop_item.item_value = form.item_quantity.data * item.item_cost_price
            db.session.add(shop_item)
            db.session.commit()
            if shop_item.item_quantity < 40:
                shop_item.stock_status = 'Running Out'
            else:
                shop_item.item_status = 'In Stock'
            db.session.commit()
        flash("Item added to stock", "success")
        return redirect(url_for('stock_from_shop', shop_id=shop.id))

    restock_lookup = {}
    current_date = datetime.now()
    restock_entries = TransferStock.query.filter(TransferStock.date_sent <= current_date,
                                                 TransferStock.transfer_to_id == shop.id,
                                                 TransferStock.is_received == True) \
        .order_by(TransferStock.date_sent.desc()).all()
    for entry in restock_entries:
        date = entry.date_sent.strftime("%d-%m-%Y")
        if date in restock_lookup:
            restock_lookup[date].append(entry)
        else:
            restock_lookup[date] = [entry]
    return render_template('stock_from_shop.html', form=form, shop=shop, restock_lookup=restock_lookup)


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
        item = Item(item_name=form.item_name.data, item_cost_price=form.item_cost_price.data,
                    item_selling_price=form.item_selling_price.data)
        try:
            db.session.add(item)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('An error occurred while adding the item.', 'danger')
        if form.item_selling_price.data < form.item_cost_price.data:
            flash('Item Added successfully', 'success')
            flash('NOTE: Selling Price is less than Cost Price', 'danger')
        else:
            flash('Item added successfully.', 'success')
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
            store_item = StoreItem.query.filter_by(item_id=item.id, store_id=store.id).first()
            store_item.item_quantity += item_received.item_quantity

            # Calculate new cost price when new items are received
            item_quantity_list = []  # A list to store quantities of the item in different locations
            for warehouse in Store.query.all():  # Quantity of the item in stores
                product = StoreItem.query.filter_by(item_id=item.id, store_id=warehouse.id).first()
                if product and product.item_quantity > 0:
                    item_quantity_list.append(product.item_quantity - form.item_quantity.data)
            for shop in Shop.query.all():  # Quantity of the item in shops
                shop_item = ShopItem.query.filter_by(item_id=item.id, shop_id=shop.id).first()
                if shop_item:
                    item_quantity_list.append(shop_item.item_quantity)

            # Check if this item has been transferred between shops and not yet received
            item_from_shops = TransferStock.query.filter_by(is_received=False, item_name=item.item_name).all()
            if item_from_shops:
                for item_from_shop in item_from_shops:
                    item_quantity_list.append(item_from_shop.item_quantity)

            # Check if this item has been transferred from a store and not yet received
            item_from_stores = StockOut.query.filter_by(is_received=False, item_name=item.item_name).all()
            if item_from_stores:
                for item_from_store in item_from_stores:
                    item_quantity_list.append(item_from_store.item_quantity)

            total_item_stock = sum(item_quantity_list)  # sum up all the item quantities in different places
            # Calculate new cost price
            old_item_cost_price = item.item_cost_price
            total_old_cost = old_item_cost_price * total_item_stock
            new_item_cost_price = form.new_price.data
            total_new_cost = new_item_cost_price * form.item_quantity.data
            total_cost = total_old_cost + total_new_cost
            total_quantity = total_item_stock + form.item_quantity.data
            item.item_cost_price = total_cost / total_quantity  # Update item cost price in db
            store_item = StoreItem.query.filter_by(item_id=item.id, store_id=store.id).first()
            store_item.item_value = store_item.item_quantity * item.item_cost_price # Update item value

            # Checking item quantity status
            if store_item.item_quantity < 100:
                store_item.stock_status = 'Running Out'
            else:
                store_item.item_status = 'In Stock'
            db.session.commit()
        else:
            store_item = StoreItem(store=store, item=item, item_quantity=form.item_quantity.data)
            store_item.item_value = form.item_quantity.data * item.item_cost_price
            db.session.add(store_item)

            # Calculate new cost price when new items are received
            item_quantity_list = []  # A list to store quantities of the item in different locations
            for warehouse in Store.query.all():  # Quantity of the item in stores
                product = StoreItem.query.filter_by(item_id=item.id, store_id=warehouse.id).first()
                if product and product.item_quantity > 0:
                    item_quantity_list.append(product.item_quantity - form.item_quantity.data)
            for shop in Shop.query.all():  # Quantity of the item in shops
                shop_item = ShopItem.query.filter_by(item_id=item.id, shop_id=shop.id).first()
                if shop_item:
                    item_quantity_list.append(shop_item.item_quantity)

            # Check if this item has been transferred between shops and not yet received
            item_from_shops = TransferStock.query.filter_by(is_received=False, item_name=item.item_name).all()
            if item_from_shops:
                for item_from_shop in item_from_shops:
                    item_quantity_list.append(item_from_shop.item_quantity)

            # Check if this item has been transferred from a store and not yet received
            item_from_stores = StockOut.query.filter_by(is_received=False, item_name=item.item_name).all()
            if item_from_stores:
                for item_from_store in item_from_stores:
                    item_quantity_list.append(item_from_store.item_quantity)

            total_item_stock = sum(item_quantity_list)  # sum up all the item quantities in different places
            # Calculate new cost price
            old_item_cost_price = item.item_cost_price
            total_old_cost = old_item_cost_price * total_item_stock
            new_item_cost_price = form.new_price.data
            total_new_cost = new_item_cost_price * form.item_quantity.data
            total_cost = total_old_cost + total_new_cost
            total_quantity = total_item_stock + form.item_quantity.data
            item.item_cost_price = total_cost / total_quantity  # Update item cost price in db
            store_item = StoreItem.query.filter_by(item_id=item.id, store_id=store.id).first()
            store_item.item_value = store_item.item_quantity * item.item_cost_price  # Update item value

            if store_item.item_quantity < 100:
                store_item.stock_status = 'Running Out'
            else:
                store_item.item_status = 'In Stock'
            db.session.commit()
        flash("Item added to stock", "success")
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
            flash("Stock sent successfully", "success")
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


@app.route('/<int:stock_id>/edit_store_stock', methods=['GET', 'POST'])
def edit_store_stock(stock_id):
    stock = StoreItem.query.get_or_404(stock_id)
    item = Item.query.get_or_404(stock.item_id)
    store = Store.query.get_or_404(stock.store.id)
    form = UpdateStoreStockForm()
    if request.method == 'GET':
        form.item_name.data = stock.item.item_name
        form.item_quantity.data = stock.item_quantity
    if form.validate_on_submit():
        stock.item.item_name = form.item_name.data
        stock.item_quantity = form.item_quantity.data
        stock.item_value = stock.item_quantity * item.item_cost_price
        db.session.commit()
        return redirect(url_for('view_store', store_id=stock.store.id))
    return render_template('update_store_stock.html', form=form, store=store)


@app.route('/<int:stock_id>/edit_shop_stock', methods=['GET', 'POST'])
def edit_shop_stock(stock_id):
    stock = ShopItem.query.get_or_404(stock_id)
    item = Item.query.get_or_404(stock.item_id)
    shop = Shop.query.get_or_404(stock.shop.id)
    form = ShopStockReceivedForm()
    if request.method == 'GET':
        form.item_name.data = stock.item.item_name
        form.item_quantity.data = stock.item_quantity
    if form.validate_on_submit():
        stock.item.item_name = form.item_name.data
        stock.item_quantity = form.item_quantity.data
        stock.item_value = stock.item_quantity * item.item_cost_price
        db.session.commit()
        return redirect(url_for('view_shop', shop_id=stock.shop.id))
    form.submit.label.text = 'Update Changes'
    return render_template('stock_received.html', form=form, shop=shop)


@app.route('/<int:shop_id>/shop/daily_count', methods=['GET', 'POST'])
def daily_count(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    session["shop_id"] = shop.id
    all_stock = [item for item in ShopItem.query.filter_by(shop_id=shop.id).all() if item.item_quantity > 0]
    return render_template('daily_count.html', all_stock=all_stock, shop=shop)


@app.route('/debt_registration/', methods=['GET', 'POST'])
def debt_registration():
    form = DebtorRegistrationForm()
    if form.validate_on_submit():
        shop_id = session.get("shop_id")
        discount = session.get("sales_discount")
        payment_method = session.get("payment_method")
        total_amount = 0
        cart_items = StockSold.query.filter_by(sale_id=None, shop_id=shop_id).all()
        for item in cart_items:
            total_amount += item.item_value
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
            account_symbol = 'GNF'
            debtor = Debtor(name=name, company_name=company_name, phone_number=phone_number,
                            amount_paid=amount_paid, unpaid_amount=unpaid_amount, account_symbol=account_symbol)
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
        for cart_item in cart_items:
            cart_item.sale_id = sale.id
            item = Item.query.filter_by(item_name=cart_item.item_name).first()
            shop_item = ShopItem.query.filter_by(item_id=item.id, shop_id=shop_id).first()  # get shop item
            shop_item.item_quantity -= cart_item.item_quantity  # Deduct the quantity if item is sold/assigned sale id
            shop_item.item_value = shop_item.item_quantity * item.item_cost_price
            db.session.commit()
        return redirect(url_for('stock_sold', shop_id=shop_id))
    return render_template('debt_registration.html', form=form)


@app.route('/get_shops_stock', methods=['GET', 'POST'])
def get_shops_stock():
    searched_term = request.json["searched_term"]
    all_stock = ShopItem.query.all()
    response = []
    for item in all_stock:
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
        daily_count = DailyCount(count=count, shop_item_id=shop_item.id, shop_id=shop_id,
                                 base_count=shop_item.item_quantity)
        db.session.add(daily_count)
        db.session.commit()
    return jsonify({"shop_id": shop_id})


# View total discounts, total sales value, total item cost, net profit per shop for the last 7 days
@app.route('/shop_daily_report', methods=['GET', 'POST'])
def shop_daily_report():
    shops = Shop.query.all()
    all_sales = Sale.query.order_by(Sale.date_sold.desc()).all()  # Grab all sale objects
    date_list = []  # Store sale dates in this list
    counter = 1  # This is for displaying only the sale of the last 7 days
    for sale in all_sales:
        date = sale.date_sold.strftime("%Y-%m-%d")
        if date not in date_list and counter <= 7:
            date_list.append(date)
            counter += 1

    payment_methods_lookup = {}  # Stores payment methods and their total values for each shop
    sales_cost_lookup = {}  # Stores total cost of items sold in each shop
    discount_lookup = {}  # Stores total discount (both item discount and general sale discount) for each shop
    total_sales_lookup = {}  # Stores total sales value of items sold in each shop
    profit_lookup = {}  # Stores total profit of each shop
    total_profit = {}  # Stores total profit of all shop

    for date in date_list:
        payment_methods_lookup[date] = {}
        sales_cost_lookup[date] = {}
        discount_lookup[date] = {}
        total_sales_lookup[date] = {}
        profit_lookup[date] = {}
        total_profit[date] = 0
        for shop in shops:
            shop_name = shop.shop_name
            payment_methods_lookup[date][shop_name] = {}
            sales_cost_lookup[date][shop_name] = 0
            discount_lookup[date][shop_name] = 0
            total_sales_lookup[date][shop_name] = 0

            sales = Sale.query.filter(Sale.shop_id == shop.id).all()

            for sale in sales:
                if date == sale.date_sold.strftime("%Y-%m-%d"):
                    payment_method = sale.payment_method
                    stock_sold = StockSold.query.filter_by(sale_id=sale.id).all()
                    for item in stock_sold:
                        item_cost = item.item_quantity * item.item_cost_price

                        sales_cost_lookup[date][shop_name] += item_cost
                        discount_lookup[date][shop_name] += item.item_discount * item.item_quantity

                    discount_lookup[date][shop_name] += sale.sales_discount
                    total_sales_lookup[date][shop_name] += sale.sales_value

                    if payment_method in payment_methods_lookup[date][shop_name]:
                        payment_methods_lookup[date][shop_name][payment_method] += sale.sales_value
                    else:
                        payment_methods_lookup[date][shop_name][payment_method] = sale.sales_value
            profit_lookup[date][shop_name] = total_sales_lookup[date][shop_name] - sales_cost_lookup[date][shop_name]
            total_profit[date] += profit_lookup[date][shop_name]

    return render_template('reports.html', payment_methods_lookup=payment_methods_lookup,
                           total_sales_lookup=total_sales_lookup, sales_cost_lookup=sales_cost_lookup,
                           discount_lookup=discount_lookup, shops=shops, profit_lookup=profit_lookup,
                           total_profit=total_profit, date_list=date_list)


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
            flash("This staff is already attached to this shop.", "danger")
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
    response = [{"name": f"{item.item_name} ({item.item_quantity})"} for item in stock_sent if
                item_name.lower() in item.item_name.lower()]
    return jsonify(response)


# Remove unwanted item s from cart items list
@app.route('/<int:shop_id>/remove_cart_item/<int:item_id>', methods=['GET', 'POST'])
def remove_cart_item(shop_id, item_id):
    item = StockSold.query.filter_by(sale_id=None, id=item_id, shop_id=shop_id).first()
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
    # Store the date as the key and nest other dicts of account names as the keys and a list of all balance logs
    # for that account as the values
    balance_log_lookup = {}

    for account in accounts:
        account_name = account.account_name
        balance_logs = AccountBalanceLog.query.filter(AccountBalanceLog.account_id == account.id).order_by(
            AccountBalanceLog.timestamp.desc()).all()  # Grab the balance logs of every account
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

    return render_template('view_accounts.html', accounts=accounts, date=date, balance_log_lookup=balance_log_lookup)


# Transfer money between account
@app.route('/account_transfer', methods=['GET', 'POST'])
def account_transfer():
    accounts = Account.query.all()
    if request.method == 'POST':
        amount = float(request.form['amount'])
        transfer_from_id = int(request.form['transfer_from'])
        transfer_to_id = int(request.form['transfer_to'])
        rate = float(request.form['rate'])

        transfer_from = Account.query.get_or_404(transfer_from_id)
        transfer_to = Account.query.get_or_404(transfer_to_id)

        if transfer_from.balance >= amount:
            # Deduct amount from transfer_from account
            transfer_from.balance -= amount
            balance_log = AccountBalanceLog(account_id=transfer_from.id, balance=transfer_from.balance)
            db.session.add(balance_log)
            db.session.commit()
            # Add amount to transfer_to account
            if "Dollar" not in transfer_from.account_name and "Dollar" in transfer_to.account_name:
                transfer_to.balance += amount / rate
            elif "Dollar" in transfer_from.account_name and "Dollar" not in transfer_to.account_name:
                transfer_to.balance += amount * rate
            else:
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
    date_today = datetime.now().date()
    start_date = date_today - timedelta(days=60)

    account_movement_lookup = {}
    account_movements = AccountMovement.query.filter(AccountMovement.timestamp >= start_date)\
        .order_by(AccountMovement.timestamp.desc()).all()
    for movement in account_movements:
        date = movement.timestamp.strftime("%Y-%m-%d")  # date of account movement
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
    form.populate_account_choices()
    selected_account_name = form.get_selected_account_name()
    selected_account = Account.query.filter_by(account_name=selected_account_name).first()
    if form.validate_on_submit():
        if selected_account.balance > form.amount.data:
            payment = Payment(name=form.name.data, phone_number=form.phone_number.data, amount=form.amount.data,
                              account=selected_account.account_name)
            selected_account.balance -= payment.amount
            balance_log = AccountBalanceLog(account_id=selected_account.id, balance=selected_account.balance)
            db.session.add(payment)
            db.session.add(balance_log)
            db.session.commit()
            return redirect(url_for('view_payments'))
        else:
            flash(f"No enough balance in the {selected_account.account_name} account", "danger")
            return redirect(url_for('make_payment'))
    return render_template('make_payments.html', form=form)


# View list of people you made payments to in the last 30 days
@app.route('/view_payments', methods=['GET', 'POST'])
def view_payments():
    date_today = datetime.now().date()
    start_date = date_today - timedelta(days=365)
    # Store date of payment as the key and the payee objects as a list of values
    payee_lookup = {}
    payees = Payment.query.filter(Payment.timestamp >= start_date).order_by(Payment.timestamp.desc()).all()
    for payee in payees:
        date = payee.timestamp.strftime("%Y-%m-%d")  # date of payment
        if date in payee_lookup:
            payee_lookup[date].append(payee)
        else:
            payee_lookup[date] = [payee]
    return render_template('view_payments.html', payee_lookup=payee_lookup)


# Update debtor balance or any other debtor details
@app.route('/update_debtor/<int:debtor_id>', methods=['GET', 'POST'])
def update_debtor(debtor_id):
    debtor = Debtor.query.get_or_404(debtor_id)
    form = UpdateDebtorForm()
    form.populate_account_choices()
    if request.method == 'GET':
        form.name.data = debtor.name
        form.company_name.data = debtor.company_name
        form.phone_number.data = debtor.phone_number
    if request.method == 'POST':
        debtor.name = form.name.data
        debtor.company_name = form.company_name.data
        debtor.phone_number = form.phone_number.data
        if "Dollar" in form.payment_method.data:
            debtor.account_symbol = 'USD'
        else:
            debtor.account_symbol = 'GNF'
        if form.amount_paid.data <= debtor.unpaid_amount:
            debtor.unpaid_amount -= form.amount_paid.data
        else:
            flash("Amount is more than balance", "warning")
        deposited_account = Account.query.filter_by(account_name=form.payment_method.data).first()
        deposited_account.balance += form.amount_paid.data
        balance_log = AccountBalanceLog(account_id=deposited_account.id, balance=deposited_account.balance)
        db.session.add(balance_log)
        db.session.commit()
        return redirect(url_for('view_debtors'))
    return render_template('update_debtor.html', form=form)


def get_daily_count(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    count_comparison_lookup = {}
    date_today = datetime.now()
    start_date = date_today - timedelta(days=7)
    daily_counts = DailyCount.query.filter(DailyCount.date >= start_date, DailyCount.shop_id == shop_id).order_by(
        DailyCount.date.desc()).all()
    if daily_counts:
        for item in daily_counts:
            item_name = item.daily_count_item.item.item_name
            item_id = item.daily_count_item.item.id
            shop_item = ShopItem.query.filter_by(item_id=item_id, shop_id=shop_id).first()
            date = item.date.strftime("%Y-%m-%d")

            if shop_item:
                if date in count_comparison_lookup:
                    if item_name not in count_comparison_lookup[date]:
                        count_comparison_lookup[date][item_name] = [item.base_count, item.count, item_id]
                else:
                    count_comparison_lookup[date] = {item_name: [item.base_count, item.count, item_id]}
    return count_comparison_lookup


# Show daily count from each shop 7 days
@app.route('/<int:shop_id>/view_daily_count', methods=['GET'])
def view_daily_count(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    count_comparison_lookup = get_daily_count(shop_id)  # Call the get_daily_count function
    return render_template('view_daily_count.html', count_comparison_lookup=count_comparison_lookup, shop=shop)


# Download reports of shops over a certain period of time
@app.route('/download_reports', methods=['GET', 'POST'])
def download_reports():
    shops = Shop.query.all()

    # Request reports download
    if request.args.get('download'):
        time_range = request.args.get('time_range')

        # Define the start date based on the specified time range
        if time_range == '30':  # 30 days
            start_date = datetime.now() - timedelta(days=30)
        elif time_range == '13':  # 3 months
            start_date = datetime.now() - timedelta(weeks=13)
        elif time_range == '26':  # 6 months
            start_date = datetime.now() - timedelta(weeks=26)
        elif time_range == '52':  # 6 months
            start_date = datetime.now() - timedelta(weeks=52)
        else:
            # Handle invalid time range here, e.g., redirect to an error page or display an error message
            flash("Range does not exist", "warning")

        all_sales = Sale.query.filter(Sale.date_sold >= start_date).order_by(
            Sale.date_sold.desc()).all()  # Grab all sale objects
        date_list = []  # Store sale dates in this list
        counter = 1  # This is for displaying only the sale of the last 7 days
        for sale in all_sales:
            date = sale.date_sold.strftime("%Y-%m-%d")
            if date not in date_list and counter <= int(time_range):
                date_list.append(date)
                counter += 1

        # Initialize data structures for storing the report data
        report_data = {}

        for date in date_list:
            month = datetime.strptime(date, "%Y-%m-%d").strftime("%B")  # Extract month from date
            if month not in report_data:
                report_data[month] = {'Total Profit': 0}

            for shop in shops:
                shop_name = shop.shop_name
                sales_cost = 0
                discount = 0
                total_sales = 0

                sales = Sale.query.filter(func.date(Sale.date_sold) == date, Sale.shop_id == shop.id).all()

                for sale in sales:
                    stock_sold = StockSold.query.filter_by(sale_id=sale.id).all()
                    for item in stock_sold:
                        item_cost = item.item_quantity * item.item_cost_price

                        sales_cost += item_cost
                        discount += item.item_discount * item.item_quantity

                    discount += sale.sales_discount
                    total_sales += sale.sales_value

                profit = total_sales - sales_cost

                if shop_name not in report_data[month]:
                    # noinspection PyTypeChecker
                    report_data[month][shop_name] = {
                        'Total Sales': total_sales,
                        'Total Cost': sales_cost,
                        'Total Discount': discount,
                        'Total Profit': profit
                    }
                else:
                    report_data[month][shop_name]['Total Sales'] += total_sales
                    report_data[month][shop_name]['Total Cost'] += sales_cost
                    report_data[month][shop_name]['Total Discount'] += discount
                    report_data[month][shop_name]['Total Profit'] += profit

                report_data[month]['Total Profit'] += profit

        # Sort the report data by month
        sorted_months = sorted(report_data.keys(), key=lambda m: datetime.strptime(m, "%B"))

        # Create an Excel workbook and add a worksheet
        workbook = xlsxwriter.Workbook('Shop_Reports.xlsx')
        worksheet = workbook.add_worksheet()

        # Define cell formats for headers and bold text
        header_format = workbook.add_format({'bold': True})
        bold_right_format = workbook.add_format({'bold': True, 'align': 'right'})

        # Write the headers
        headers = ['Month', 'Shop Name', 'Total Sales', 'Total Cost', 'Total Discount', 'Total Profit']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Write the report data
        row = 1
        for month in sorted_months:
            for shop_name, shop_data in report_data[month].items():
                if shop_name != 'Total Profit':
                    worksheet.write(row, 0, month)
                    worksheet.write(row, 1, shop_name)
                    worksheet.write(row, 2, shop_data['Total Sales'])
                    worksheet.write(row, 3, shop_data['Total Cost'])
                    worksheet.write(row, 4, shop_data['Total Discount'])
                    worksheet.write(row, 5, shop_data['Total Profit'])
                    row += 1

        # Merge cells for the "Total Profit for all shops" row
        last_row = row
        worksheet.merge_range(last_row, 0, last_row, 4, 'Total Profit for all shops', bold_right_format)
        worksheet.write(last_row, 5, report_data[sorted_months[-1]]['Total Profit'], bold_right_format)

        # Set column widths
        worksheet.set_column(0, 0, 12)
        worksheet.set_column(1, 1, 20)
        worksheet.set_column(2, 5, 15)

        # Close the workbook
        workbook.close()

        # Prepare the response with the Excel file
        filename = 'Shop_Reports.xlsx'
        with open('Shop_Reports.xlsx', 'rb') as file:
            response = make_response(file.read())
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        response.headers['Content-type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        return response


# Get items transfered from another shop
@app.route('/get_transferred_items', methods=['GET', 'POST'])
def get_transfered_items():
    item_name = request.json["item_name"]
    shop_id = request.json["shop_id"]
    shop = Shop.query.get_or_404(shop_id)
    stock_sent = TransferStock.query.filter_by(is_received=False, transfer_to_id=shop.id).all()
    response = [{"name": f"{item.item_name} ({item.item_quantity})"} for item in stock_sent if
                item_name.lower() in item.item_name.lower()]
    return jsonify(response)


# Remove a shopkeeper from a shop
@app.route('/remove_shopkeeper/<int:shopkeeper_id>', methods=['GET', 'POST'])
def remove_shopkeeper(shopkeeper_id):
    shopkeeper = Shopkeeper.query.get_or_404(shopkeeper_id)
    if shopkeeper:
        db.session.delete(shopkeeper)
        db.session.commit()
    else:
        flash("Shopkeeper does not exist")
    return redirect(url_for('view_shops'))


# Harmonize differences in daily count submitted by shopkeepers and item quantity in the system
@app.route('/<int:shop_id>/<int:item_id>/void_count_differences', methods=['GET', 'POST'])
def void_count_differences(shop_id, item_id):
    count_comparison_lookup = get_daily_count(shop_id)

    for date, items in count_comparison_lookup.items():
        if date == datetime.now().strftime("%Y-%m-%d"):  # Only make changes for the current date
            for item_name, values in items.items():
                if values[2] == item_id:  # Check if the item ID matches the clicked item
                    shop_item = ShopItem.query.filter_by(shop_id=shop_id, item_id=item_id).first()
                    base_count = values[0]
                    item_daily_count = values[1]

                    if base_count != item_daily_count:
                        difference = item_daily_count - base_count
                        item = CountDifference.query.filter_by(shop_id=shop_id,
                                                               shop_item_id=shop_item.id).first()
                        if item:
                            item.quantity += difference
                        else:
                            count_difference = CountDifference(quantity=difference, shop_id=shop_id,
                                                               shop_item_id=shop_item.id)
                            db.session.add(count_difference)

                        shop_item.item_quantity = item_daily_count
                        # Update the item quantity in the dictionary
                        daily_counts = DailyCount.query.filter(DailyCount.shop_item_id == shop_item.id,
                                                              DailyCount.shop_id == shop_id)\
                            .order_by(DailyCount.date.desc()).all()
                        for item in daily_counts:
                            if item.date.strftime("%Y-%m-%d") == date:
                                item.base_count = item.count
                        db.session.commit()
    return redirect(url_for('view_daily_count', shop_id=shop_id))


# List lost items for every shop for the last 30 days
@app.route('/view_lost_items', methods=['GET'])
def view_lost_items():
    lost_items_lookup = dict()
    total_value_lookup = dict()
    current_date = datetime.now()
    start_time = current_date - timedelta(days=30)
    lost_items = CountDifference.query.filter(CountDifference.date >= start_time) \
        .order_by(CountDifference.date.desc()).all()
    for item in lost_items:
        shop_name = item.difference_item.shop_name
        date = item.date.strftime("%Y-%m-%d")
        item_name = item.shop_item.item.item_name
        product = Item.query.filter_by(item_name=item_name).first()

        # Calculate the value of the lost item for this specific entry
        lost_item_value = item.quantity * product.item_cost_price

        # Update the total value for the shop in the total_value_lookup dictionary
        if shop_name in total_value_lookup:
            total_value_lookup[shop_name] += lost_item_value
        else:
            total_value_lookup[shop_name] = lost_item_value

        # Update the lost_items_lookup dictionary
        if shop_name in lost_items_lookup:
            if date in lost_items_lookup[shop_name]:
                lost_items_lookup[shop_name][date][item_name] = [item.quantity, product.item_cost_price, product.id]
            else:
                lost_items_lookup[shop_name][date] = {item_name: [item.quantity, product.item_cost_price, product.id]}
        else:
            lost_items_lookup[shop_name] = {date: {item_name: [item.quantity, product.item_cost_price, product.id]}}
    return render_template('view_lost_items.html', lost_items_lookup=lost_items_lookup,
                           total_value_lookup=total_value_lookup)


# Debtors lent by manager
@app.route('/borrowers', methods=['GET', 'POST'])
def borrowers():
    form = PaymentForm()
    form.populate_account_choices()
    selected_account_name = form.get_selected_account_name()
    account_symbol = 'GNF'
    if selected_account_name and "Dollar" in selected_account_name:
        account_symbol = 'USD'
    if form.validate_on_submit():
        debtor = Debtor.query.filter_by(phone_number=form.phone_number.data).first()
        if debtor:
            debtor.unpaid_amount += form.amount.data
        else:
            debtor = Debtor(name=form.name.data, company_name='--', phone_number=form.phone_number.data,
                            unpaid_amount=form.amount.data, amount_paid=0, account_symbol=account_symbol)
            db.session.add(debtor)
        account = Account.query.filter_by(account_name=selected_account_name).first()
        account.balance -= form.amount.data
        balance_log = AccountBalanceLog(account_id=account.id, balance=account.balance)
        db.session.add(balance_log)
        db.session.commit()
        return redirect(url_for('view_debtors'))
    return render_template('borrower_registration.html', form=form)


@app.route('/update_account/<int:account_id>', methods=['GET', 'POST'])
def update_account(account_id):
    account = Account.query.get_or_404(account_id)
    form = UpdateAccountForm()
    if request.method == 'GET':
        form.account_name.data = account.account_name
        form.balance.data = account.balance
    if request.method == 'POST':
        account.account_name = form.account_name.data
        account.balance = form.balance.data
        balance_log = AccountBalanceLog(account_id=account.id, balance=account.balance)
        db.session.add(balance_log)
        db.session.commit()
        return redirect(url_for('view_accounts'))
    return render_template('update_account.html', form=form)


@app.route('/edit_stock_from_store/<int:item_id>', methods=['GET', 'POST'])
def edit_stock_from_store(item_id):
    item = StockOut.query.get_or_404(item_id)
    form = UpdateStoreStockOutForm()
    form.populate_shop_choices()  # Populate the shop choices

    if request.method == 'GET':
        form.item_name.data = item.item_name
        form.item_quantity.data = item.item_quantity
        form.shop.data = item.shop_id  # Set the selected shop based on item's shop_id

    if request.method == 'POST':
        item.item_name = form.item_name.data
        item.item_quantity = form.item_quantity.data
        item.shop_id = form.shop.data
        db.session.commit()
        return redirect(url_for('stock_out', store_id=item.store.id))
    return render_template('update_stock_out.html', form=form, item=item)


@app.route('/edit_stock_from_shop/<int:item_id>', methods=['GET', 'POST'])
def edit_stock_from_shop(item_id):
    item = TransferStock.query.get_or_404(item_id)
    form = UpdateTransferStockForm()
    form.populate_shop_choices()

    if request.method == 'GET':
        form.item_name.data = item.item_name
        form.item_quantity.data = item.item_quantity
        form.shop.data = item.transfer_to_id  # Set the selected shop based on item's shop_id

    if request.method == 'POST':
        item.item_name = form.item_name.data
        item.item_quantity = form.item_quantity.data
        item.transfer_to_id = form.shop.data
        db.session.commit()
        return redirect(url_for('transfer_stock', shop_id=item.transfer_from.id))
    return render_template('update_transfer_stock.html', form=form, item=item)


@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    form = StoreNewItemForm()
    if request.method == 'GET':
        form.item_name.data = item.item_name
        form.item_cost_price.data = item.item_cost_price
        form.item_selling_price.data = item.item_selling_price
    if request.method == 'POST':
        item.item_name = form.item_name.data
        item.item_cost_price = form.item_cost_price.data
        item.item_selling_price = form.item_selling_price.data

        # Keep track of edited price
        price_log = PriceLog(item_name=item.item_name, item_cost_price=item.item_cost_price,
                             item_selling_price=item.item_selling_price)
        db.session.add(price_log)

        # Update item ivalue in stores and shops
        for store in Store.query.all():
            store_item = StoreItem.query.filter_by(item_id=item.id, store_id=store.id).first()
            if store_item:
                store_item.item_value = store_item.item_quantity * item.item_cost_price
        for shop in Shop.query.all():
            shop_item = ShopItem.query.filter_by(item_id=item.id, shop_id=shop.id).first()
            if shop_item:
                shop_item.item_value = shop_item.item_quantity * item.item_cost_price
        db.session.commit()
        return redirect(url_for('view_items'))
    form.submit.label.text = 'Update Changes'
    return render_template('edit_item.html', form=form)


@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserRegistrationForm()
    if request.method == 'GET':
        form.username.data = user.username
        form.user_role.data = user.user_role
    if request.method == 'POST':
        user.username = form.username.data
        user.password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.user_role = form.user_role.data
        db.session.commit()
        return redirect(url_for('view_users'))
    form.submit.label.text = 'Update Changes'
    return render_template('register_user.html', form=form)


@app.route('/edit_store/<int:store_id>', methods=['GET', 'POST'])
def edit_store(store_id):
    store = Store.query.get_or_404(store_id)
    form = StoreRegistrationForm()
    if request.method == 'GET':
        form.store_name.data = store.store_name
        form.location.data = store.location
    if request.method == 'POST':
        store.store_name = form.store_name.data
        store.location = form.location.data
        db.session.commit()
        return redirect(url_for('view_stores'))
    form.submit.label.text = 'Update Changes'
    return render_template('register_store.html', form=form)


@app.route('/edit_shop/<int:shop_id>', methods=['GET', 'POST'])
def edit_shop(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    form = ShopRegistrationForm()
    if request.method == 'GET':
        form.shop_name.data = shop.shop_name
        form.location.data = shop.location
    if request.method == 'POST':
        shop.shop_name = form.shop_name.data
        shop.location = form.location.data
        db.session.commit()
        return redirect(url_for('view_shops'))
    form.submit.label.text = 'Update Changes'
    return render_template('register_shop.html', form=form)


@app.route('/<int:store_id>/delete_store_stock/<int:item_id>', methods=['GET', 'POST'])
def delete_store_stock(store_id, item_id):
    store_item = StoreItem.query.get_or_404(item_id)
    item = Item.query.filter_by(id=store_item.item_id).first()
    trash_log = TrashLog(item_name=item.item_name, item_cost_price=item.item_cost_price,
                         item_selling_price=item.item_selling_price, item_quantity=store_item.item_quantity)
    db.session.add(trash_log)
    db.session.delete(store_item)
    db.session.commit()
    return redirect(url_for('view_store', store_id=store_id))


@app.route('/<int:shop_id>/delete_shop_stock/<int:item_id>', methods=['GET', 'POST'])
def delete_shop_stock(shop_id, item_id):
    shop_item = ShopItem.query.get_or_404(item_id)
    db.session.delete(shop_item)
    db.session.commit()
    return redirect(url_for('view_shop', shop_id=shop_id))


@app.route('/update_lost_items/<int:item_id>', methods=['GET', 'POST'])
def update_lost_items(item_id):
    form = StockFromShopForm()
    item = Item.query.get_or_404(item_id)
    print(item.item_name)
    shop_item = ShopItem.query.filter_by(item_id=item.id).first()
    print(shop_item.id)
    shop_id = shop_item.shop_id
    shop = Shop.query.get_or_404(shop_id)
    print(shop.shop_name)
    count_difference = CountDifference.query.filter_by(shop_item_id=shop_item.id, shop_id=shop.id).first()
    print(count_difference.quantity)
    if request.method == 'GET':
        form.item_name.data = item.item_name
        form.item_quantity.data = count_difference.quantity

    if request.method == 'POST':
        count_difference.quantity = form.item_quantity.data
        count_difference.shop_id = shop.id
        count_difference.shop_item_id = shop_item.id
        db.session.commit()
        return redirect(url_for('view_lost_items'))
    form.item_quantity.label.text = 'Count'
    form.submit.label.text = 'Update Changes'
    return render_template('update_lost_items.html', form=form, shop=shop, item=item)


# View items in a sale
@app.route('/<sale_id>/view_sale_items', methods=['GET'])
def view_sale_items(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    return render_template('view_sale_items.html', sale=sale)


# Edit items in a sale
@app.route('/<int:item_id>/edit_sale_item/<int:shop_id>', methods=['GET', 'POST'])
def edit_sale_item(item_id, shop_id):
    item_sold = StockSold.query.get_or_404(item_id)
    # get item sold cost price by getting the item
    item = Item.query.filter_by(item_name=item_sold.item_name).first()
    shop = Shop.query.get_or_404(shop_id)
    form = ShopStockSoldForm()
    if request.method == 'GET':
        form.item_name.data = item_sold.item_name
        form.item_quantity.data = item_sold.item_quantity
        form.item_discount.data = item_sold.item_discount

    if request.method == 'POST':
        # First remove the item from sale, shop item quantity, account balance and account balance log
        sale = Sale.query.get_or_404(item_sold.sale_id)
        sale.sales_value -= item_sold.item_quantity * (item.item_selling_price - item_sold.item_discount)

        # Update shop item quantity
        shop_item = ShopItem.query.filter_by(item_id=item.id, shop_id=shop.id).first()
        shop_item.item_quantity += item_sold.item_quantity

        # Update account and balance log
        account = Account.query.filter_by(account_name=sale.payment_method).first()
        account.balance -= item_sold.item_quantity * (item.item_selling_price - item_sold.item_discount)

        item_sold.item_name = form.item_name.data
        item_sold.item_quantity = form.item_quantity.data
        item_sold.item_discount = form.item_discount.data
        item_sold.item_value = item_sold.item_quantity * (item.item_selling_price - item_sold.item_discount)
        db.session.commit()

        # Then update sale, shop item quantity, account balance and account balance log
        item = Item.query.filter_by(item_name=item_sold.item_name).first()
        shop_item = ShopItem.query.filter_by(item_id=item.id, shop_id=shop.id).first()

        sale.sales_value += item_sold.item_quantity * (item.item_selling_price - item_sold.item_discount)
        shop_item.item_quantity -= item_sold.item_quantity
        account.balance += item_sold.item_quantity * (item.item_selling_price - item_sold.item_discount)
        balance_log = AccountBalanceLog(account_id=account.id, balance=account.balance)
        db.session.add(balance_log)
        db.session.commit()
        return redirect(url_for('stock_sold', shop_id=shop.id))
    return render_template('edit_sale_item.html', form=form, shop=shop)


# Edit daily count from shops
@app.route('/<int:item_id>/edit_daily_count/<int:shop_id>', methods=['GET', 'POST'])
def edit_daily_count(item_id, shop_id):
    shop = Shop.query.get_or_404(shop_id)
    item = Item.query.get_or_404(item_id)
    shop_item = ShopItem.query.filter_by(item_id=item.id).first()
    daily_count = DailyCount.query.filter_by(shop_item_id=shop_item.id, shop_id=shop.id)\
        .order_by(DailyCount.date.desc()).first()

    form = UpdateDailyCountForm()
    if request.method == 'GET':
        form.item_name.data = item.item_name
        form.count.data = daily_count.count

    if request.method == 'POST':
        item.item_name = item.item_name
        daily_count.count = form.count.data
        db.session.commit()
        return redirect(url_for('view_daily_count', shop_id=shop.id))
    return render_template('edit_daily_count.html', form=form)


@app.route('/price_change_log', methods=['GET'])
def price_change_log():
    current_date = datetime.now()
    start_time = current_date - timedelta(days=60)
    price_changes = PriceLog.query.filter(PriceLog.date >= start_time).all()
    return render_template('price_change.html', price_changes=price_changes)


@app.route('/trash', methods=['GET'])
def trash():
    current_date = datetime.now()
    start_time = current_date - timedelta(days=60)
    trash_items = TrashLog.query.filter(TrashLog.date >= start_time).all()
    return render_template('trash.html', trash_items=trash_items)


@app.route('/<int:shop_id>/view_sales', methods=['GET'])
def view_sales(shop_id):
    current_date = datetime.now()
    start_time = current_date - timedelta(days=7)
    sales = Sale.query.filter(Sale.date_sold >= start_time, Sale.shop_id == shop_id).order_by(Sale.date_sold.desc()).all()
    return render_template('view_sales.html', sales=sales)


@app.route('/expenses', methods=['GET', 'POST'])
def record_expense():
    form = ExpenseForm()
    form.populate_account_choices()
    selected_account_name = form.get_selected_account_name()
    selected_account = Account.query.filter_by(account_name=selected_account_name).first()
    if form.validate_on_submit():
        expense = Expense(amount=form.amount.data, account=selected_account.account_name,
                          description=form.description.data)
        selected_account.balance -= expense.amount
        balance_log = AccountBalanceLog(account_id=selected_account.id, balance=selected_account.balance)
        db.session.add(expense)
        db.session.add(balance_log)
        db.session.commit()
        return redirect(url_for('record_expense'))

    date_today = datetime.now().date()
    start_date = date_today - timedelta(days=60)

    expense_lookup = {}
    expenses = Expense.query.filter(Expense.date >= start_date).order_by(Expense.date.desc()).all()
    for expense in expenses:
        date = expense.date.strftime("%Y-%m-%d")  # date of payment
        if date in expense_lookup:
            expense_lookup[date].append(expense)
        else:
            expense_lookup[date] = [expense]

    return render_template('expenses.html', form=form, expense_lookup=expense_lookup)


@app.route('/<int:expense_id>/edit_expense', methods=['GET', 'POST'])
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    form = ExpenseForm()
    form.populate_account_choices()
    selected_account_name = form.get_selected_account_name()
    selected_account = Account.query.filter_by(account_name=selected_account_name).first()

    if request.method == 'GET':
        form.amount.data = expense.amount
        form.account.data = expense.account
        form.description.data = expense.description

    if form.validate_on_submit():
        # First, return the money in this expense to the account
        selected_account.balance += expense.amount

        # Update the form with the expense details
        expense.amount = form.amount.data
        expense.account = form.account.data
        expense.description = form.description.data

        # Updating the account balance and balance log
        selected_account.balance -= form.amount.data
        balance_log = AccountBalanceLog(account_id=selected_account.id, balance=selected_account.balance)
        db.session.add(balance_log)
        db.session.commit()
        return redirect(url_for('record_expense'))
    form.submit.label.text = 'Save Changes'
    return render_template('edit_expenses.html', form=form)
