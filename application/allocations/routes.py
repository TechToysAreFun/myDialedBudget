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

allocations = Blueprint('allocations', __name__)


""" ---------- A L L O C A T E ------------------------------------------------------------------------------------------ """
@app.route('/allocate', methods=["GET", "POST"])
@login_required
def allocate():

    if request.method == "POST":
        # Store form inputs into variables
        TO = request.form.get("TO")
        FROM = request.form.get("FROM")
        memo = request.form.get("memo")



        # Get TO & FROM ids
        TO_ID = db.execute("SELECT * FROM cats WHERE user_id = ? AND bud_id = ? AND cat_name = ?", session['user_id'], session['selected_bud'], TO)[0]['cat_id']
        FROM_ID = db.execute("SELECT * FROM cats WHERE user_id = ? AND bud_id = ? AND cat_name = ?", session['user_id'], session['selected_bud'], FROM)[0]['cat_id']


        """ Check if the request is coming from the "fully fund" dollar-sign button, which sets the value to -1 """
        fully_funded_check = False
        if request.form.get("amount") == "-1":

            # Calculate how much is needed to fully fund the goal
            amount = float(db.execute("SELECT (cat_goal - cat_funded) FROM cats WHERE user_id = ? AND bud_id = ? AND cat_id = ?", session['user_id'], session['selected_bud'],  TO_ID)[0]['(cat_goal - cat_funded)'])

            # If amount == 0.00 then goal either has been met or there isn't a goal. Find out here:
            if amount == 0.00:

                if float(db.execute("SELECT * FROM cats WHERE user_id = ? AND bud_id = ? AND cat_id = ?", session['user_id'], session['selected_bud'], TO_ID)[0]['cat_goal']) == 0.00:
                    # A Goal isn't set
                    flash("This category doesn't have a goal yet", "warning")
                    return redirect(url_for('index'))

                else:
                    # The goal is fully funded

                    # Reference this below to switch the flashed message so it's relevant to "fully funding"
                    fully_funded_check = True

                    flash("This category is already funded!", "success")
                    return redirect(url_for('index'))


        # Else, the request is coming from the Allocate page
        else:
            amount = float(request.form.get("amount"))

        # If no memo, show a blank rather than 'None'
        if not memo:
            memo = ''


        # Get date of allocation
        date = datetime.datetime.now().strftime("%Y-%m-%d")

        # Validate that all required fields were populated
        if not amount or not TO or not FROM:
            flash('Please complete all required fields', 'warning')
            return redirect(url_for('allocate'))

        # Validate that "amount" is a positive number
        if amount <= 0:
            flash('Only positive values may be allocated.', 'warning')
            return redirect(url_for('allocate'))

        # Check for sufficient funds when FROM is not 'Deposit'
        if FROM != 'Deposit':
            cat_avail = db.execute("SELECT cat_avail FROM cats WHERE user_id = ? AND bud_id = ? AND cat_name = ?", session['user_id'], session['selected_bud'], FROM)[0]['cat_avail']
            if amount > cat_avail:
                required = amount - cat_avail
                flash(f'Insufficient funds: ${"{:.2f}".format(required)} more needed in {FROM}', 'danger')
                return redirect(url_for('allocate'))


        # Update user's total_assets if from Deposit
        if FROM == 'Deposit':
            db.execute("UPDATE budgets SET total_assets = (total_assets + ?) WHERE user_id = ? and bud_id = ?", amount, session['user_id'], session['selected_bud'])

        # Decrease user's unassigned funds
        elif FROM == 'Unassigned':
            db.execute("UPDATE budgets SET unassigned = (unassigned - ?) WHERE user_id = ? AND bud_id = ?", amount, session['user_id'], session['selected_bud'])

        # Else FROM is another category, so revaluate if that category's goal has still been met after reducing it's funded amount
        else:
            CATS = db.execute("SELECT * FROM cats WHERE user_id = ? AND bud_id = ? AND cat_id = ?", session['user_id'], session['selected_bud'], FROM_ID)

            from_met = False

            # Revaluate if the FROM cat's goal has been fully funded
            if (CATS[0]['cat_funded'] - amount) >= CATS[0]['cat_goal']:
                from_met = True

            # Update goal_met
            db.execute("UPDATE cats SET cat_funded = (cat_funded - ?), cat_goal_met = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", amount, from_met, session['user_id'], session['selected_bud'], FROM_ID)



        # Increase user's unassigned funds if allocation was back to the unassigned category
        if TO == 'Unassigned':
            db.execute("UPDATE budgets SET unassigned = (unassigned + ?) WHERE user_id = ? AND bud_id = ?", amount, session['user_id'], session['selected_bud'])
            to_met = 0

        else:
            # Check if the TO cat goal has been fully funded as a result of this allocation
            to_met = 0
            funded = float(db.execute('SELECT * FROM cats WHERE user_id = ? AND bud_id = ? AND cat_id = ?', session['user_id'], session['selected_bud'], TO_ID)[0]['cat_funded'])
            goal = float(db.execute('SELECT * FROM cats WHERE user_id = ? AND bud_id = ? AND cat_id = ?', session['user_id'], session['selected_bud'], TO_ID)[0]['cat_goal'])
            if (funded + amount) >= goal:
                to_met = 1


        # Update cat_avail, cat_funded, and cat_goal_met for TO category
        db.execute("UPDATE cats SET cat_avail = (cat_avail + ?), cat_funded = (cat_funded + ?), cat_goal_met = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", amount, amount, to_met, session['user_id'], session['selected_bud'], TO_ID)

        # Update cat_avail for FROM category.
        db.execute("UPDATE cats SET cat_avail = (cat_avail - ?) WHERE user_id = ? AND bud_id = ? AND cat_id = ?", amount, session['user_id'], session['selected_bud'], FROM_ID)


        # Add allocation to allocs table
        db.execute("INSERT INTO allocs (user_id, bud_id, alloc_date, to_cat_id, to_cat_name, from_cat_id, from_cat_name, amount, memo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", session['user_id'], session['selected_bud'], date, TO_ID, TO, FROM_ID, FROM, amount, memo)

        if fully_funded_check:
            flash(f'{TO} has been fully funded!', 'success')

        else:
            flash(f'Allocated ${"{:.2f}".format(amount)} to {TO}', 'success')

        return redirect(url_for('index'))


    if request.method == "GET":
        # If user doesn't have a budget yet, alert them and return to index
        if db.execute("SELECT * FROM users WHERE user_id = ?", session['user_id'])[0]['budgets'] < 1:
            flash("You don't have a budget yet. Create one below!", "warning")
            return redirect(url_for('index'))

        # Extract user's cats and feed to html form
        CATS = db.execute("SELECT * FROM cats WHERE user_id = ? AND bud_id = ? AND active = ?", session['user_id'], session['selected_bud'], 1)

        return render_template('allocate.html', cats=CATS, ptitle='Allocate Funds')