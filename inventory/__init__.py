from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager


app = Flask(__name__)


app.config['SECRET_KEY'] = 'daf871535e9fb00d72ba5e35ae01ca5f'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'landing_page'
login_manager.login_message = ""
login_manager.login_message_category = "info"

from inventory import routes
