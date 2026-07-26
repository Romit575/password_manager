"""
services/export_service.py

Exports a user's vault to either:
- CSV (plain text passwords -- convenient for migrating to another
  password manager, but the resulting file is NOT protected, so the
  UI must warn the user clearly before writing one).
- Encrypted JSON (passwords stay encrypted with the app's own Fernet
  key -- safer to store/transfer, and can be re-imported later by
  this same app instance).
"""

import csv
import json
import logging
from pathlib import Path

from encryption.crypto import CryptoManager
from models.password_model import PasswordEntry

logger = logging.getLogger(__name__)

CSV_FIELDS = ["website", "url", "username", "email", "password", "notes", "category"]


def export_to_csv(entries: list[PasswordEntry], filepath: Path) -> None:
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for entry in entries:
            writer.writerow(
                {
                    "website": entry.website,
                    "url": entry.url,
                    "username": entry.username,
                    "email": entry.email,
                    "password": entry.password,
                    "notes": entry.notes,
                    "category": entry.category,
                }
            )
    logger.info("Exported %d entries to CSV: %s", len(entries), filepath)


def export_to_encrypted_json(
    entries: list[PasswordEntry], filepath: Path, crypto: CryptoManager
) -> None:
    payload = []
    for entry in entries:
        payload.append(
            {
                "website": entry.website,
                "url": entry.url,
                "username": entry.username,
                "email": entry.email,
                # Re-encrypt explicitly here (rather than reusing the
                # DB ciphertext) to keep this module independent of
                # storage format.
                "encrypted_password": crypto.encrypt(entry.password),
                "notes": entry.notes,
                "category": entry.category,
            }
        )
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({"format": "password_manager_encrypted_v1", "entries": payload}, f, indent=2)
    logger.info("Exported %d entries to encrypted JSON: %s", len(entries), filepath)
