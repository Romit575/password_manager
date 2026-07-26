"""
database/database.py

A thin, safe wrapper around sqlite3.

Design goals:
- Single place responsible for opening/closing connections.
- Every query is parameterized (never uses string formatting) to
  prevent SQL injection.
- Foreign key constraints are enabled explicitly (SQLite disables
  them by default).
"""

import logging
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional

from database.schema import ALL_STATEMENTS

logger = logging.getLogger(__name__)

# Location of the SQLite database file. Placed at the project root
# so it sits next to main.py, matching the required project layout.
DB_PATH = Path(__file__).resolve().parent.parent / "vault.db"


class Database:
    """
    Wraps a single SQLite connection and exposes safe helper methods.

    Usage:
        db = Database()
        db.initialize()
        rows = db.fetchall("SELECT * FROM users WHERE username = ?", (name,))
    """

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------
    def connect(self) -> sqlite3.Connection:
        """Return an open connection, creating it on first use."""
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            # Rows behave like dictionaries -> row["column_name"]
            self._connection.row_factory = sqlite3.Row
            # SQLite requires this pragma to actually enforce
            # FOREIGN KEY ... ON DELETE CASCADE behavior.
            self._connection.execute("PRAGMA foreign_keys = ON;")
            logger.info("Connected to database at %s", self.db_path)
        return self._connection

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed.")

    def initialize(self) -> None:
        """Create all tables/indexes if they do not already exist."""
        conn = self.connect()
        try:
            for statement in ALL_STATEMENTS:
                conn.execute(statement)
            conn.commit()
            logger.info("Database schema is ready.")
        except sqlite3.Error:
            logger.exception("Failed to initialize database schema.")
            raise

    # ------------------------------------------------------------------
    # Query helpers (ALWAYS use parameterized queries -- never format
    # user input directly into SQL strings).
    # ------------------------------------------------------------------
    def execute(self, query: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        """Run an INSERT/UPDATE/DELETE and commit. Returns the cursor
        (useful for reading `.lastrowid` after an INSERT)."""
        conn = self.connect()
        try:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor
        except sqlite3.Error:
            conn.rollback()
            logger.exception("Query failed: %s | params=%s", query, params)
            raise

    def fetchone(self, query: str, params: Iterable[Any] = ()) -> Optional[sqlite3.Row]:
        conn = self.connect()
        try:
            cursor = conn.execute(query, params)
            return cursor.fetchone()
        except sqlite3.Error:
            logger.exception("Query failed: %s | params=%s", query, params)
            raise

    def fetchall(self, query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        conn = self.connect()
        try:
            cursor = conn.execute(query, params)
            return cursor.fetchall()
        except sqlite3.Error:
            logger.exception("Query failed: %s | params=%s", query, params)
            raise
