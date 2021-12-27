import os
import secrets
from PIL import Image
from flask import flash, redirect, render_template, request, session, url_for
from application import app, nav_avatar
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import datetime
import re
from application.helpers import login_required
from application import db


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


""" ---------- L O G I N ------------------------------------------------------------------------------------------ """

@app.route('/login', methods=['GET', 'POST'])
def login():

    # Clear the existing user_id
    session.clear()

    if request.method == "POST":
        # Extract inputs into variables
        username = request.form.get("username")
        password = request.form.get("password")

        # Set an indicator showing whether the user is logged in, telling the flashed messaged which format to show in
        logged = 0

        # Validate that a username and a password were entered
        if not username:
            flash('Username field empty', 'danger')
            return render_template('login.html', logged=logged, ptitle='Login')

        if not password:
            flash('Password field empty', 'danger')
            return render_template('login.html', logged=logged, ptitle='Login')

        # Query username and password from Users table
        USER = db.execute("SELECT * FROM users WHERE username = ?", username)

        # Check that username exists
        found = 'none'
        for users in USER:
            if username == users['username']:
                found = users['username']
                break

        exists = False
        if found.lower() == username.lower():
            exists = True


        if not exists:
            flash('Incorrect username', 'danger')
            return render_template('login.html', logged=logged, ptitle='Login')

        # Check that password is correct
        if not check_password_hash(USER[0]['password'], password):
                flash('Invalid passworrd', 'danger')
                return render_template('login.html', logged=logged, ptitle='Login')

        """ All credentials match. Proceed to log user in. """
        
        # Indicate the layout format for flashed messages to use
        logged = 1

        # Set session cookies
        session['user_id'] = USER[0]['user_id']
        session['selected_bud'] = USER[0]['selected_bud']
        session['day_tup'] = (datetime.datetime.now().strftime("%m"), datetime.datetime.now().strftime("%d"))
        session['avatar'] = USER[0]['avatar']

        # Redirect user to homepage (index)
        if db.execute("SELECT * FROM users WHERE user_id = ?", session['user_id'])[0]['is_first_login'] == 1:
            db.execute("UPDATE users SET is_first_login = ? WHERE user_id = ?", 0, session['user_id'])
            flash('Welcome to Budget Buddy! Thank you for demoing my first fully-functioning web application! <3', 'success')
        else:
            name = db.execute("SELECT * FROM users WHERE user_id = ?", session['user_id'])[0]['first_name']
            flash(f'Hello, {name}!', 'primary')

        return redirect(url_for('index'))

    else:
        return render_template('login.html', session=session, ptitle='Login')


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



""" ---------- R E G I S T E R ------------------------------------------------------------------------------------------ """
@app.route('/register', methods=["GET", "POST"])
def register():

    if request.method == "POST":

        # Set an indicator showing whether the user is logged in, telling the flashed messaged which format to show in
        logged = False

        # Store form inputs into variables
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Validate that all fields received values
        if not first_name or not last_name or not email or not username or not password:
            flash('Please complete all fields', 'warning')
            return render_template('register.html', logged=logged, ptitle='Register')

        # Make sure username is unique
        for user in db.execute("SELECT * FROM users"):
            if username == user['username']:
                flash('Username already taken', 'warning')
                return render_template('register.html', logged=logged, ptitle='Register')

        # Validate that passwords match
        if password != confirmation:
            flash('Passwords do not match', 'warning')
            return render_template('register.html', logged=logged, ptitle='Register')

        # Use REGEX to validate email
        regex = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z|A-Z]{2,}\b'
        if not re.fullmatch(regex, email):
            flash('Invalid email', 'warning')
            return render_template('register.html', logged=logged, ptitle='Register')

        # Make sure email hasn't already been used
        for user in db.execute("SELECT * FROM users"):
            if email == user['email']:
                flash('An account is already registered under that email', 'warning')
                return render_template('register.html', logged=logged, ptitle='Register')


        # Hash password
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)

        # Generate the current date
        register_date = datetime.datetime.now().strftime("%m/%d/%Y")

        # Insert user into users table
        db.execute("INSERT INTO users (first_name, last_name, email, username, password, register_date) VALUES (?, ?, ?, ?, ?, ?)", first_name, last_name, email, username, hashed_pw, register_date)

        # Redirect to index
        flash('Registration successful!', 'success')
        return render_template('login.html', logged=logged, ptitle='Login')

    if request.method == "GET":
        return render_template('register.html', ptitle='Register')


