"""
auth/register.py

Handles creation of new user accounts, including the very first
"admin" account created on first launch of the app.
"""

import logging
import sqlite3

from auth.security import hash_password, is_non_empty, is_strong_password, is_valid_email
from database.database import Database

logger = logging.getLogger(__name__)


class RegistrationError(Exception):
    """Raised for any validation/uniqueness failure during registration."""


def has_any_user(db: Database) -> bool:
    """Used by the UI to decide whether to show the 'Create admin
    account' first-run screen or the normal login/register screen."""
    row = db.fetchone("SELECT COUNT(*) AS count FROM users;")
    return row["count"] > 0


def register_user(
    db: Database,
    username: str,
    email: str,
    password: str,
    confirm_password: str,
    security_question: str,
    security_answer: str,
) -> int:
    """
    Validates input and inserts a new user row.
    Returns the new user's id on success.
    Raises RegistrationError with a human-readable message on failure.
    """
    username = username.strip()
    email = email.strip()

    if not is_non_empty(username):
        raise RegistrationError("Username is required.")
    if not is_non_empty(email) or not is_valid_email(email):
        raise RegistrationError("Please enter a valid email address.")
    if password != confirm_password:
        raise RegistrationError("Passwords do not match.")
    ok, message = is_strong_password(password)
    if not ok:
        raise RegistrationError(message)
    if not is_non_empty(security_question) or not is_non_empty(security_answer):
        raise RegistrationError(
            "A security question and answer are required for password recovery."
        )

    password_hash = hash_password(password)
    security_answer_hash = hash_password(security_answer.strip().lower())

    try:
        cursor = db.execute(
            """
            INSERT INTO users
                (username, email, password_hash, security_question, security_answer_hash)
            VALUES (?, ?, ?, ?, ?);
            """,
            (username, email, password_hash, security_question.strip(), security_answer_hash),
        )
        logger.info("Registered new user '%s'", username)
        return cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        logger.warning("Registration failed for '%s': %s", username, exc)
        if "username" in str(exc):
            raise RegistrationError("That username is already taken.") from exc
        if "email" in str(exc):
            raise RegistrationError("That email is already registered.") from exc
        raise RegistrationError("Could not create account. Please try again.") from exc
