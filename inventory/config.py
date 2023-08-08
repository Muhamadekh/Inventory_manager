import os
# import json
#
# with open("/etc/config.json") as config_file:
# 	config = json.load(config_file)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI")