""" ---------- E X P E N S E ------------------------------------------------------------------------------------------ """
@app.route('/expense', methods=["GET", "POST"])
@login_required
def expense():

    if request.method == "POST":
        """ Extract and validate form responses """
        # Extract form inputs into variables
        amount = float(request.form.get("amount"))
        payee = request.form.get("payee")
        cat = request.form.get("cat")
        date = str(request.form.get("trans_date"))
        note = request.form.get("memo")

        # Validate that all required fields were populated
        if not amount or not payee or not cat or not date:
            flash('Please complete all required fields', 'warning')
            return redirect(url_for('expense'))

        # Convert cat_name into cat_id
        cat_id = db.execute("SELECT * FROM cats WHERE cat_name = ? AND user_id = ?", cat, session['user_id'])[0]['cat_id']

        # Check for sufficient funds in category
        CATS = db.execute("SELECT * FROM cats WHERE user_id = ? AND bud_id = ? AND cat_id = ?", session['user_id'], session['selected_bud'], cat_id)
        cat_avail = CATS[0]['cat_avail']
        if amount > cat_avail:
            required = amount - cat_avail
            # The following.   "{:.2f}".format()     formats a python float with 2 decilal points
            flash(f'Insufficient funds: ${"{:.2f}".format(required)} more needed in {cat}', 'danger')
            return redirect(url_for('expense'))

        # First check if the cat goal has been fully funded
        goal_spent = CATS[0]['cat_goal_spent']
        funded = CATS[0]['cat_goal_met']
        if funded == 1:
            # Then check if the cat goal has been fully spent
            if cat_avail - amount == 0:
                goal_spent = 1

        # If no memo entered, show a blank rather than 'None'
        if not note:
            note = ''

        """ Update, &/or add to, payees table """
        # Get payees table from database
        PAYEES = db.execute("SELECT * FROM payees WHERE user_id = ? AND bud_id = ?", session['user_id'], session['selected_bud'])

        check = False
        # Add payee to table if they don't already exist
        for row in PAYEES:
            if payee == row['payee_name']:
                # Update existing payee
                db.execute("UPDATE payees SET last_trans = ?, trans_vol = (trans_vol + ?), spent = (spent + ?) WHERE user_id = ? AND bud_id = ?", date, 1, amount, session['user_id'], session['selected_bud'])
                check = True
                break

        if not check:
            # Add payee to payees table
            db.execute("INSERT INTO payees (payee_name, user_id, bud_id, last_trans, trans_vol, spent) VALUES (?, ?, ?, ?, ?, ?)", payee, session['user_id'], session['selected_bud'], date, 1, amount)



        """ Update cats, trans, budgets, and groups tables """
        # Determine category group_id for reference in the remaining queries
        group_id = db.execute("SELECT * FROM cats WHERE cat_name = ? AND user_id = ?", cat, session['user_id'])[0]['group_id']

        # Update cats table
        db.execute("UPDATE cats SET cat_spent = (cat_spent + ?), cat_avail = (cat_avail - ?), cat_goal_spent = ? WHERE cat_id = ? AND user_id = ?", amount, amount, goal_spent, cat_id, session['user_id'])

        # Insert transaction into trans table
        db.execute("INSERT INTO trans (bud_id, user_id, group_id, cat_id, trans_date, trans_type, payee, amount, memo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", session['selected_bud'], session['user_id'], group_id, cat_id, date, 'expense', payee, amount, note)

        # Update budgets table for 'total_assets'
        db.execute("UPDATE budgets SET total_assets = (total_assets - ?) WHERE bud_id = ? AND user_id = ?", amount, session['selected_bud'], session['user_id'])

        # Update groups table
        db.execute("UPDATE groups SET group_spent = (group_spent + ?), group_avail = (group_avail - ?) WHERE group_id = ? AND user_id = ?", amount, amount, group_id, session['user_id'])


        return redirect(url_for('index'))


    if request.method == "GET":

        # Pass user's payees to the select input
        PAYEES = db.execute("SELECT * FROM payees WHERE user_id = ? AND bud_id = ?", session['user_id'], session['selected_bud'])

        # Extract user's existing categories to pass into html
        CATS = db.execute("SELECT * FROM cats WHERE user_id = ? AND bud_id = ? AND active = ?", session['user_id'], session['selected_bud'], 1)

        return render_template('expense.html', payees=PAYEES, cats=CATS, ptitle='Post Transaction')


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
        # Extract user's cats and feed to html form
        CATS = db.execute("SELECT * FROM cats WHERE user_id = ? AND bud_id = ? AND active = ?", session['user_id'], session['selected_bud'], 1)

        return render_template('allocate.html', cats=CATS, ptitle='Allocate Funds')



