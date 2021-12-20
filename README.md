# Budget Buddy
## CS50 2021 | Final Project | Matt Hart
### [Video Demo](https://youtube.com)

## Overview

My final project for CS50x is a budgeting tool inspired by the design of [You Need A Budget](www.youneedabudget). My objective with this project
was to push my limits and create as much functionality as possible within a month. While I had aimed to incorporate Jquery and Ajax, that proved to be a challenge for the next project. This application runs on the following technologies:

#### FRAMEWORKS
    - Flask (with Jinja2 template engine)
    - Bootstrap

#### LANGUAGES
    - Python
    - SQLite
    - Javascript
    - HTML
    - CSS
    - Regex

#### LIBRARIES
    - cs50
    - flask
    - flask-session
    - os
    - requests
    - tempfile
    - werkzeug
    - re
    - functools

As wells as icons by [Font Awesome](https://fontawesome.com/)

My ability to learn these technologies and develop this application are almost entirely attributed to the first 6 weeks of CS50x,
which are spent learning fundamental CS concepts using C; a small sample of which are as follows:
    - Abstraction
    - Code *correctness* vs. *design* and *eloquence/readability*
    - Conditional statements
    - Looping, iteration techniques, and sub-looping
    - Functions
    - Recurson (Built a Tideman election in C)
    - Arrays, Dictionaries, Linked Lists, Trees, Tries
    - Memory allocation and debugging with Valgrind
    - File reading, writing, and appending
    - CSV reading and writing
    - Hashing
    - Using browser developer tools for debugging and monitoring


I am proud to present this project as a demonstration of my new skills in computational thinking, asking better questions, and best of all, learning how to learn.
This documentation outlines the fundamental concepts behind developing a web app, a high-level guide to navigating the code, and a recap on my educational experience.
Thank you sincerely for your time and interest.


### Python | IP | TCP | HTTP
The application leverages 9 static and 2 dynamic HTTP routes with 15 subroutes. All requests are made
via *GET* or *POST* with responses delivered using *redirect* or *render_template* and are accompanied by
*flashed* messages for key events. There are a total of 8 HTML pages:
    - Layout (Template page)
    - Account registration
    - Login page
    - Index (Budget page)
    - Posting expenses
    - Posting allocations
    - History of all expenses and allocations
    - Settings page

In order to develop a fully functioning web application within the parameters of the course's teachings, I have used part of the CS50x
Week 9 project, Finance, source code in the first 42 lines of my Python code. This source code performs 3 primary functions:

1. Configure the server to auto-update whenever changes are made within the flask framework (application.py, static files, and/or templates)
2. Prevents response headers from being cached
3. Configures the session to my own filesystem rather than signed cookies (So that I can easily store/retrieve into/from my SQLite database)

The first 42 lines also contains code that I, however, am comfortable with, but are nearly identical due to the Flask framework protocol:

1. Importing libraries
2. Connecting to the SQLite database
3. Configuring the Flask app

In addition to these 42 lines is a *helpers.py* file from which 2 functions are used from the CS50x Finance source code.

1. login_required(f)
       - Called upon as the first function within every route that requires the user to be logged in to run by checking if the *user_id* has been stored in the session cookies
2. usd(value)
       - Performs Jinja2 formating on integers and floats/reals into a 2-decimal dollar-currency

Aside from these two crutches, the remaining 958 lines of Python, 924 lines of HTML, proprietary CSS file, all Javascript, and the entire
SQLite database are original code and of my own design.


### CSS | Javascript | Design
For this project I used Bootstrap, CSS, and Javascript. Most of the CSS is provided via Bootstrap, although I added some personal touches in my own file.
With the exception of *login.html* and *register.html*, each HTML page processes a variety of conditional statements and loops using Jinja2 syntax.
In doing so, they are able to generate dynamic content and formatting based on data extracted via SQLite queries within my Python code.
The Javascrip is original and contains only 2 functions. The first is an interating display toggle that I built that allows me to send up to 6 IDs at a time, switching
the display property between "none" and "", depending on the element's value upon entry.

The second function interacts with the category lines in the budget table and uses data regarding the category's financial goal, goal due date, available funds,
and amount funded since the last due date as arguments. This proved to be one of the more challenging objectives in replicating [YNAB's](www.youneedabudget) design.
It performs the following:

1. Toggle the available funds column background color in the main budget table between green, yellow, grey, and none
2. Display a check mark icon when the category is fully funded
   - Turns green when fully funded
   - Remains green as the funds are spent (Goals are based on the assumption that category funds are allocated for spending in that particular area rather than saving)
     - A "savings" goal would simply compound the "available" funds while resetting the "funded" amount per period to 0 upon the passing of each due day
   - Back to yellow if funds are allocated *away* from the category to another category, effectively reducing the funded amount to that goal
   - Grey when a fully funded category's funds are fully spent
3. Display a green money symbol button when a category is not fully funded that when clicked, fully funds the category goal


### SQLite Database
This was my second database design (CS50x Finance being the first). During concept generation, I spent a great deal of time wireframing my HTML pages
and HTTP routes. Doing so helped me generate my UX and flow charts and gave me a greater understanding of all the data that I would need to store, as well
as when and where that data would be created, referenced, and updated. My initial design started small, but as the project developed, some tables were deleted,
some were created, and many columns added as my understanding of data relationships grew.

#### My design uses a single database with 7 tables:
1. Users
2. Budgets
3. Budget Groups
4. Group Categories
5. Transactions
6. Allocations
7. Payees

#### All of which contain at least 1 unique index and 1 standard index and are joined together using 4 foreign keys:
1. User ID
2. Budget ID
3. Budget Group ID
4. Group Category ID

For future projects, I am eager to explore designs that dynamically generate new tables for major elements, such as users.

To mitigate against SQL injection attacks, every SQLite query was written uses prepared statements.


## Route Documentation

### Index
#### GET Only
    1. Determine if user has any budgets
    2. What budget the user was viewing during their last session
    3. Perform category goal resets based on due date
       - Updates due month, funded amount, and goal_met bool
    4. Extract user's current budget, groups, and categories


### Index / Usage
#### POST Only
    1. Add budget groups
    2. Add categories for each group
       - Name
       - Goal
       - Goal due day
    3. Edit categories
       - Name
       - Goal
       - Due day
       - Remove goal &/or due day
       - Redirect to "goal_check" route to determine if a reset is warranted
    4. Deactivate categories
       - Still shows in transaction/allocation history tables and is indicated as inactive
    5. Deactivate groups
       - Also deactivates all categories within the group


### Login
#### POST
    1. Validate that username exists in *users* table
    2. Uses Werkzeug utility to validate hashed password
    3. Set session cookies into filesystem
    4. Welcome first-time users with unique flashed message
    5. Welcome revisiting users by their first name

#### GET
    1. Render template


### Goal Check
#### POST Only
    The Goal Check route determines whether a reset is needed and updates due dates. Goal resetting is then performed within the Index route, allowing multiple routes to schedule a goal for a reset, while isolating the execution itself to a single route.
    1. Loop through each category in the budget
    2. Check if a due *day* exists
    3. Check if goal due day and month has passed
    4. Iterate due *month* if passed
    5. Check effects of due day edits
    6. Update category "reset" SQLite field to True or False
    7. Redirect to Index route


### Register
#### POST
    1. Request and validate first & last name, email, username, password, & pw confirmation
       - Use Regex to validate email
       - Make sure username and email don't already exist in the database
    2. Hash the user's password using the Werkzeug utility
    3. Render registration date using datetime library
    4. Create user in *user* table

#### GET
    1. Render template


### Expense
#### POST
    1. Request and validate expense amount, payee, category, date, and note/memo
    2. Check for sufficient funds in category
    3. Check if category has bee fully funded
    4. Check if category has been fully spent as a result of the transaction
    5. Add payee to *payees* table if payee is new
    6. If payee exists, update payee's transaction count, total spent, and last (this) transaction date
    7. Update budgets, groups, categories, and transactions tables

#### GET
    1. Pass user's payees and categories to the HTML form


### Allocate
#### POST
    1. Request and validate To & From categories, note/memo, and date
    2. Set allocation amount
       - Check if the request is coming from allocate.html or from the "fully fund" money symbol displayed next to category names
       - If symbol: calculate how much is needed to fully fund
       - Otherwise set amount to user input from allocate.html
    3. Treat *Deposit*, *Unassigned*, and *other category* with separate data validations and updates
       - If From category To another category, determine if the allocation removes the From category's "fully funded" status
    4. Determine if To category becomes fully funded
    5. Depending on the above conditions, update:
       - Total assets, unassigned funds, fully funded status, and/or available funds

#### GET
    1. Render template


### Transactions (History)
#### GET
    1. Get user's transaction and allocation history for the current budget
    2. Get user's category "active/disabled" status
    3. Render template


### Settings / Usage
#### POST
    1. Create new budget
       - Update session cookies
       - Create *Unassigned* and *Deposit* categories in the budget for processing and holding externally deposited and unallocated funds
       - Update user's budget count
    2. Switch between budgets
       - Almost every SQLite query in Python references the session cookie for the user's selected budget
       - Simply update this and the "selected_bud" field in the users table
    3. Delete budgets
       - Full send
    4. Reset budgets
       - Retaining groups, categories, and payees
       - Deleting all allocations, transactions, goals, etc.
       - (Mostly awesome for me because I'm a newb at debugging and now I don't have to DELETE FROM or DROP all of my tables every 5 min XD)
    3. Edit payees
    4. Reactivate individual group categories
       - Displays again in the budget table
       - Shows as active in transaction/allocation history tables
    5. Reactivate entire budget groups and their categories
       - Same as above
    6. Reset password
       - Similar to Login route
    7. Most subroutes redirect to /settings


### Settings
#### GET
    1. Select from database:
       - Budgets
       - Payees
       - Deactivated groups and their categories
       - Deactivated categories that are in active groups
       - User information
    2. Redirect to /index

### Logout
    1. Clear session files
    2. Redirect to /index

