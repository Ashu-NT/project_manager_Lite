from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.presenters.financials.shared.validation import (
    optional_text,
    require_date,
    require_decimal,
)


def _optional_date(payload: dict[str, Any], key: str):
    value = optional_text(payload, key)
    if not value:
        return None
    return require_date(payload, key, f"{key} must use YYYY-MM-DD.")


def _optional_decimal_text(payload: dict[str, Any], key: str) -> str | None:
    value = optional_text(payload, key)
    if value is None:
        return None
    return format(require_decimal(payload, key, f"{key} must be a valid number."), "f")
