from cs50 import SQL
from flask import Flask, session
from flask_session import Session
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from application.helpers import usd
from flask_mail import Mail
from application.config import Config

# Create instance of the application
app = Flask(__name__)

# Set application to use configurations in config.py
app.config.from_object(Config)

# Create instance of 'mail' for this application
mail = Mail(app)

# Make sure responses from requests aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Create custom filter
app.jinja_env.filters["usd"] = usd

# Create instance of 'Session' for this application
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///application/final.db")

# Set global variable that will hold the user's navbar avatar
nav_avatar = '/static/avatars/nav/default.png'



# routes must be imported after the database is initialized above because routes uses the db.
from application.account.routes import account
from application.allocations.routes import allocations
from application.budget.routes import budget
from application.history.routes import history
from application.settings.routes import settings
from application.transactions.routes import transactions

app.register_blueprint(account)
app.register_blueprint(allocations)
app.register_blueprint(budget)
app.register_blueprint(history)
app.register_blueprint(settings)
app.register_blueprint(transactions)