from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any


def clean_text(value: Any, *, default: str = "") -> str:
    normalized = str(value or "").strip()
    if normalized:
        return normalized
    return default


def clean_id(value: Any) -> str | None:
    normalized = clean_text(value)
    return normalized or None


def enum_value(value: Any) -> str:
    return clean_text(getattr(value, "value", value)).upper()


def format_enum_label(value: str | None) -> str:
    normalized = clean_text(value).replace("_", " ")
    return normalized.title() if normalized else "-"


def format_active_label(value: bool) -> str:
    return "Active" if bool(value) else "Inactive"


def code_name_label(code: Any, name: Any, *, fallback: str = "-") -> str:
    code_text = clean_text(code)
    name_text = clean_text(name)
    if code_text and name_text:
        return f"{code_text} - {name_text}"
    if code_text:
        return code_text
    if name_text:
        return name_text
    return fallback


def party_contact_label(row) -> str:
    email = clean_text(getattr(row, "email", ""))
    phone = clean_text(getattr(row, "phone", ""))
    if email and phone:
        return f"{email} | {phone}"
    return email or phone or "-"


def date_text(value: date | None) -> str:
    return value.isoformat() if isinstance(value, date) else ""


def datetime_text(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat()


def parse_datetime_text(value: str | None):
    normalized = clean_text(value)
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    return datetime.fromisoformat(normalized)


def float_value(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def decimal_value(value: float | int | str | None) -> Decimal | None:
    if value in (None, ""):
        return None
    return Decimal(str(value))


def int_value(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


__all__ = [
    "clean_id",
    "clean_text",
    "code_name_label",
    "date_text",
    "datetime_text",
    "decimal_value",
    "enum_value",
    "float_value",
    "format_active_label",
    "format_enum_label",
    "int_value",
    "parse_datetime_text",
    "party_contact_label",
]
