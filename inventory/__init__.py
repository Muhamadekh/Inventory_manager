from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from inventory.config import Config
from flask_cors import CORS


app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db, render_as_batch=True)
bcrypt = Bcrypt(app)
cors = CORS()
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = ""
login_manager.login_message_category = "info"

from inventory import routes
