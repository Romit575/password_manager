"""
auth/login.py

Handles authenticating an existing user, the "remember me" feature,
"forgot password" recovery via a security question, and changing an
already-logged-in user's password.
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional

from auth.security import hash_password, is_strong_password, verify_password
from database.database import Database

logger = logging.getLogger(__name__)

# Small local file used only to remember the last username typed in,
# so the login field can be pre-filled. No password/secret is ever
# stored here.
REMEMBER_ME_PATH = Path(__file__).resolve().parent.parent / "assets" / "remember_me.json"


class AuthenticationError(Exception):
    """Raised when login/recovery/change-password fails."""


def authenticate_user(db: Database, username: str, password: str) -> sqlite3.Row:
    """Verify credentials and return the matching user row.
    Raises AuthenticationError on any failure (never reveals whether
    the username or the password was the wrong part, to avoid
    leaking which usernames exist)."""
    row = db.fetchone("SELECT * FROM users WHERE username = ?;", (username.strip(),))
    if row is None or not verify_password(password, row["password_hash"]):
        logger.warning("Failed login attempt for username '%s'", username)
        raise AuthenticationError("Invalid username or password.")
    logger.info("User '%s' logged in.", username)
    return row


def get_security_question(db: Database, username: str) -> Optional[str]:
    row = db.fetchone(
        "SELECT security_question FROM users WHERE username = ?;", (username.strip(),)
    )
    return row["security_question"] if row else None


def reset_password_with_security_answer(
    db: Database,
    username: str,
    security_answer: str,
    new_password: str,
    confirm_password: str,
) -> None:
    row = db.fetchone("SELECT * FROM users WHERE username = ?;", (username.strip(),))
    if row is None:
        raise AuthenticationError("No account found with that username.")

    if not verify_password(security_answer.strip().lower(), row["security_answer_hash"]):
        raise AuthenticationError("Security answer is incorrect.")

    if new_password != confirm_password:
        raise AuthenticationError("New passwords do not match.")

    ok, message = is_strong_password(new_password)
    if not ok:
        raise AuthenticationError(message)

    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?;",
        (hash_password(new_password), row["id"]),
    )
    logger.info("Password reset via security question for user '%s'", username)


def change_password(
    db: Database,
    user_id: int,
    current_password: str,
    new_password: str,
    confirm_password: str,
) -> None:
    row = db.fetchone("SELECT * FROM users WHERE id = ?;", (user_id,))
    if row is None:
        raise AuthenticationError("User not found.")

    if not verify_password(current_password, row["password_hash"]):
        raise AuthenticationError("Current password is incorrect.")

    if new_password != confirm_password:
        raise AuthenticationError("New passwords do not match.")

    ok, message = is_strong_password(new_password)
    if not ok:
        raise AuthenticationError(message)

    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?;",
        (hash_password(new_password), user_id),
    )
    logger.info("User id %s changed their password.", user_id)


# ------------------------------------------------------------------
# Remember Me (username only -- never persists a password)
# ------------------------------------------------------------------
def save_remembered_username(username: str) -> None:
    REMEMBER_ME_PATH.parent.mkdir(parents=True, exist_ok=True)
    REMEMBER_ME_PATH.write_text(json.dumps({"username": username}), encoding="utf-8")


def load_remembered_username() -> Optional[str]:
    if not REMEMBER_ME_PATH.exists():
        return None
    try:
        data = json.loads(REMEMBER_ME_PATH.read_text(encoding="utf-8"))
        return data.get("username")
    except (json.JSONDecodeError, OSError):
        return None


def clear_remembered_username() -> None:
    if REMEMBER_ME_PATH.exists():
        REMEMBER_ME_PATH.unlink()
