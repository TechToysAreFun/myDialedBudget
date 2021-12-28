from cs50 import SQL
from flask import Flask, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from application.helpers import usd

# Configure application
app = Flask(__name__)

# Maue sure the server auto-updates templates when any changes are made
app.config["TEMPLATES_AUTO_RELOAD"] = True

app.config["SECRET_KEY"] = 'TEST'

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