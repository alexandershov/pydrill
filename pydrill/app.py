from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config.from_pyfile('/etc/pydrill/pydrill.cfg')

db = SQLAlchemy(app)
