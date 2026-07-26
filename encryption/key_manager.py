"""
encryption/key_manager.py

Handles creation and safe storage of the Fernet encryption key used
to encrypt/decrypt every vault password.

IMPORTANT SECURITY NOTE (documented again in README.md):
This is a *local, single-machine* vault. The key is stored on disk,
next to the database, with restricted file permissions. Anyone with
direct filesystem access to a logged-in machine could theoretically
read both the key and the database. This is the same trust model
used by most local password managers/browser vaults -- protecting
the OS user account itself (disk encryption, OS login password) is
what ultimately protects the vault.
"""

import logging
import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

KEY_PATH = Path(__file__).resolve().parent / "secret.key"


class KeyManager:
    """Creates the Fernet key on first run and loads it afterwards."""

    def __init__(self, key_path: Path = KEY_PATH) -> None:
        self.key_path = key_path

    def get_or_create_key(self) -> bytes:
        if self.key_path.exists():
            return self._load_key()
        return self._generate_key()

    def _generate_key(self) -> bytes:
        key = Fernet.generate_key()
        self.key_path.write_bytes(key)
        self._restrict_permissions()
        logger.info("Generated new encryption key at %s", self.key_path)
        return key

    def _load_key(self) -> bytes:
        return self.key_path.read_bytes()

    def _restrict_permissions(self) -> None:
        """Best-effort: make the key file readable/writable only by
        the current OS user. No-op (silently skipped) on platforms
        that don't support POSIX permission bits, e.g. Windows."""
        try:
            os.chmod(self.key_path, stat.S_IRUSR | stat.S_IWUSR)
        except (OSError, NotImplementedError):
            logger.debug("Could not restrict key file permissions on this OS.")
