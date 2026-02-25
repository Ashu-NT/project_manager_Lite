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


_T = TypeVar("_T")
_UI_KNOWN_ERRORS = (
    ValidationError,
    BusinessRuleError,
    NotFoundError,
    ConcurrencyError,
    ValueError,
)


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
) -> _T | None:
    try:
        return action()
    except _UI_KNOWN_ERRORS as exc:
        QMessageBox.warning(parent, title, str(exc))
        return None
    except Exception as exc:
        QMessageBox.critical(parent, title, str(exc))
        return None


def make_guarded_slot(
    parent: QWidget,
    *,
    title: str,
    callback: Callable[..., object],
) -> Callable[..., None]:
    def _wrapped(*_args, **_kwargs) -> None:
        run_guarded_action(
            parent,
            title=title,
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
