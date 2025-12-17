



import logging
import urllib
from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_session import Session

app = Flask(__name__)
app.config.from_object(Config)


logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)


params = urllib.parse.quote_plus(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=cms-flask-server.database.windows.net;"
    "DATABASE=cmsdb;"
    "UID=cmsadmin;"
    "PWD=CMS4dmin;"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=30;"
)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mssql+pyodbc:///?odbc_connect={params}"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

Session(app)
db = SQLAlchemy(app)

login = LoginManager(app)
login.login_view = "login"


import FlaskWebProject.views

