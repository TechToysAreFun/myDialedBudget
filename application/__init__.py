import os
from cs50 import SQL
from flask import Flask, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from application.helpers import usd
from flask_mail import Mail

# Configure application
app = Flask(__name__)

# Maue sure the server auto-updates templates when any changes are made
app.config["TEMPLATES_AUTO_RELOAD"] = True

app.config["SECRET_KEY"] = os.environ.get('BUDGET_BUDDY_SECRET_KEY')

# Configure gmail API
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('BUDGET_BUDDY_GMAIL_USER')
app.config['MAIL_PASSWORD'] = os.environ.get('BUDGET_BUDDY_GMAIL_PASS')
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

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///application/final.db")

# Set global variable that will hold the user's navbar avatar
nav_avatar = '/static/avatars/nav/default.png'



# routes must be imported after the database is initialized above because routes uses the db.
from application import routes