import base64
import hashlib
import os

from src.core.platform.auth.passwords import verify_password


def test_verify_password_accepts_sha256_stored_scheme():
    raw_password = "StrongPass123!"
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", raw_password.encode("utf-8"), salt, 100_000)
    encoded_hash = (
        "pbkdf2_sha256$100000$"
        f"{base64.b64encode(salt).decode('ascii')}$"
        f"{base64.b64encode(digest).decode('ascii')}"
    )

    assert verify_password(raw_password, encoded_hash) is True


def test_verify_password_rejects_unknown_scheme():
    raw_password = "StrongPass123!"
    encoded_hash = "pbkdf2_unknown$100000$AAAAAAAAAAAAAAAAAAAAAA==$BBBBBBBBBBBBBBBBBBBBBB=="

    assert verify_password(raw_password, encoded_hash) is False
