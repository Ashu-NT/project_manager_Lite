from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import ProjectManagementTimesheetsDesktopApi

from .validation import (
    optional_text,
    require_positive_int,
    require_text,
)

def approve_period(
    desktop_api: ProjectManagementTimesheetsDesktopApi,
    payload: dict[str, Any],
) -> None:
    desktop_api.approve_period(
        require_text(payload, "periodId", "Choose a period to approve."),
        expected_version=require_positive_int(
            payload, "expectedVersion", "Refresh the period before approving it."
        ),
        note=optional_text(payload, "note") or "",
    )

def reject_period(
    desktop_api: ProjectManagementTimesheetsDesktopApi,
    payload: dict[str, Any],
) -> None:
    desktop_api.reject_period(
        require_text(payload, "periodId", "Choose a period to reject."),
        expected_version=require_positive_int(
            payload, "expectedVersion", "Refresh the period before returning it."
        ),
        note=require_text(payload, "note", "A return reason is required."),
    )

def lock_period(
    desktop_api: ProjectManagementTimesheetsDesktopApi,
    payload: dict[str, Any],
) -> None:
    desktop_api.lock_period(
        require_text(payload, "periodId", "Choose a period to lock."),
        expected_version=require_positive_int(
            payload, "expectedVersion", "Refresh the period before locking it."
        ),
        note=optional_text(payload, "note") or "",
    )

def unlock_period(
    desktop_api: ProjectManagementTimesheetsDesktopApi,
    payload: dict[str, Any],
) -> None:
    desktop_api.unlock_period(
        require_text(payload, "periodId", "Choose a period to unlock."),
        expected_version=require_positive_int(
            payload, "expectedVersion", "Refresh the period before unlocking it."
        ),
        note=optional_text(payload, "note") or "",
    )
