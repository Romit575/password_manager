"""
auth/security.py

Shared security helpers used by both login.py and register.py:
- bcrypt password hashing/verification
- basic form validation
- an inactivity/auto-logout timer used by the dashboard
"""

import logging
import re
from typing import Callable, Optional

import bcrypt

logger = logging.getLogger(__name__)

# Auto logout after this many milliseconds of no mouse/keyboard activity.
AUTO_LOGOUT_MS = 5 * 60 * 1000  # 5 minutes

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ------------------------------------------------------------------
# Password hashing
# ------------------------------------------------------------------
def hash_password(plain_password: str) -> str:
    """Hash a password with bcrypt. Returns a string safe to store
    in the database (bcrypt hashes are self-contained: they embed
    the salt, so no separate salt column is needed)."""
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except ValueError:
        logger.exception("Stored password hash is malformed.")
        return False


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------
def is_valid_email(email: str) -> bool:
    return bool(EMAIL_PATTERN.match(email))


def is_strong_password(password: str) -> tuple[bool, str]:
    """Returns (is_valid, message). Used for both account passwords
    and as a sanity check when users type a custom master password."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one digit."
    return True, "OK"


def is_non_empty(value: str) -> bool:
    return bool(value and value.strip())


# ------------------------------------------------------------------
# Auto-logout / inactivity monitor
# ------------------------------------------------------------------
class InactivityMonitor:
    """
    Watches for user activity on a Tkinter/CustomTkinter widget tree
    and triggers a callback after a period of inactivity.

    Usage (inside the dashboard window):
        monitor = InactivityMonitor(root, on_timeout=self.logout)
        monitor.start()
    Any bound widget event (mouse move, click, key press) resets the
    timer via `reset()`.
    """

    def __init__(
        self,
        widget,
        on_timeout: Callable[[], None],
        timeout_ms: int = AUTO_LOGOUT_MS,
    ) -> None:
        self.widget = widget
        self.on_timeout = on_timeout
        self.timeout_ms = timeout_ms
        self._after_id: Optional[str] = None

    def start(self) -> None:
        self.widget.bind_all("<Motion>", self._reset, add="+")
        self.widget.bind_all("<Key>", self._reset, add="+")
        self.widget.bind_all("<Button>", self._reset, add="+")
        self._reset()

    def stop(self) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _reset(self, _event=None) -> None:
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
        self._after_id = self.widget.after(self.timeout_ms, self._trigger_timeout)

    def _trigger_timeout(self) -> None:
        logger.info("Auto-logout triggered due to inactivity.")
        self.on_timeout()
