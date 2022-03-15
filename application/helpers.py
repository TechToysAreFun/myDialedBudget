# The contents of this file are copied directly from Harvard's cs50x Finance source code
from flask import redirect, session, request
from functools import wraps

def login_required(f):
    """
    Decorate routes to require login.
    https://flask.palletsprojects.com/en/2.0.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login", next=request.url)
        return f(*args, **kwargs)
    return decorated_function

def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"
