from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct
from datetime import datetime, timezone


_TOTP_INTERVAL_SECONDS = 30
_TOTP_DIGITS = 6


def generate_mfa_secret(*, num_bytes: int = 20) -> str:
    raw_secret = os.urandom(max(10, int(num_bytes or 20)))
    return base64.b32encode(raw_secret).decode("ascii").rstrip("=")


def generate_totp_code(secret: str, *, at_time: datetime | None = None) -> str:
    current_time = at_time or datetime.now(timezone.utc)
    counter = int(current_time.timestamp()) // _TOTP_INTERVAL_SECONDS
    normalized_secret = _decode_secret(secret)
    payload = struct.pack(">Q", counter)
    digest = hmac.new(normalized_secret, payload, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary_code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    value = binary_code % (10**_TOTP_DIGITS)
    return f"{value:0{_TOTP_DIGITS}d}"


def verify_totp_code(
    secret: str | None,
    code: str | None,
    *,
    at_time: datetime | None = None,
    allowed_drift_steps: int = 1,
) -> bool:
    normalized_secret = str(secret or "").strip().upper()
    normalized_code = "".join(ch for ch in str(code or "").strip() if ch.isdigit())
    if not normalized_secret or len(normalized_code) != _TOTP_DIGITS:
        return False
    current_time = at_time or datetime.now(timezone.utc)
    for step in range(-max(0, int(allowed_drift_steps or 0)), max(0, int(allowed_drift_steps or 0)) + 1):
        window_time = datetime.fromtimestamp(
            current_time.timestamp() + (step * _TOTP_INTERVAL_SECONDS),
            tz=timezone.utc,
        )
        if hmac.compare_digest(generate_totp_code(normalized_secret, at_time=window_time), normalized_code):
            return True
    return False


def _decode_secret(secret: str) -> bytes:
    normalized = str(secret or "").strip().upper()
    padding = "=" * ((8 - (len(normalized) % 8)) % 8)
    return base64.b32decode((normalized + padding).encode("ascii"), casefold=True)


__all__ = [
    "generate_mfa_secret",
    "generate_totp_code",
    "verify_totp_code",
]
