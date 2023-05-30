from flask import Flask, render_template, url_for, flash, redirect, session, request, abort
from inventory import app, bcrypt, db
from inventory.models import User, Shop
from inventory.forms import UserRegistrationForm, ShopRegistrationForm, LoginForm, AdminLoginForm
from flask_login import current_user, login_user, logout_user, login_required


@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if current_user.user_role != 'Admin':
        return 404
    return render_template('home.html')


@app.route('/register_user', methods=['GET', 'POST'])
def register_user():
    form = UserRegistrationForm()
    user = User.query.filter_by(username=form.username.data).first()
    if user:
        flash("A user with this username exist. Try another name", "warning")
    else:
        if form.validate_on_submit():
            hashed_password = bcrypt.generate_password_hash(form.password.data)
            user = User(username=form.username.data, password=hashed_password, user_role=form.user_role.data)
            db.session.add(user)
            print(user.username)
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
        if form.validate_on_submit():
            shop = Shop(shop_name=form.shop_name.data, location=form.location.data, user_id=current_user.id)
            db.session.add(shop)
            db.session.commit()
            flash(f"{shop.shop_name} at {shop.location} was successfully registered.")
            return redirect(url_for('view_shop'))
    return render_template('register_shop.html', form=form)


@app.route('/view_shops', methods=['GET'])
def view_shop():
    shops = Shop.query.all()
    return render_template('view_shops.html', shops=shops)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    else:
        form = LoginForm()
        form.populate_shop_choices()
        if form.validate_on_submit():
            form.store_selected_shop_id_in_session()
            user = User.query.filter_by(username=form.username.data).first()
            if user and bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                next_page = request.args.get("next")
                return redirect(url_for(next_page)) if next_page else redirect(url_for('shop'))
            else:
                flash('Please check your username and password.')
        return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('landing_page'))


@app.route('/shop', methods=['GET','POST'])
def shop():
    selected_shop_id = session.get('selected_shop_id')
    print(selected_shop_id)
    user_shop = Shop.query.filter_by(id=selected_shop_id).first()
    return render_template('shop.html', user_shop=user_shop)


@app.route('/landing_page')
def landing_page():
    return render_template('landing_page.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.user_role == 'Admin':
        return redirect(url_for('home'))
    else:
        form = AdminLoginForm()
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get("next")
            if user.user_role == 'Admin':
                return redirect(url_for(next_page)) if next_page else redirect(url_for('home'))
            else:
                flash("You do not have admin privileges", "warning")
                return redirect(url_for('landing_page'))

        else:
            flash("Please check your details and make sure you have admin access", "info")
    return render_template('admin_login.html', form=form)


