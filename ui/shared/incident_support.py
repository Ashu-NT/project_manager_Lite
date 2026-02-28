from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from PySide6.QtWidgets import QWidget

from infra.operational_support import get_operational_support


def resolve_incident_id(parent: QWidget | None = None) -> str:
    if parent is not None:
        current = getattr(parent, "_current_incident_id", None)
        if callable(current):
            try:
                value = str(current()).strip()
                if value:
                    return value
            except Exception:
                pass
    return get_operational_support().new_incident_id()


def message_with_incident(message: str, incident_id: str) -> str:
    base = (message or "Operation failed.").strip()
    return f"{base}\n\nIncident ID: {incident_id}\nShare this ID with support."


def emit_error_event(
    *,
    event_type: str,
    message: str,
    parent: QWidget | None = None,
    error: BaseException | None = None,
    data: Mapping[str, Any] | None = None,
    trace_id: str | None = None,
) -> str:
    incident_id = (trace_id or resolve_incident_id(parent)).strip()
    payload: dict[str, Any] = dict(data or {})
    if parent is not None:
        payload.setdefault("widget", type(parent).__name__)
    if error is not None:
        payload.setdefault("error_type", type(error).__name__)
        payload.setdefault("error", str(error))
    try:
        get_operational_support().emit_event(
            event_type=(event_type or "ui.error").strip() or "ui.error",
            level="ERROR",
            trace_id=incident_id,
            message=message or "UI error.",
            data=payload,
        )
    except Exception:
        pass
    return incident_id


__all__ = [
    "emit_error_event",
    "message_with_incident",
    "resolve_incident_id",
]
