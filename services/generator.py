"""
services/generator.py

Generates strong random passwords. Uses the `secrets` module rather
than `random` -- `secrets` is designed for cryptographic use and is
the correct choice any time you're generating something security
sensitive like a password or token.
"""

import string
import secrets

UPPERCASE = string.ascii_uppercase
LOWERCASE = string.ascii_lowercase
DIGITS = string.digits
SYMBOLS = "!@#$%^&*()-_=+[]{};:,.<>?/"


class GeneratorError(Exception):
    pass


def generate_password(
    length: int = 16,
    use_upper: bool = True,
    use_lower: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
) -> str:
    if length < 4:
        raise GeneratorError("Password length must be at least 4 characters.")

    pool = ""
    guaranteed: list[str] = []

    if use_upper:
        pool += UPPERCASE
        guaranteed.append(secrets.choice(UPPERCASE))
    if use_lower:
        pool += LOWERCASE
        guaranteed.append(secrets.choice(LOWERCASE))
    if use_digits:
        pool += DIGITS
        guaranteed.append(secrets.choice(DIGITS))
    if use_symbols:
        pool += SYMBOLS
        guaranteed.append(secrets.choice(SYMBOLS))

    if not pool:
        raise GeneratorError("Select at least one character type.")
    if length < len(guaranteed):
        raise GeneratorError(
            f"Length must be at least {len(guaranteed)} to include every selected character type."
        )

    # Guarantee at least one character from every selected category,
    # then fill the rest randomly, then shuffle so the guaranteed
    # characters aren't always in the same position.
    remaining = length - len(guaranteed)
    password_chars = guaranteed + [secrets.choice(pool) for _ in range(remaining)]

    # Fisher-Yates shuffle using the secrets module (random.shuffle
    # is NOT cryptographically secure).
    for i in range(len(password_chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        password_chars[i], password_chars[j] = password_chars[j], password_chars[i]

    return "".join(password_chars)


def estimate_strength(password: str) -> str:
    """A lightweight heuristic (not a full entropy calculation) used
    to show a 'Weak / Medium / Strong / Very Strong' label in the UI."""
    score = 0
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if any(c.islower() for c in password):
        score += 1
    if any(c.isupper() for c in password):
        score += 1
    if any(c.isdigit() for c in password):
        score += 1
    if any(c in SYMBOLS for c in password):
        score += 1

    if score <= 2:
        return "Weak"
    if score <= 4:
        return "Medium"
    if score == 5:
        return "Strong"
    return "Very Strong"
