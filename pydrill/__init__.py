import os

from flask import Flask
from flask.ext.redis import FlaskRedis
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_pyfile(os.environ.get('PYDRILL_CONFIG', '/etc/pydrill/pydrill.cfg'))

db = SQLAlchemy(app)
redis_store = FlaskRedis(app)


# adding views, models, and jinja2 stuff to our app
from pydrill import models  # noqa
from pydrill import views  # noqa
from pydrill import jinja_env  # noqa
