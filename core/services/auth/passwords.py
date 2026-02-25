from __future__ import annotations

import base64
import hashlib
import hmac
import os


_ALGORITHM = "sha256"
_DEFAULT_ITERATIONS = 390_000
_SALT_BYTES = 16


def hash_password(raw_password: str, *, iterations: int = _DEFAULT_ITERATIONS) -> str:
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        _ALGORITHM,
        raw_password.encode("utf-8"),
        salt,
        iterations,
    )
    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_{_ALGORITHM}${iterations}${salt_b64}${digest_b64}"


def verify_password(raw_password: str, encoded_hash: str) -> bool:
    try:
        scheme, iter_s, salt_b64, digest_b64 = encoded_hash.split("$", 3)
        if scheme != f"pbkdf2_{_ALGORITHM}":
            return False
        iterations = int(iter_s)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(digest_b64.encode("ascii"))
    except Exception:
        return False

    actual = hashlib.pbkdf2_hmac(
        _ALGORITHM,
        raw_password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual, expected)


__all__ = ["hash_password", "verify_password"]

