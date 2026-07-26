"""
main.py

Application entry point.

Run with:
    python main.py

Responsibilities:
1. Configure logging (console + rotating log file).
2. Initialize the SQLite database (creates tables on first run).
3. Initialize the encryption key manager / CryptoManager.
4. Launch the login window, which hands off to the dashboard on
   successful authentication.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from database.database import Database
from encryption.crypto import CryptoManager
from ui.login_window import LoginWindow

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_FILE = LOG_DIR / "app.log"


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Rotates once the log file passes ~1 MB, keeping 3 old copies.
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def main() -> None:
    configure_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Password Manager...")

    db = Database()
    db.initialize()

    crypto = CryptoManager()

    app = LoginWindow(db, crypto)
    try:
        app.mainloop()
    finally:
        db.close()
        logger.info("Password Manager closed.")


if __name__ == "__main__":
    main()
