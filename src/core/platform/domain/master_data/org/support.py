from __future__ import annotations

import re

from src.core.platform.common.exceptions import ValidationError

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def normalize_optional_organization_text(value: object) -> str:
    """Blank-allowed free text: trim only, never rewrite the content itself
    (legal identifiers such as registration/tax numbers must not be
    silently reformatted)."""
    return str(value or "").strip()


def normalize_email(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return ""
    if not _EMAIL_RE.match(normalized):
        raise ValidationError("Invalid email format.", code="ORGANIZATION_EMAIL_INVALID")
    return normalized


def normalize_phone(value: object) -> str:
    return str(value or "").strip()


def normalize_country_code(value: object) -> str:
    return str(value or "").strip().upper()


DEFAULT_ORGANIZATION_CODE = "DEFAULT"
DEFAULT_ORGANIZATION_NAME = "Default Organization"
DEFAULT_ORGANIZATION_TIMEZONE = "UTC"
DEFAULT_ORGANIZATION_CURRENCY = "EUR"


def normalize_code(value: str, *, label: str) -> str:
    normalized = (value or "").strip().upper()
    if not normalized:
        raise ValidationError(f"{label} is required.", code=f"{label.upper().replace(' ', '_')}_REQUIRED")
    return normalized


def normalize_name(value: str, *, label: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise ValidationError(f"{label} is required.", code=f"{label.upper().replace(' ', '_')}_REQUIRED")
    return normalized


__all__ = [
    "DEFAULT_ORGANIZATION_CODE",
    "DEFAULT_ORGANIZATION_CURRENCY",
    "DEFAULT_ORGANIZATION_NAME",
    "DEFAULT_ORGANIZATION_TIMEZONE",
    "normalize_code",
    "normalize_country_code",
    "normalize_email",
    "normalize_name",
    "normalize_optional_organization_text",
    "normalize_phone",
]
