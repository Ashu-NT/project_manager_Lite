from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from argon2.low_level import Type


# OWASP's Argon2id baseline. Keep these explicit so a dependency upgrade does
# not silently change authentication cost across application environments.
_TIME_COST = 2
_MEMORY_COST_KIB = 19 * 1024
_PARALLELISM = 1
_HASH_LENGTH = 32
_SALT_LENGTH = 16

_PASSWORD_HASHER = PasswordHasher(
    time_cost=_TIME_COST,
    memory_cost=_MEMORY_COST_KIB,
    parallelism=_PARALLELISM,
    hash_len=_HASH_LENGTH,
    salt_len=_SALT_LENGTH,
    type=Type.ID,
)


def hash_password(raw_password: str) -> str:
    """Return a PHC-encoded Argon2id password hash with a random salt."""
    return _PASSWORD_HASHER.hash(raw_password)


def verify_password(raw_password: str, encoded_hash: str) -> bool:
    """Verify only Argon2id hashes and fail closed for invalid input."""
    if not isinstance(encoded_hash, str) or not encoded_hash.startswith("$argon2id$"):
        return False
    try:
        return bool(_PASSWORD_HASHER.verify(encoded_hash, raw_password))
    except (InvalidHashError, VerificationError, TypeError):
        return False


def password_needs_rehash(encoded_hash: str) -> bool:
    """Report whether a valid hash uses an obsolete Argon2id cost profile."""
    if not isinstance(encoded_hash, str) or not encoded_hash.startswith("$argon2id$"):
        return True
    try:
        return _PASSWORD_HASHER.check_needs_rehash(encoded_hash)
    except (InvalidHashError, TypeError):
        return True


__all__ = ["hash_password", "password_needs_rehash", "verify_password"]
