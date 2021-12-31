import os
import secrets
from PIL import Image
from flask import flash, redirect, render_template, request, session, url_for, Blueprint
from flask_mail import Message
from application import app, nav_avatar, mail
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import datetime
import re
from application.helpers import login_required
from application import db
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

history = Blueprint('history', __name__)

""" ---------- T R A N S A C T I O N S   H I S T O R Y ------------------------------------------------------------------------------------------ """
@app.route ('/transactions')
@login_required
def transactions():

     # If user doesn't have a budget yet, alert them and return to index
    if db.execute("SELECT * FROM users WHERE user_id = ?", session['user_id'])[0]['budgets'] < 1:
        flash("You don't have a budget yet. Create one below!", "warning")
        return redirect(url_for('index'))

    # Get user's transaction history and join to cats to know whether the cat is active and indicate that in the tables
    TRANS = db.execute("SELECT * FROM trans JOIN cats ON trans.cat_id = cats.cat_id WHERE trans.user_id = ? AND trans.bud_id = ? ORDER BY trans_date DESC", session['user_id'], session['selected_bud'])

    # Get user's allocations history
    ALLOCS = db.execute("SELECT * FROM allocs WHERE user_id = ? AND bud_id = ? ORDER BY alloc_date DESC", session['user_id'], session['selected_bud'])

    # Get user's cats to reference active status in allocs
    CATS = db.execute("SELECT * FROM cats WHERE user_id = ? AND bud_id = ?", session['user_id'], session['selected_bud'])

    return render_template('transactions.html', trans=TRANS, allocs=ALLOCS, cats=CATS, ptitle='Transaction History')