""" ---------- T R A N S A C T I O N S ------------------------------------------------------------------------------------------ """
@app.route ('/transactions')
@login_required
def transactions():

    # Get user's transaction history and join to cats to know whether the cat is active and indicate that in the tables
    TRANS = db.execute("SELECT * FROM trans JOIN cats ON trans.cat_id = cats.cat_id WHERE trans.user_id = ? AND trans.bud_id = ? ORDER BY trans_date DESC", session['user_id'], session['selected_bud'])

    # Get user's allocations history
    ALLOCS = db.execute("SELECT * FROM allocs WHERE user_id = ? AND bud_id = ? ORDER BY alloc_date DESC", session['user_id'], session['selected_bud'])

    # Get user's cats to reference active status in allocs
    CATS = db.execute("SELECT * FROM cats WHERE user_id = ? AND bud_id = ?", session['user_id'], session['selected_bud'])

    return render_template('transactions.html', trans=TRANS, allocs=ALLOCS, cats=CATS, ptitle='Transaction History')



""" ---------- S E T T I N G S  /  U S A G E ------------------------------------------------------------------------------------------ """
@app.route('/settings/<usage>', methods=["POST"])
@login_required
def settings_usage(usage):

    if usage == "new_bud":

        # See if user currently has a budget. If so, switch it's active status to 0 (false)
        if db.execute("SELECT * FROM users WHERE user_id = ?", session['user_id'])[0]['budgets'] > 0:
            db.execute("UPDATE budgets SET active = ? WHERE user_id = ? AND bud_id = ?", 0, session['user_id'], session['selected_bud'])

        # New budgets are created with a default active status of 0 (true)

        # Get budget name and assets
        bud_name = request.form.get("bud_name")
        total_assets = float(request.form.get("total_assets"))

        # Create a new budget in the budgets table
        db.execute("INSERT INTO budgets (user_id, bud_name, total_assets, unassigned) VALUES (?, ?, ?, ?)", session['user_id'], bud_name, total_assets, total_assets)

        # Update user's cookies for the new budget
        session['selected_bud'] = db.execute("SELECT * FROM budgets WHERE user_id = ? AND bud_name = ?", session['user_id'], bud_name)[0]['bud_id']

        # Create 'unassigned' and 'deposit' categories in the new budget that are not part of a group
        db.execute("INSERT INTO cats (bud_id, user_id, cat_name, is_deposit) VALUES (?, ?, ?, ?)", session['selected_bud'], session['user_id'], 'Deposit', 1)
        db.execute("INSERT INTO cats (bud_id, user_id, cat_name, cat_spent, cat_avail, is_unass) VALUES (?, ?, ?, ?, ?, ?)", session['selected_bud'], session['user_id'], 'Unassigned', 0, total_assets, 1)

        # Set selected_bud in users table to the id of the new budget
        db.execute("UPDATE users SET selected_bud = ? WHERE user_id = ?", session['selected_bud'], session['user_id'])

        # Update user's budget count
        db.execute("UPDATE users SET budgets = (budgets + ?) WHERE user_id = ?", 1, session['user_id'])

        flash(f"{bud_name} successfully created", "success")
        return redirect(url_for('index'))


    if usage == "switch":
        # Get new bud_id and bud_name
        new_bud_id = request.form.get("budget")
        bud_name = db.execute("SELECT * FROM budgets WHERE user_id = ? AND bud_id = ?", session["user_id"], new_bud_id)[0]["bud_name"]

        # Switch old budgets active column in budgets to false
        db.execute("UPDATE budgets SET active = ? WHERE bud_id = ?", 0, session['selected_bud'])

        # Update user's cookies
        session['selected_bud'] = new_bud_id

        # Switch new budgets 'active' culumn in budgets to true
        db.execute("UPDATE budgets SET active = ? WHERE bud_id = ?", 1, session['selected_bud'])

        # Update user's selected_bud in users table
        db.execute("UPDATE users SET selected_bud = ? WHERE user_id = ?", session['selected_bud'], session['user_id'])

        flash(f"Switched to {bud_name}", "success")
        return redirect(url_for('goal_check'))

    if usage =="edit_payees":
        # Get form inputs
        old_name = request.form.get("old_name")
        payee_id = request.form.get("payee_id")
        new_name = request.form.get("new_name")

        # Check that new name doesn't already exists in this budgets payees
        for payee in db.execute("SELECT * FROM payees WHERE user_id = ? and bud_id = ?", session["user_id"], session["selected_bud"]):
            if new_name == payee['payee_name']:
                flash("That payee name already exists.", "warning")
                return redirect(url_for('settings'))

        # Update payee name in payees table
        db.execute("UPDATE payees SET payee_name = ? WHERE user_id = ? AND bud_id = ? AND payee_id = ?", new_name, session["user_id"], session["selected_bud"], payee_id)

        # Update payee name in trans table
        db.execute("UPDATE trans SET payee = ? WHERE user_id = ? AND bud_id = ? AND payee = ?", new_name, session["user_id"], session["selected_bud"], old_name)

        flash('Payee name updated', 'success')
        return redirect(url_for('settings'))


    if usage == "group_react":
        # Get group_id
        group_id = request.form.get("group_id")

        # Update group active to True
        db.execute("UPDATE groups SET active = ? WHERE user_id = ? AND bud_id = ? AND group_id = ?", 1, session["user_id"], session["selected_bud"], group_id)

        # Update active to True for all categories in that group
        db.execute("UPDATE cats SET active = ? WHERE user_id = ? AND bud_id = ? AND group_id = ?", 1, session["user_id"], session["selected_bud"], group_id )

        flash("Group and categories reactivated!", "success")
        return redirect(url_for('settings'))

    if usage == "cat_react":
        # Get cat_id
        cat_id = request.form.get("cat_id")

        # Update active to True for cat
        db.execute("UPDATE cats SET active = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", 1, session["user_id"], session["selected_bud"], cat_id)

        flash("Category reactivated!", "success")
        return redirect(url_for('settings'))

    if usage == "pw_reset":
        # Get user input for existing pw, new pw, and confirmation
        old = request.form.get("old")
        new = request.form.get("new")
        confirm = request.form.get("confirm")

        # Get users information
        USER = db.execute("SELECT * FROM users WHERE user_id = ?", session['user_id'])

        # Check that old password matches the existing password
        if not check_password_hash(USER[0]['password'], old):
            flash('Incorrect password', 'danger')
            return redirect(url_for('settings'))

        # Check that new and confirm match
        if new == confirm:
            # Hash new password
            new_hashed = generate_password_hash(new, method='pbkdf2:sha256', salt_length=8)

            # Reset password
            db.execute("UPDATE users SET password = ? WHERE user_id = ?", new_hashed, session['user_id'])
            flash('Password successfully changed', 'success')

        else:
            flash('New passwords do not match', 'danger')

        return redirect(url_for('settings'))



    if usage == "bud_delete":
        # Get budget id
        bud_id = int(request.form.get("budget"))

        # Update user's budget count in users table
        db.execute("UPDATE users SET budgets = (budgets - ?) WHERE user_id = ?", 1, session['user_id'])

        # Delete all allocations in the budget
        db.execute("DELETE FROM allocs WHERE user_id = ? AND bud_id = ?", session['user_id'], bud_id)

        # Delete all transactions in the budget
        db.execute("DELETE FROM trans WHERE user_id = ? AND bud_id = ?", session['user_id'], bud_id)

        # Delete all categories in the budget
        db.execute("DELETE FROM cats WHERE user_id = ? AND bud_id = ?", session['user_id'], bud_id)

        # Delete all groups in the budget
        db.execute("DELETE FROM groups WHERE user_id = ? AND bud_id = ?", session['user_id'], bud_id)

        # Delete all payees in the budget
        db.execute("DELETE FROM payees WHERE user_id = ? AND bud_id = ?", session['user_id'], bud_id)

        # Delete budget
        db.execute("DELETE FROM budgets WHERE user_id = ? AND bud_id = ?", session['user_id'], bud_id)

        # Switch to another budget if exists and return to /settings
        if db.execute("SELECT * FROM users WHERE user_id = ?", session['user_id'])[0]['budgets'] > 0:
            new_bud = db.execute("SELECT * FROM budgets WHERE user_id = ?", session['user_id'])

            # Update session
            session['selected_bud'] = new_bud[0]['bud_id']

            # Update user's selected budget
            db.execute("UPDATE users SET selected_bud = ? WHERE user_id = ?", session['selected_bud'], session['user_id'])

            # Set the budget to active
            db.execute("UPDATE budgets SET active = ? WHERE user_id = AND bud_id = ?", 1, session['user_id'], session['selected_bud'])

            flash(f'Budget successfully deleted. Switched to: {new_bud[0]["bud_name"]}', 'success')

            return redirect(url_for('settings'))

        # Else if no other budgets, return to index
        else:
            # Clear session cookies for selected budget
            session['selected_bud'] = None

            # Clear selected budget in users table
            db.execute("UPDATE users SET selected_bud = ? WHERE user_id = ?", '', session['user_id'])

            flash('Budget successfully deleted', 'success')
            return redirect(url_for('index'))



    if usage == "bud_reset":
        # Get budget id
        bud_id = int(request.form.get("budget"))

        # Delete all transactions
        db.execute("DELETE FROM trans WHERE user_id = ? AND bud_id = ?", session['user_id'], bud_id)

        # Delete all allocations
        db.execute("DELETE FROM allocs WHERE user_id = ? AND bud_id = ?", session['user_id'], bud_id)

        # RESET categories while retaining id, name, user, due_month (because this is never shown and is used in goal checking & resetting) budget & group associations, type (deposit/unassigned), and 'active' status
        db.execute("UPDATE cats SET due_tup_d = ?, cat_goal = ?, cat_funded = ?, cat_goal_met = ?, cat_goal_spent = ?, cat_spent = ?, cat_avail = ?, cat_cmnt = ?, reset = ? WHERE user_id = ? AND bud_id = ?", '', 0.00 , 0.00, 0, 0, 0.00, 0.00, '', 1, session['user_id'], bud_id)

        # RESET groups while retaining id, name, user, budget association, amount of categories, and 'active' status
        db.execute("UPDATE groups SET group_goal = ?, group_spent = ?, group_avail = ? WHERE user_id = ? AND bud_id = ?", 0.00, 0.00, 0.00, session['user_id'], bud_id)

        # RESET payees while retaining id, name, user, and budget association
        db.execute("UPDATE payees SET last_trans = ?, trans_vol = ?, spent = ? WHERE user_id = ? AND bud_id = ?", '', 0, 0.00, session['user_id'], bud_id)

        # RESET budgets while retaining id, user id, name, etc.
        db.execute("UPDATE budgets SET total_assets = ?, unassigned = ? WHERE user_id = ? AND bud_id = ?", 0.00, 0.00, session['user_id'], session['selected_bud'])


        # Get budget name to flash
        bud_name = db.execute("SELECT * FROM budgets WHERE user_id = ? AND bud_id = ?", session['user_id'], bud_id)[0]['bud_name']

        flash(f'{bud_name} successfully reset!', 'success')
        return redirect(url_for('index'))



    # Update budget name
    if usage == "bud_edit":
        new_bud_name = request.form.get("new_name")

        db.execute("UPDATE budgets SET bud_name = ? WHERE user_id = ? AND bud_id = ?", new_bud_name, session['user_id'], session['selected_bud'])

        flash('Budget name updated', 'success')
        return redirect(url_for('index'))

    
    # Update profile picture
    if usage == "edit_avatar":
        
        # Check that a file extension exists
        if 'avatar_file' not in request.files:
            flash('No file part', 'warning')
            return redirect(url_for('settings'))

        # Receive user's uploaded file from the form
        avatar = request.files['avatar_file']

        # Check that a file was selected before submission (The browser submits an empty filename if not)
        if avatar.filename == '':
            flash('No file selected')
            return redirect(request.url)

        # Extract file extension
        _, f_ext = os.path.splitext(avatar.filename)

        #Create random hex code for new filename
        random_hex = secrets.token_hex(8)
        
        # Concat hex code to file extension
        new_name = random_hex + f_ext

        # Concat the root path and file location to the new file
        file_path = os.path.join(app.root_path, 'static/avatars', new_name)

        # Set resizing for settings page display and navbar display
        output_size = (125, 125)
        nav_size = (40, 40)
        
        # Open original image and resize it
        i = Image.open(avatar)
        i.thumbnail(output_size)

        # Save resized image with newly rendered filepath
        i.save(file_path)

        # Resize and save for navbar
        i.thumbnail(nav_size)
        i.save(os.path.join(app.root_path, 'static/avatars/nav', new_name))

        # Update user's avatar to the new image paths
        db.execute("UPDATE users SET avatar = ? WHERE user_id = ?", os.path.join('static/avatars', new_name), session['user_id'])
        db.execute("UPDATE users SET nav_avatar = ? WHERE user_id = ?", os.path.join('static/avatars/nav', new_name), session['user_id'])

        # Update session for settings page image
        session['avatar'] = os.path.join('static/avatars', new_name)

        # Set global variable for navbar image since this needs to be passed to layout.html, which is never called via render_template
        global nav_avatar
        nav_avatar = os.path.join('static/avatars/nav', new_name)
        
        # Redirect to settings
        flash('Avatar successfully updated', 'success')
        return redirect(url_for('settings'))



