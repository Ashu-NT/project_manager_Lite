from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from PySide6.QtWidgets import QMessageBox, QWidget

from core.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from core.services.approval.policy import is_governance_required
from core.services.auth import UserSessionContext
from ui.shared.incident_support import emit_error_event, message_with_incident


_T = TypeVar("_T")
_UI_KNOWN_ERRORS = (
    ValidationError,
    BusinessRuleError,
    NotFoundError,
    ConcurrencyError,
    ValueError,
)
_CALLBACK_ERROR_EVENT_MAP = {
    "create_task": "business.task.add.error",
    "edit_task": "business.task.update.error",
    "recalc_project_schedule": "business.schedule.recalculate.error",
    "_generate_baseline": "business.baseline.create.error",
    "export_gantt_png": "business.export.gantt.error",
    "export_evm_png": "business.export.evm.error",
    "export_excel": "business.export.excel.error",
    "export_pdf": "business.export.pdf.error",
}


def has_permission(user_session: UserSessionContext | None, permission_code: str) -> bool:
    if user_session is None:
        return True
    return user_session.has_permission(permission_code)


def can_execute_governed_action(
    *,
    user_session: UserSessionContext | None,
    manage_permission: str,
    governance_action: str | None = None,
    request_permission: str = "approval.request",
) -> bool:
    if has_permission(user_session, manage_permission):
        return True
    if not governance_action:
        return False
    if not has_permission(user_session, request_permission):
        return False
    return is_governance_required(governance_action)


def apply_permission_hint(widget: QWidget, *, allowed: bool, missing_permission: str) -> None:
    if allowed:
        return
    widget.setEnabled(False)
    current_hint = widget.toolTip().strip()
    if current_hint:
        return
    widget.setToolTip(f"Requires '{missing_permission}' permission.")


def run_guarded_action(
    parent: QWidget,
    *,
    title: str,
    action: Callable[[], _T],
    callback_name: str | None = None,
) -> _T | None:
    name = str(callback_name or "").strip()
    event_type = _CALLBACK_ERROR_EVENT_MAP.get(name, "ui.action.error")
    try:
        return action()
    except _UI_KNOWN_ERRORS as exc:
        incident_id = emit_error_event(
            event_type=event_type,
            message=f"{title} action failed.",
            parent=parent,
            error=exc,
            data={"callback": name or "unknown", "known_error": True},
        )
        QMessageBox.warning(parent, title, message_with_incident(str(exc), incident_id))
        return None
    except Exception as exc:
        incident_id = emit_error_event(
            event_type=event_type,
            message=f"{title} action failed with unexpected error.",
            parent=parent,
            error=exc,
            data={"callback": name or "unknown", "known_error": False},
        )
        QMessageBox.critical(parent, title, message_with_incident(str(exc), incident_id))
        return None


def make_guarded_slot(
    parent: QWidget,
    *,
    title: str,
    callback: Callable[..., object],
) -> Callable[..., None]:
    callback_name = getattr(callback, "__name__", "") or ""

    def _wrapped(*_args, **_kwargs) -> None:
        run_guarded_action(
            parent,
            title=title,
            callback_name=callback_name,
            action=lambda: callback(),
        )

    return _wrapped


__all__ = [
    "apply_permission_hint",
    "can_execute_governed_action",
    "has_permission",
    "make_guarded_slot",
    "run_guarded_action",
]
