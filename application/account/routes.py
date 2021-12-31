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

account = Blueprint('account', __name__)


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
        session['nav_avatar'] = USER[0]['nav_avatar']

        global nav_avatar
        nav_avatar = session['nav_avatar']

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



""" ---------- L O G O U T ------------------------------------------------------------------------------------------ """
@app.route('/logout')
def logout():

    # Forget the user_id currently logged into the filesystem
    session.clear()

    # Send user back to index, which requires login, which will redirect back to login.html
    return redirect(url_for('index'))
    


""" ---------- E M A I L  R E S E T ------------------------------------------------------------------------------------------ """
@app.route('/reset_pw', methods=['GET', 'POST'])
def reset_request():

        # Get all data from users table for both route methods
        users = db.execute("SELECT * FROM users")
        
        # User clicked on "Forgot Password" button on login page
        if request.method == "GET":
            return render_template('request_reset.html')

        # User submitted email address
        if request.method == "POST":

            # Get email address from form on request_reset.html
            submitted_email = request.form.get('email')

            # Validate that email is in the database
            found = False
            for user in users:
                if submitted_email == user['email']:
                    found = True
                    break
            
            if found == False:
                flash('That email is not registered with an account.', 'warning')
                return render_template('request_reset.html', logged=0)

            else:
                # Email is valid. Get user_id associated with that email
                user_id = db.execute("SELECT * FROM users WHERE email = ?", submitted_email)[0]['user_id']

                # Pass user_id into email function
                send_reset_email(user_id, submitted_email)

                # Let user know that the email is sent then return them to login.html
                flash(f'A reset email has successfully been sent to {submitted_email}', 'success')
                return render_template('login.html', logged=0)
        

@app.route('/reset_pw/<token>', methods=['GET'])
def reset_token(token):

    # User is accessing the page via the link in their email, which also passes the <token> parameter

    # verify_reset_token() returns 'None' if token is invalid or expired
    if not verify_reset_token(token):
        flash('That token is either expired or invalid.', 'warning')
        return render_template('request_reset.html', logged=0)

    else:
        # User has been validated. Pass token to html so that it can be submited via POST back to this route
        return render_template('reset_pw.html', token=token)


@app.route('/submit_reset', methods=['POST'])
def submit_reset():

    token = request.form.get('token')
        
    # Verify token
    if not verify_reset_token(token):
        flash('It appears that your token has expired. Please make another reset request.', 'warning')
        return render_template('request_reset.html', logged=0)

    password = request.form.get('password')
    confirmation = request.form.get('confirmation')

    # Check that new password matches confirmation password
    if password == confirmation:
        # Hash new password
        new_hashed = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)

        # Reset password
        db.execute("UPDATE users SET password = ? WHERE user_id = ?", new_hashed, verify_reset_token(token))
        flash('Password successfully changed', 'success')
        return render_template('login.html', logged=0)

    else:
        flash('New passwords do not match', 'danger')
        return render_template('reset_pw.html', token=token, logged=0)