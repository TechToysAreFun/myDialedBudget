import os
import secrets
from PIL import Image
from flask import flash, redirect, render_template, request, session, url_for, Blueprint, current_app
from application import  nav_avatar
from werkzeug.security import check_password_hash, generate_password_hash
from application.helpers import login_required
from application import db

settings = Blueprint('settings', __name__)





""" ---------- S E T T I N G S  ------------------------------------------------------------------------------------------ """
@settings.route('/settings')
@login_required
def settings_route():

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


""" ---------- S E T T I N G S  /  U S A G E ------------------------------------------------------------------------------------------ """
@settings.route('/settings/<usage>', methods=["POST"])
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
        return redirect(url_for('budget.index'))


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
        return redirect(url_for('budget.goal_check'))

    if usage =="edit_payees":
        # Get form inputs
        old_name = request.form.get("old_name")
        payee_id = request.form.get("payee_id")
        new_name = request.form.get("new_name")

        # Check that new name doesn't already exists in this budgets payees
        for payee in db.execute("SELECT * FROM payees WHERE user_id = ? and bud_id = ?", session["user_id"], session["selected_bud"]):
            if new_name == payee['payee_name']:
                flash("That payee name already exists.", "warning")
                return redirect(url_for('settings.settings_route'))

        # Update payee name in payees table
        db.execute("UPDATE payees SET payee_name = ? WHERE user_id = ? AND bud_id = ? AND payee_id = ?", new_name, session["user_id"], session["selected_bud"], payee_id)

        # Update payee name in trans table
        db.execute("UPDATE trans SET payee = ? WHERE user_id = ? AND bud_id = ? AND payee = ?", new_name, session["user_id"], session["selected_bud"], old_name)

        flash('Payee name updated', 'success')
        return redirect(url_for('settings.settings_route'))


    if usage == "group_react":
        # Get group_id
        group_id = request.form.get("group_id")

        # Update group active to True
        db.execute("UPDATE groups SET active = ? WHERE user_id = ? AND bud_id = ? AND group_id = ?", 1, session["user_id"], session["selected_bud"], group_id)

        # Update active to True for all categories in that group
        db.execute("UPDATE cats SET active = ? WHERE user_id = ? AND bud_id = ? AND group_id = ?", 1, session["user_id"], session["selected_bud"], group_id )

        flash("Group and categories reactivated!", "success")
        return redirect(url_for('settings.settings_route'))

    if usage == "cat_react":
        # Get cat_id
        cat_id = request.form.get("cat_id")

        # Update active to True for cat
        db.execute("UPDATE cats SET active = ? WHERE user_id = ? AND bud_id = ? AND cat_id = ?", 1, session["user_id"], session["selected_bud"], cat_id)

        flash("Category reactivated!", "success")
        return redirect(url_for('settings.settings_route'))

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
            return redirect(url_for('settings.settings_route'))

        # Check that new and confirm match
        if new == confirm:
            # Hash new password
            new_hashed = generate_password_hash(new, method='pbkdf2:sha256', salt_length=8)

            # Reset password
            db.execute("UPDATE users SET password = ? WHERE user_id = ?", new_hashed, session['user_id'])
            flash('Password successfully changed', 'success')

        else:
            flash('New passwords do not match', 'danger')

        return redirect(url_for('settings.settings_route'))



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

            return redirect(url_for('settings.settings_route'))

        # Else if no other budgets, return to index
        else:
            # Clear session cookies for selected budget
            session['selected_bud'] = None

            # Clear selected budget in users table
            db.execute("UPDATE users SET selected_bud = ? WHERE user_id = ?", '', session['user_id'])

            flash('Budget successfully deleted', 'success')
            return redirect(url_for('budget.index'))



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
        return redirect(url_for('budget.index'))



    # Update budget name
    if usage == "bud_edit":
        new_bud_name = request.form.get("new_name")

        db.execute("UPDATE budgets SET bud_name = ? WHERE user_id = ? AND bud_id = ?", new_bud_name, session['user_id'], session['selected_bud'])

        flash('Budget name updated', 'success')
        return redirect(url_for('budget.index'))

    
    # Update profile picture
    if usage == "edit_avatar":
        
        # Check that a file extension exists
        if 'avatar_file' not in request.files:
            flash('No file part', 'warning')
            return redirect(url_for('settings.settings_route'))

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
        file_path = os.path.join(current_app.root_path, 'static/avatars', new_name)

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
        i.save(os.path.join(current_app.root_path, 'static/avatars/nav', new_name))

        # Update user's avatar to the new image paths
        db.execute("UPDATE users SET avatar = ? WHERE user_id = ?", os.path.join('static/avatars', new_name), session['user_id'])
        db.execute("UPDATE users SET nav_avatar = ? WHERE user_id = ?", os.path.join('static/avatars/nav', new_name), session['user_id'])

        # Update session for settings page and navbar image
        session['avatar'] = os.path.join('static/avatars', new_name)
        session['nav_avatar'] = os.path.join('static/avatars/nav', new_name)
        global nav_avatar
        nav_avatar = session['nav_avatar']

        # Redirect to settings
        flash('Avatar successfully updated', 'success')
        return redirect(url_for('settings.settings_route'))

