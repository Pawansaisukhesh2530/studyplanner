"""Password hashing and opaque, expiring login tokens using Python's library."""

import hashlib
import hmac
import secrets


def hash_password(password):
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        raise ValueError("Password must contain 8–128 characters.")
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 300000)
    return "pbkdf2_sha256$300000$" + salt + "$" + digest.hex()


def check_password(password, stored):
    if not isinstance(password, str) or len(password) > 128:
        return False
    try:
        method, iterations, salt, expected = stored.split("$")
        if method != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False


def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()
