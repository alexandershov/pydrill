from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.redis import FlaskRedis


app = Flask(__name__)
app.config.from_pyfile('/etc/pydrill/pydrill.cfg')

db = SQLAlchemy(app)
redis_store = FlaskRedis(app)
