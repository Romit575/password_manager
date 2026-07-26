"""
models/password_model.py

A simple data class representing one vault entry. Keeping this
separate from the database layer means UI code and services can pass
around a typed object instead of raw sqlite3.Row / dict values.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PasswordEntry:
    website: str
    username: str
    password: str  # plain text in memory only -- never written to disk like this
    id: Optional[int] = None
    user_id: Optional[int] = None
    url: str = ""
    email: str = ""
    notes: str = ""
    category: str = "Other"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row, decrypted_password: str) -> "PasswordEntry":
        """Build a PasswordEntry from a sqlite3.Row plus an already
        decrypted password string."""
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            website=row["website"],
            url=row["url"] or "",
            username=row["username"] or "",
            email=row["email"] or "",
            password=decrypted_password,
            notes=row["notes"] or "",
            category=row["category"] or "Other",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
