------------ USERS TABLE ------------
CREATE TABLE users (
    user_id INTEGER,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    username TEXT,
    password TEXT,
    register_date TEXT,
    subscription INTEGER DEFAULT 0,
    acct_credit REAL DEFAULT 20.00 NOT NULL,
    theme TEXT DEFAULT "NT",
    budgets INTEGER DEFAULT 0,
    selected_bud INTEGER,
    is_first_login INTEGER DEFAULT 1,
    PRIMARY KEY (user_id)
    );

CREATE UNIQUE INDEX users_id_index ON users (user_id);
CREATE INDEX users_first_index ON users (first_name);
CREATE INDEX users_last_index ON users (last_name);


------------ BUDGETS TABLE ------------
CREATE TABLE budgets (
    bud_id INTEGER,
    user_id INTEGER,
    bud_name TEXT,
    total_assets REAL,
    unassigned REAL,
    groups INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1,
    PRIMARY KEY (bud_id),
    FOREIGN KEY (user_id) REFERENCES users (user_id)
    );

CREATE UNIQUE INDEX budgets_id_index ON budgets (bud_id);
CREATE INDEX budgets_user_index ON budgets (user_id);


------------ GROUPS TABLE ------------
CREATE TABLE groups (
    group_id INTEGER,
    bud_id INTEGER,
    user_id INTEGER,
    group_name TEXT,
    group_goal REAL,
    group_spent REAL,
    group_avail REAL,
    cats INTEGER DEFAULT 0,
    active_cats INTEGER DEFAULT 0,
    active INT DEFAULT 1, -- BOOL to indicate deleted or not
    PRIMARY KEY (group_id),
    FOREIGN KEY (bud_id) REFERENCES budgets (bud_id),
    FOREIGN KEY (user_id) REFERENCES users (user_id)
    );

CREATE UNIQUE INDEX groups_id_index ON groups (group_id);
CREATE INDEX groups_user_index ON groups (user_id);
CREATE INDEX groups_bud_index ON groups (bud_id);


------------ CATEGORIES TABLE ------------
CREATE TABLE cats (
    cat_id INTEGER,
    bud_id INTEGER,
    group_id INTEGER,
    user_id INTEGER,
    cat_name TEXT,
    due_tup_m TEXT,
    due_tup_d TEXT,
    cat_goal REAL,
    cat_funded REAL DEFAULT 0.00,
    cat_goal_met INT DEFAULT 0, -- BOOL
    cat_goal_spent INT DEFAULT 0, -- BOOL indicating that goal was met and fully spent
    cat_spent REAL,
    cat_avail REAL,
    cat_cmnt TEXT,
    is_unass INT DEFAULT 0, -- BOOL
    is_deposit INT DEFAULT 0, -- BOOL
    active INT DEFAULT 1, -- BOOL to indicate deleted or not
    reset INT DEFAULT 0, -- BOOL to indicate goal reset required
    PRIMARY KEY (cat_id),
    FOREIGN KEY (bud_id) REFERENCES budgets (bud_id),
    FOREIGN KEY (group_id) REFERENCES groups (group_id),
    FOREIGN KEY (user_id) REFERENCES users (user_id)
    );

CREATE UNIQUE INDEX cats_id_index ON cats (cat_id);
CREATE INDEX cats_user_index ON cats (user_id);
CREATE INDEX cats_bud_index ON cats (bud_id);

------------ TRANSACTIONS TABLE ------------
CREATE TABLE trans (
    trans_id INTEGER,
    bud_id INTEGER,
    group_id INTEGER,
    cat_id INTEGER,
    user_id INTEGER,
    trans_date TEXT,
    trans_type TEXT,
    payee TEXT,
    cat_cnt INTEGER,
    amount REAL,
    flag INTEGER ,
    memo TEXT,
    PRIMARY KEY (trans_id),
    FOREIGN KEY (bud_id) REFERENCES budgets (bud_id),
    FOREIGN KEY (user_id) REFERENCES users (user_id),
    FOREIGN KEY (group_id) REFERENCES groups (group_id),
    FOREIGN KEY (cat_id) REFERENCES cats (cat_id)
    );

CREATE UNIQUE INDEX trans_id_index ON trans (trans_id);
CREATE INDEX trans_user_index ON trans (user_id);
CREATE INDEX trans_bud_index ON trans (bud_id);


------------ ALLOCATIONS TABLE ------------
CREATE TABLE allocs (
    alloc_id INTEGER,
    user_id INTEGER,
    bud_id INTEGER,
    alloc_date TEXT,
    to_cat_id INTEGER,
    to_cat_name TEXT,
    from_cat_name TEXT,
    from_cat_id INTEGER,
    amount REAL,
    memo TEXT,
    PRIMARY KEY (alloc_id),
    FOREIGN KEY (user_id) REFERENCES users (user_id),
    FOREIGN KEY (bud_id) REFERENCES budgets (bud_id)
    );

CREATE UNIQUE INDEX allocs_id_index ON allocs (alloc_id);
CREATE INDEX allocs_user_index ON allocs (user_id);
CREATE INDEX allocs_bud_index ON allocs (bud_id);

------------ PAYEES TABLE ------------
CREATE TABLE payees (
    payee_id INTEGER,
    payee_name TEXT,
    user_id INTEGER,
    bud_id INTEGER,
    last_trans TEXT, -- Date
    trans_vol INTEGER, -- Number of transactions
    spent REAL,
    PRIMARY KEY (payee_id),
    FOREIGN KEY (user_id) REFERENCES users (user_id),
    FOREIGN KEY (bud_id) REFERENCES budgets (bud_id)
    );

CREATE UNIQUE INDEX payees_id_index ON payees (payee_id);
CREATE INDEX payees_user_index ON payees (user_id);
CREATE INDEX payees_bud_index ON payees (bud_id);


-----------------------------------------------------------------------------------------
------- DELETE ALL DATA -----------------------------------------------------------------
-----------------------------------------------------------------------------------------
DELETE FROM users;
DELETE FROM budgets;
DELETE FROM groups;
DELETE FROM cats;
DELETE FROM trans;
DELETE FROM allocs;
DELETE FROM payees;


-- DROP ALL TABLES
DROP TABLE users;
DROP TABLE budgets;
DROP TABLE groups;
DROP TABLE cats;
DROP TABLE trans;
DROP TABLE allocs;
DROP TABLE payees;