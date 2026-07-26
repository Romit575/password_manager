"""
services/password_service.py

Business logic for managing vault entries. This is the ONLY layer
that talks to both the database and the encryption module, so UI
code never has to think about encrypting/decrypting by hand.
"""

import logging
from typing import Optional

from database.database import Database
from encryption.crypto import CryptoManager
from models.password_model import PasswordEntry

logger = logging.getLogger(__name__)


class PasswordServiceError(Exception):
    pass


class PasswordService:
    def __init__(self, db: Database, crypto: CryptoManager) -> None:
        self.db = db
        self.crypto = crypto

    # ------------------------------------------------------------------
    def add_password(self, user_id: int, entry: PasswordEntry) -> int:
        if not entry.website.strip():
            raise PasswordServiceError("Website is required.")
        if not entry.password:
            raise PasswordServiceError("Password is required.")

        encrypted = self.crypto.encrypt(entry.password)
        cursor = self.db.execute(
            """
            INSERT INTO passwords
                (user_id, website, url, username, email, encrypted_password, notes, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                user_id,
                entry.website.strip(),
                entry.url.strip(),
                entry.username.strip(),
                entry.email.strip(),
                encrypted,
                entry.notes.strip(),
                entry.category.strip() or "Other",
            ),
        )
        logger.info("Added password entry '%s' for user %s", entry.website, user_id)
        return cursor.lastrowid

    # ------------------------------------------------------------------
    def update_password(self, entry_id: int, user_id: int, entry: PasswordEntry) -> None:
        if not entry.website.strip():
            raise PasswordServiceError("Website is required.")
        if not entry.password:
            raise PasswordServiceError("Password is required.")

        encrypted = self.crypto.encrypt(entry.password)
        self.db.execute(
            """
            UPDATE passwords
            SET website = ?, url = ?, username = ?, email = ?,
                encrypted_password = ?, notes = ?, category = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?;
            """,
            (
                entry.website.strip(),
                entry.url.strip(),
                entry.username.strip(),
                entry.email.strip(),
                encrypted,
                entry.notes.strip(),
                entry.category.strip() or "Other",
                entry_id,
                user_id,
            ),
        )
        logger.info("Updated password entry id=%s for user %s", entry_id, user_id)

    # ------------------------------------------------------------------
    def delete_password(self, entry_id: int, user_id: int) -> None:
        self.db.execute(
            "DELETE FROM passwords WHERE id = ? AND user_id = ?;", (entry_id, user_id)
        )
        logger.info("Deleted password entry id=%s for user %s", entry_id, user_id)

    # ------------------------------------------------------------------
    def get_password_by_id(self, entry_id: int, user_id: int) -> Optional[PasswordEntry]:
        row = self.db.fetchone(
            "SELECT * FROM passwords WHERE id = ? AND user_id = ?;", (entry_id, user_id)
        )
        if row is None:
            return None
        decrypted = self.crypto.decrypt(row["encrypted_password"])
        return PasswordEntry.from_row(row, decrypted)

    # ------------------------------------------------------------------
    def get_all_passwords(self, user_id: int) -> list[PasswordEntry]:
        rows = self.db.fetchall(
            "SELECT * FROM passwords WHERE user_id = ? ORDER BY website COLLATE NOCASE;",
            (user_id,),
        )
        return [PasswordEntry.from_row(row, self.crypto.decrypt(row["encrypted_password"])) for row in rows]

    # ------------------------------------------------------------------
    def search_passwords(self, user_id: int, query: str) -> list[PasswordEntry]:
        """Search by website, username, or category. Uses a
        parameterized LIKE query -- never string-concatenated -- to
        stay safe from SQL injection."""
        like_query = f"%{query.strip()}%"
        rows = self.db.fetchall(
            """
            SELECT * FROM passwords
            WHERE user_id = ?
              AND (website LIKE ? OR username LIKE ? OR category LIKE ?)
            ORDER BY website COLLATE NOCASE;
            """,
            (user_id, like_query, like_query, like_query),
        )
        return [PasswordEntry.from_row(row, self.crypto.decrypt(row["encrypted_password"])) for row in rows]

    # ------------------------------------------------------------------
    def get_stats(self, user_id: int) -> dict:
        """Powers the Dashboard 'overview' cards."""
        total = self.db.fetchone(
            "SELECT COUNT(*) AS count FROM passwords WHERE user_id = ?;", (user_id,)
        )["count"]
        categories = self.db.fetchone(
            "SELECT COUNT(DISTINCT category) AS count FROM passwords WHERE user_id = ?;",
            (user_id,),
        )["count"]
        recent_rows = self.db.fetchall(
            """
            SELECT * FROM passwords WHERE user_id = ?
            ORDER BY created_at DESC LIMIT 5;
            """,
            (user_id,),
        )
        recent = [row["website"] for row in recent_rows]
        return {"total_passwords": total, "total_categories": categories, "recent": recent}
