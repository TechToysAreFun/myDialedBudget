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

budget = Blueprint('budget', __name__)

""" ---------- I N D E X ------------------------------------------------------------------------------------------ """
@app.route('/')
@login_required
def index():

    # Determine if the user has any budgets
    has_budget = True
    if db.execute("SELECT * FROM users WHERE user_id = ?", session['user_id'])[0]['budgets'] < 1:
        return render_template('index.html', has_budget=False, ptitle='Budget')


    # Find out what budget the user's account was last set to
    selected_bud = db.execute("SELECT * FROM users WHERE user_id = ?", session['user_id'])[0]['selected_bud']

    # Get all categories for budget to perform goal resets
    allCATS = db.execute("SELECT * FROM cats WHERE user_id = ? AND bud_id = ?", session['user_id'], session['selected_bud'])

    """ Perform goal resets """
    # Loop through each category in the current budget
    for cat in allCATS:
        if cat['reset'] == 1:

            # Reset goal due touple, keeping the original day, but updating the month to the next month
            cat['due_tup_m'] = (int(session['day_tup'][0]) + 1)

            # Set funded amount
            db.execute("UPDATE cats SET cat_funded = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", cat['cat_avail'], session['user_id'], session['selected_bud'], cat['cat_id'])

            # Revaluate if goal has been met. If goal is 0 though, do not set as met

            if (cat['cat_funded'] >= cat['cat_goal']):
                db.execute("UPDATE cats SET cat_goal_met = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", 1, session['user_id'], session['selected_bud'], cat['cat_id'])
            else:
                db.execute("UPDATE cats SET cat_goal_met = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", 0, session['user_id'], session['selected_bud'], cat['cat_id'])

            # Set goal spent amount to 0 and 'reset' back to false
            db.execute("UPDATE cats SET cat_goal_spent = ?, reset = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", 0.00, 0, session['user_id'], session['selected_bud'], cat['cat_id'])


    """ Create a list of dictionaries to store budget group totals """
    # Get groups
    GROUPS = db.execute("SELECT * FROM groups WHERE user_id = ? AND bud_id = ? AND active = ?", session['user_id'], session['selected_bud'], 1)

    # Declare list
    TOTALS = []

    # Loop through each group
    for group in GROUPS:
        # Calculate totals for the group
        group_totals = db.execute("SELECT SUM(cat_goal) goal, SUM(cat_spent) spent, SUM(cat_avail) avail FROM cats WHERE user_id = ? AND bud_id = ? AND group_id = ? AND active = ?", session['user_id'], session['selected_bud'], group['group_id'], 1)

        # Check if SUM(cat_goal) is NoneType, meaning none of the cats have a goal, if so, set it to 0.00
        if group_totals[0]['goal'] == None:
            group_totals[0]['goal'] = 0

        # Append the TOTALS list with a dictionary of the totals for each group
        TOTALS.append({'group_id': group['group_id'], 'goal': group_totals[0]['goal'], 'spent': group_totals[0]['spent'], 'avail': group_totals[0]['avail']})


    # Extract the user's updated selected budget, as well as groups and cats for that budget
    BUDGET = db.execute("SELECT * FROM budgets WHERE user_id = ? AND bud_id = ?", session['user_id'], session['selected_bud'])
    GROUPS = db.execute("SELECT * FROM groups WHERE user_id = ? AND bud_id = ? AND active = ?", session['user_id'], session['selected_bud'], 1)
    CATS = db.execute("SELECT * FROM cats WHERE user_id = ? AND bud_id = ? AND active = ?", session['user_id'], session['selected_bud'], 1)


    # Send the user's groups, cats, and calculated totals to index.html
    return render_template('index.html', has_budget=has_budget, budget=BUDGET, groups=GROUPS, cats=CATS, totals=TOTALS, ptitle='Budget')