""" ---------- S E T T I N G S  ------------------------------------------------------------------------------------------ """
@app.route('/settings')
@login_required
def settings():

    # Get all information from users table
    USERS = db.execute("SELECT * FROM users WHERE user_id = ?", session['user_id'])
    
    # Determine if the user has any budgets
    if USERS[0]['budgets'] >= 1:

        # Get user's budgets
        BUDGETS = db.execute("SELECT * FROM budgets WHERE user_id = ?", session['user_id'])

        # Get user's payees and order alphabetically
        PAYEES = db.execute("SELECT * FROM payees WHERE user_id = ? AND bud_id = ? ORDER BY payee_name ASC", session['user_id'], session['selected_bud'])

        # Get user's deactivated groups
        GROUPS = db.execute("SELECT * FROM groups WHERE user_id = ? AND bud_id = ? AND active = ?", session['user_id'], session['selected_bud'], 0)

        # Get user's deactivated categories that are in deactivated groups
        CATSinc = db.execute("SELECT * FROM cats JOIN groups ON cats.group_id = groups.group_id WHERE cats.user_id = ? AND cats.bud_id = ? AND cats.active = ? AND groups.active = ?", session['user_id'], session['selected_bud'], 0, 0)

        # Get user's deactivated cats that are not in deactivated groups
        CATSex = db.execute("SELECT * FROM cats JOIN groups ON cats.group_id = groups.group_id WHERE cats.user_id = ? AND cats.bud_id = ? AND cats.active = ? AND groups.active = ?", session['user_id'], session['selected_bud'], 0, 1)
    

        return render_template('settings.html', budgets=BUDGETS, payees=PAYEES, groups=GROUPS, catsinc=CATSinc, catsex=CATSex, users=USERS, ptitle='Account Settings', avatar=session['avatar'])

    return render_template('settings.html', users=USERS, ptitle='Account Settings', avatar=session['avatar'])


""" ---------- L O G O U T ------------------------------------------------------------------------------------------ """
@app.route('/logout')
def logout():

    # Forget the user_id currently logged into the filesystem
    session.clear()

    # Send user back to index, which requires login, which will redirect back to login.html
    return redirect(url_for('index'))


""" ---------- N A V   B A R   A V A T A R  ----------"""

@app.context_processor
def context_processor():
    global nav_avatar
    return dict(avatar_key=nav_avatar )