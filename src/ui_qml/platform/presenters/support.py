from __future__ import annotations

from typing import Any

from src.api.desktop.platform import DesktopApiError, DesktopApiResult


def preview_error_result(message: str) -> DesktopApiResult[object]:
    return DesktopApiResult(
        ok=False,
        error=DesktopApiError(
            code="preview_only",
            message=message,
            category="preview",
        ),
    )


def option_item(
    *,
    label: str,
    value: str,
    supporting_text: str = "",
) -> dict[str, str]:
    return {
        "label": label,
        "value": value,
        "supportingText": supporting_text,
    }


def string_value(payload: dict[str, Any], key: str, *, default: str = "") -> str:
    value = payload.get(key, default)
    if value is None:
        return default
    return str(value).strip()


def optional_string_value(payload: dict[str, Any], key: str) -> str | None:
    value = string_value(payload, key)
    return value or None


def bool_value(payload: dict[str, Any], key: str, *, default: bool = False) -> bool:
    value = payload.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def int_value(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value in {None, ""}:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def tuple_of_strings(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(
        item_text
        for item in value
        if (item_text := str(item).strip())
    )


def enum_code(value: Any) -> str:
    raw = getattr(value, "value", value)
    if raw is None:
        return ""
    return str(raw).strip()


def title_case_code(value: Any) -> str:
    code = enum_code(value)
    return code.replace("_", " ").title()


__all__ = [
    "bool_value",
    "enum_code",
    "int_value",
    "option_item",
    "optional_string_value",
    "preview_error_result",
    "string_value",
    "title_case_code",
    "tuple_of_strings",
]
