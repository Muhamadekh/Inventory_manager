import os
import json

# Production
with open("/etc/config.json") as config_file:
        config = json.load(config_file)


class Config:
    SECRET_KEY = config.get("SECRET_KEY")
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
    SQLALCHEMY_DATABASE_URI = config.get("SQLALCHEMY_DATABASE_URI")


# # Development
# class Config:
#     SECRET_KEY = os.environ.get("SECRET_KEY")
#     # SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
#     SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI")


## url_for endpoints in developmet: ${window.location.hostname}:5000