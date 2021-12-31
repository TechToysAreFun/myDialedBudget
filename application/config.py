import os
from tempfile import mkdtemp

class Config:
    # Maue sure the server auto-updates templates when any changes are made
    TEMPLATES_AUTO_RELOAD = True

    SECRET_KEY = os.environ.get('BUDGET_BUDDY_SECRET_KEY')

    # Configure gmail API
    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT  = 587
    MAIL_USERNAME = os.environ.get('BUDGET_BUDDY_GMAIL_USER')
    MAIL_PASSWORD  = os.environ.get('BUDGET_BUDDY_GMAIL_PASS')
    MAIL_USE_TLS = True

    # Configure session to use filesystem (instead of signed cookies)
    SESSION_FILE_DIR = mkdtemp()
    SESSION_PERMANENT = False
    SESSION_TYPE = "filesystem"