from flask import Blueprint

transactions = Blueprint('transactions', __name__)


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

         # If user doesn't have a budget yet, alert them and return to index
        if db.execute("SELECT * FROM users WHERE user_id = ?", session['user_id'])[0]['budgets'] < 1:
            flash("You don't have a budget yet. Create one below!", "warning")
            return redirect(url_for('index'))

        # Pass user's payees to the select input
        PAYEES = db.execute("SELECT * FROM payees WHERE user_id = ? AND bud_id = ?", session['user_id'], session['selected_bud'])

        # Extract user's existing categories to pass into html
        CATS = db.execute("SELECT * FROM cats WHERE user_id = ? AND bud_id = ? AND active = ?", session['user_id'], session['selected_bud'], 1)

        return render_template('expense.html', payees=PAYEES, cats=CATS, ptitle='Post Transaction')