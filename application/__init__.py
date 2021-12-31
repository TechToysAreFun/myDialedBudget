from cs50 import SQL
from flask import Flask, current_app
from flask_session import Session
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from application.helpers import usd
from flask_mail import Mail
from application.config import Config

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///application/final.db")

# Set global variable that will hold the user's navbar avatar
nav_avatar = '/static/avatars/nav/default.png'

# Create instance of 'mail' for this application
mail = Mail()

# Create instance of 'Session' for this application
session = Session()


def create_app(config_class=Config):
    # Create instance of the application
    app = Flask(__name__)
    # Set application to use configurations in config.py
    app.config.from_object(Config)

    with app.app_context():
        @current_app.context_processor
        def context_processor():
            return dict(avatar_key=nav_avatar)

    mail.init_app(app)
    session.init_app(app)

    # Create custom filter
    app.jinja_env.filters["usd"] = usd

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

    return app