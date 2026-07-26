"""
services/import_service.py

Reads entries back in from CSV or the app's own encrypted JSON
export format and returns a list of PasswordEntry objects, ready to
be handed to PasswordService.add_password() one at a time.

Note: this file is named `import_service.py` rather than `import.py`
because `import` is a reserved Python keyword and cannot be used as
a module filename.
"""

import csv
import json
import logging
from pathlib import Path

from encryption.crypto import CryptoManager
from models.password_model import PasswordEntry

logger = logging.getLogger(__name__)


class ImportError_(Exception):
    """Custom name to avoid shadowing Python's built-in ImportError."""


def import_from_csv(filepath: Path) -> list[PasswordEntry]:
    entries: list[PasswordEntry] = []
    try:
        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                website = (row.get("website") or "").strip()
                password = (row.get("password") or "").strip()
                if not website or not password:
                    # Skip malformed rows rather than crashing the
                    # whole import.
                    logger.warning("Skipping CSV row missing website/password: %s", row)
                    continue
                entries.append(
                    PasswordEntry(
                        website=website,
                        url=(row.get("url") or "").strip(),
                        username=(row.get("username") or "").strip(),
                        email=(row.get("email") or "").strip(),
                        password=password,
                        notes=(row.get("notes") or "").strip(),
                        category=(row.get("category") or "Other").strip(),
                    )
                )
    except (OSError, csv.Error) as exc:
        raise ImportError_(f"Could not read CSV file: {exc}") from exc

    logger.info("Parsed %d entries from CSV: %s", len(entries), filepath)
    return entries


def import_from_encrypted_json(filepath: Path, crypto: CryptoManager) -> list[PasswordEntry]:
    try:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise ImportError_(f"Could not read JSON file: {exc}") from exc

    if data.get("format") != "password_manager_encrypted_v1":
        raise ImportError_("Unrecognized export format.")

    entries: list[PasswordEntry] = []
    for item in data.get("entries", []):
        try:
            password = crypto.decrypt(item["encrypted_password"])
        except (ValueError, KeyError):
            logger.warning("Skipping JSON entry that could not be decrypted: %s", item.get("website"))
            continue
        entries.append(
            PasswordEntry(
                website=item.get("website", ""),
                url=item.get("url", ""),
                username=item.get("username", ""),
                email=item.get("email", ""),
                password=password,
                notes=item.get("notes", ""),
                category=item.get("category", "Other"),
            )
        )

    logger.info("Parsed %d entries from encrypted JSON: %s", len(entries), filepath)
    return entries