""" ---------- I N D E X  /  U S A G E ------------------------------------------------------------------------------------------ """
@app.route('/index/<usage>', methods=["POST"])
@login_required
def index_usage(usage):

    """ Functions that every Usage reqires """
    # Determine current budget id
    selected_bud = db.execute("SELECT * FROM users WHERE user_id = ?", session['user_id'])[0]['selected_bud']

    """ Add Group """
    if usage == "add_group":
        # Extract form inputs into variables
        group_name = request.form.get("group_name")

        # Reject group name if it already exists in the same budget
        GROUPS = db.execute("SELECT * FROM groups WHERE user_id = ? AND bud_id = ?", session['user_id'], session['selected_bud'])
        for group in GROUPS:
            if group_name == group['group_name']:
                flash('That group name already exists in this budget.')
                return render_template('/')

        # Update user's group count in this budget
        db.execute("UPDATE budgets SET groups = (groups + ?) WHERE user_id = ? AND bud_id = ?", 1, session['user_id'], session['selected_bud'])

        # Create the group in the groups table
        db.execute("INSERT INTO groups (bud_id, user_id, group_name) VALUES (?, ?, ?)", selected_bud, session['user_id'], group_name)

        flash('Group created!', 'success')
        return redirect(url_for('index'))



    """ Add Group Category """
    if usage == "add_cat":
        # Extract form inputs into variables
        cat_name = request.form.get("cat_name")
        group_id = request.form.get("group_id")
        cat_goal = request.form.get("goal")
        due_day = request.form.get("due")

        # Get the current month integer value
        due_month = session['day_tup'][0]


        """ Validate """
        # Reject category name if it's "deposit" or "unassigned"
        if cat_name == 'Deposit' or cat_name == 'Unassigned':
            flash('Your budget automatically comes with that category.')
            return redirect(url_for('index'))


        # Reject category name if it already exists in the same budget
        CATS = db.execute("SELECT * FROM cats WHERE user_id = ? AND bud_id = ?", session['user_id'], session['selected_bud'])
        for category in CATS:
            if cat_name == category['cat_name']:
                if not category['active']:
                    flash('You already have that category name set to inactive. Reactivate in Settings page.', 'warning')
                else:
                    flash('That category name already exists in this budget.')
                return redirect(url_for('index'))


        # Update user's cat count in this group
        db.execute("UPDATE groups SET cats = (cats + ?), active_cats = (active_cats + ?) WHERE user_id = ? AND group_id = ?", 1, 1, session['user_id'], group_id)

        """ Create new category in cats table for the given group """
        # Set goal to blank if not provided
        if not cat_goal:
            cat_goal = 0.00

        # Set due_day to blank if not provided
        if not due_day:
            due_day = ''

        db.execute("INSERT INTO cats (group_id, bud_id, user_id, cat_name, cat_funded, cat_goal_met, cat_spent, cat_avail, due_tup_m, due_tup_d, cat_goal) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", group_id, session['selected_bud'], session['user_id'], cat_name, 0, 0, 0, 0, due_month, due_day, cat_goal)

        flash('Category created!', 'success')
        return redirect(url_for('index'))



    """ Edit Category """
    if usage == 'cat_edit':
        # Check variable to indicate whether redirect straight to index or back through goal_check
        check_goal = False

        # Store form inputs into variables
        cat_id = request.form.get("cat_id")
        due_day = request.form.get("new_due")
        new_goal = request.form.get("new_goal")
        new_name = request.form.get("new_name")
        rm_due = request.form.get("rm_due")
        rm_goal = request.form.get("rm_goal")


        # # If a new goal is not entered, python can't convert an empty string to a float, so check first
        # if request.form.get("new_goal"):
        #     new_goal = float(request.form.get("new_goal")

        if new_name:
        # if request.form.get("new_name"):

            new_name = request.form.get("new_name")

            # Validate that name doesn't already exist in the budget
            existing = db.execute("SELECT * FROM cats WHERE user_id = ? AND bud_id = ?", session['user_id'], session['selected_bud'])
            for name in existing:
                if new_name == name['cat_name']:
                    flash('That category already exists in your budget')
                    return redirect(url_for('index'))

            # Update cat_name
            db.execute("UPDATE cats SET cat_name = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", new_name, session['user_id'], session['selected_bud'], cat_id)

        # Update cats due_tup_d
        if due_day:
            # Convert from python string to int
            due_day = int(due_day)

            # Update due day
            db.execute("UPDATE cats SET due_tup_d = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", due_day, session['user_id'], session['selected_bud'], cat_id)

            # Tell function to route through goal_check to check if the new due date warrants a reset
            check_goal = True

        # Revaluate if goal has been met
        if new_goal:
            new_goal = float(new_goal)
            met = 0

            # Get funded amount for cat goal
            funded = db.execute("SELECT * FROM cats WHERE user_id = ? AND bud_id = ? AND cat_id = ?", session['user_id'], session['selected_bud'], cat_id)[0]['cat_funded']

            if funded >= new_goal:
                met = 1

            # Update cat_goal and goal_met
            db.execute("UPDATE cats SET cat_goal = ?, cat_goal_met = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", new_goal, met, session['user_id'], session['selected_bud'], cat_id)

        # Remove goal due date
        if rm_due == 'on':
            db.execute("UPDATE cats SET due_tup_d = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", '', session['user_id'], session['selected_bud'], cat_id)

            # Tell function to route through goal_check to check if the new due date warrants a reset
            check_goal = True


        # Remove goal
        if rm_goal == 'on':
            db.execute("UPDATE cats SET cat_goal = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", 0.00, session['user_id'], session['selected_bud'], cat_id)

            # Tell function to route through goal_check to check if the new due date warrants a reset
            check_goal = True

        flash('Category updated', 'success')

        if check_goal == False:
            return redirect(url_for('index'))
        else:
            return redirect(url_for('goal_check'))


    """ Deactivate Category """
    if usage == 'cat_del':
        # Get cat_id
        cat_id = request.form.get("cat_id")

        # Change 'active' value in cats table to false and add 'inactive' to name
        db.execute("UPDATE cats SET active = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", 0, session['user_id'], session['selected_bud'], cat_id)

        # Get the cats group_id
        group_id = db.execute("SELECT * FROM cats WHERE user_id = ? AND bud_id = ? AND cat_id = ?", session['user_id'], session['selected_bud'], cat_id)[0]['group_id']

        # Update the groups "active_cats" count
        db.execute("UPDATE groups SET active_cats = (active_cats - ?) WHERE user_id = ? AND bud_id = ? AND group_id = ?", 1, session['user_id'], session['selected_bud'], group_id)

        flash('Category deactivated', 'success')
        return redirect(url_for('goal_check'))


    """ Edit Group """
    if usage == 'group_edit':
        # Get new name and group_id
        new_name = request.form.get("new_name")
        group_id = request.form.get("group_id")

        # Validate that the new name doesn't already exist in that budget
        existing = db.execute("SELECT * FROM groups WHERE user_id = ? AND bud_id = ?", session['user_id'], session['selected_bud'])
        for name in existing:
            if new_name == name['group_name']:
                flash('That group already exists in your budget', 'warning')
                return redirect(url_for('index'))


        # Rename the group
        db.execute("UPDATE groups SET group_name = ? WHERE user_id = ? AND bud_id = ? AND group_id = ?", new_name, session['user_id'], session['selected_bud'], group_id)

        flash('Group name updated', 'success')
        return redirect(url_for('index'))



    """ Deactivate Group """
    if usage == 'group_del':
        # Get group_id
        group_id = request.form.get("group_id")

        # Get all cat_ids for the group
        CATS = db.execute("SELECT * FROM cats WHERE user_id = ? AND bud_id = ? AND group_id = ?", session['user_id'], session['selected_bud'], group_id)

        # Set all of the groups cats to inactive
        for cat in CATS:
            db.execute("UPDATE cats SET active = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", 0, session['user_id'], session['selected_bud'], cat['cat_id'])

        # Set active_cats in groups table to 0
        db.execute("UPDATE groups SET active_cats = (active_cats - ?) WHERE user_id = ? AND bud_id = ? AND group_id = ?", 0, session['user_id'], session['selected_bud'], group_id)

        # Set group to inactive
        db.execute("UPDATE groups SET active = ? WHERE user_id = ? AND bud_id = ? AND group_id = ?", 0, session['user_id'], session['selected_bud'], group_id)

        flash('Group deactivated', 'success')
        return redirect(url_for('index'))


    return redirect(url_for('index'))



