"""
database/schema.py

Holds the raw SQL statements used to create the application's tables.
Keeping schema definitions in one place makes the database structure
easy to review and modify without hunting through business logic.
"""

# ------------------------------------------------------------------
# USERS TABLE
# ------------------------------------------------------------------
# Stores application login accounts. Passwords are NEVER stored in
# plain text -- only a bcrypt hash is persisted.
# security_question / security_answer_hash power the "Forgot Password"
# flow without needing an external email service.
CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    username              TEXT NOT NULL UNIQUE,
    email                 TEXT UNIQUE,
    password_hash         TEXT NOT NULL,
    security_question     TEXT,
    security_answer_hash  TEXT,
    created_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

# ------------------------------------------------------------------
# PASSWORDS TABLE
# ------------------------------------------------------------------
# Stores vault entries belonging to a user. `encrypted_password` holds
# a Fernet ciphertext -- the plain password is only ever held in
# memory transiently when the user chooses to reveal/copy it.
CREATE_PASSWORDS_TABLE = """
CREATE TABLE IF NOT EXISTS passwords (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL,
    website             TEXT NOT NULL,
    url                 TEXT,
    username            TEXT,
    email               TEXT,
    encrypted_password  TEXT NOT NULL,
    notes               TEXT,
    category            TEXT NOT NULL DEFAULT 'Other',
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
"""

# Helpful indexes for fast search-as-you-type on the vault screen.
CREATE_PASSWORDS_INDEX_WEBSITE = """
CREATE INDEX IF NOT EXISTS idx_passwords_website ON passwords (website);
"""

CREATE_PASSWORDS_INDEX_CATEGORY = """
CREATE INDEX IF NOT EXISTS idx_passwords_category ON passwords (category);
"""

CREATE_PASSWORDS_INDEX_USER = """
CREATE INDEX IF NOT EXISTS idx_passwords_user_id ON passwords (user_id);
"""

# Predefined categories shown as dropdown options in the UI.
# Users are also free to type a custom category.
DEFAULT_CATEGORIES = [
    "Social",
    "Banking",
    "Education",
    "Gaming",
    "Shopping",
    "Work",
    "Other",
]

# Grouped so database.py can loop through and execute them in order.
ALL_STATEMENTS = [
    CREATE_USERS_TABLE,
    CREATE_PASSWORDS_TABLE,
    CREATE_PASSWORDS_INDEX_WEBSITE,
    CREATE_PASSWORDS_INDEX_CATEGORY,
    CREATE_PASSWORDS_INDEX_USER,
]
