from __future__ import annotations

from src.core.platform.common.exceptions import ValidationError


def normalize_email(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    return normalized or None


def normalize_phone(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


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
    "normalize_email",
    "normalize_name",
    "normalize_phone",
]
