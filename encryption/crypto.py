"""
encryption/crypto.py

Thin wrapper around Fernet symmetric encryption. Every password
stored in the vault passes through encrypt() before hitting the
database, and through decrypt() only at the moment the user asks
to view/copy it.
"""

import logging

from cryptography.fernet import Fernet, InvalidToken

from encryption.key_manager import KeyManager

logger = logging.getLogger(__name__)


class CryptoManager:
    def __init__(self, key_manager: KeyManager | None = None) -> None:
        self._key_manager = key_manager or KeyManager()
        self._fernet = Fernet(self._key_manager.get_or_create_key())

    def encrypt(self, plain_text: str) -> str:
        """Encrypt a plain string and return a URL-safe base64 string
        suitable for storing directly in a SQLite TEXT column."""
        token = self._fernet.encrypt(plain_text.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, cipher_text: str) -> str:
        """Decrypt a string previously produced by encrypt(). Raises
        ValueError if the ciphertext is invalid/corrupted/tampered."""
        try:
            plain_bytes = self._fernet.decrypt(cipher_text.encode("utf-8"))
            return plain_bytes.decode("utf-8")
        except InvalidToken:
            logger.error("Failed to decrypt value: invalid token.")
            raise ValueError("Could not decrypt this entry. The data may be corrupted.")
