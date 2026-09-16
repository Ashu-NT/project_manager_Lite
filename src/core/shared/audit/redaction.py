from __future__ import annotations

from typing import Any

# Any dict key containing one of these substrings (case-insensitive) is
# redacted before it can reach Audit persistence -- applied centrally here so
# no individual producer has to remember to sanitize its own metadata/
# before_data/after_data/changed_fields payload.
_SENSITIVE_KEY_MARKERS: tuple[str, ...] = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "private_key",
    "privatekey",
    "credential",
    "mfa_secret",
    "totp_secret",
    "recovery_code",
)

_REDACTED = "[REDACTED]"


def _is_sensitive_key(key: str) -> bool:
    lowered = str(key or "").lower()
    return any(marker in lowered for marker in _SENSITIVE_KEY_MARKERS)


def _redact_if_secret_value(inner: Any) -> Any:
    """A key merely naming a secret marker isn't itself sensitive -- a
    boolean/None policy flag like `must_change_password` can't hold a secret
    value, only a string (or nested structure) can. Recurse into dicts/lists
    rather than blindly stamping the whole value."""
    if isinstance(inner, str):
        return _REDACTED
    if isinstance(inner, dict):
        return {k: _REDACTED if isinstance(v, str) else redact_sensitive(v) for k, v in inner.items()}
    if isinstance(inner, (list, tuple)):
        return [_redact_if_secret_value(item) for item in inner]
    return inner


def redact_sensitive(value: Any) -> Any:
    """Recursively redacts any dict value whose key looks like a secret.
    Applied to every structured payload (metadata, before_data, after_data,
    changed_fields) on the way into Audit persistence -- Audit must never
    become a historical secret store."""
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, inner in value.items():
            if _is_sensitive_key(key):
                redacted[key] = _redact_if_secret_value(inner)
            else:
                redacted[key] = redact_sensitive(inner)
        return redacted
    if isinstance(value, (list, tuple)):
        return [redact_sensitive(item) for item in value]
    return value


def redact_changed_fields(value: Any) -> Any:
    """changed_fields has a nested {field: {"before": ..., "after": ...}}
    shape -- a field NAME that looks sensitive must redact both sides, not
    just whichever key inside the inner dict happens to match."""
    if not isinstance(value, dict):
        return redact_sensitive(value)
    result: dict[str, Any] = {}
    for field_name, diff in value.items():
        if _is_sensitive_key(field_name):
            if isinstance(diff, dict):
                result[field_name] = {
                    side: _REDACTED if isinstance(side_value, str) else side_value
                    for side, side_value in diff.items()
                }
            else:
                result[field_name] = _redact_if_secret_value(diff)
        else:
            result[field_name] = redact_sensitive(diff)
    return result


__all__ = ["redact_sensitive", "redact_changed_fields"]