""" ---------- G O A L   C H E C K ------------------------------------------------------------------------------------------ """
@app.route('/goal_check')
@login_required
def goal_check():

    """ The actual goal resetting occurs in the index route (based on the bool value of 'reset' for each cat) so that the data is always revaluated everytime the budget table is displayed """

    # Get user's categories for the selected budget
    CATS = db.execute("SELECT * FROM cats WHERE user_id = ? AND bud_id= ?", session['user_id'], session['selected_bud'])

    # Loop through each category
    for cat in CATS:

        # Check if a due day exists for this cat, if not, skip entirely and set reset to false
        if cat['due_tup_d']:

            # Because my formula to calculate whether a reset is required is: (if current month - goal month > 0 AND current day - goal day > 0), Check if the new year elapsed since goal due day because if so,
            # this is the one exception to the formula, because 1 - 12 !> 0 (Dec to Jan), but the next month has in fact, arrived
            if session['day_tup'][0] == 1 and cat['due_tup_m'] == 12:

                # If so, simply check if today is after the due day
                if session['day_tup'][1] > cat['due_tup_d']:

                    # Reset
                    db.execute("UPDATE cats SET reset = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", 1, session['user_id'], session['selected_bud'], cat['cat_id'])

                else:
                    # Do NOT reset
                    db.execute("UPDATE cats SET reset = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", 0, session['user_id'], session['selected_bud'], cat['cat_id'])

            # This is the formula where the new year-exception is not True
            else:
                # Check if the next month has arrived by subtracting this months numeric value by last months, and checking for > 0
                if (int(session['day_tup'][0]) - int(cat['due_tup_m'])) > 0:

                    # Due day has passed since this month is after the due month, reset.
                    db.execute("UPDATE cats SET reset = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", 1, session['user_id'], session['selected_bud'], cat['cat_id'])

                # Check if the due month is this month
                elif (int(session['day_tup'][0]) - int(cat['due_tup_m'])) == 0:

                    # Check if the due day this month has passed
                    if session['day_tup'][1] > cat['due_tup_d']:

                        # Reset
                        db.execute("UPDATE cats SET reset = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", 1, session['user_id'], session['selected_bud'], cat['cat_id'])

                else:

                    # Check if the due month AND the due day is next month, which would indicate the due date had just been changed to a future date of the current month
                    if ((int(session['day_tup'][0]) < int(cat['due_tup_m'])) and (session['day_tup'][1] < cat['due_tup_d'])):

                        # Change back the due month to the current month and do NOT reset
                        db.execute("UPDATE cats SET cat_due_m = (cat_due_m - ?) WHERE user_id = ? and bud_id = and cat_id = ?", 1, session['user_id'], session['selected_bud'], cat['cat_id'])

                    # Do NOT reset
                    db.execute("UPDATE cats SET reset = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", 0, session['user_id'], session['selected_bud'], cat['cat_id'])

        else:
            # Do NOT reset
            db.execute("UPDATE cats SET reset = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", 0, session['user_id'], session['selected_bud'], cat['cat_id'])

    return redirect(url_for('index'))