from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementSchedulingDesktopApi,
    SchedulingBaselineApproveCommand,
    SchedulingBaselineCreateCommand,
    SchedulingBaselineRejectCommand,
    SchedulingBaselineSubmitCommand,
    SchedulingWorkingDayCalculationCommand,
)

from .validation import optional_text, require_date, require_int, require_text

def create_baseline(
    desktop_api: ProjectManagementSchedulingDesktopApi,
    payload: dict[str, Any],
) -> None:
    desktop_api.create_baseline(
        SchedulingBaselineCreateCommand(
            project_id=require_text(
                payload,
                "projectId",
                "Select a project before creating a baseline.",
            ),
            name=optional_text(payload, "name") or "Baseline",
        )
    )

def delete_baseline(
    desktop_api: ProjectManagementSchedulingDesktopApi,
    baseline_id: str,
) -> None:
    normalized_id = (baseline_id or "").strip()
    if not normalized_id:
        raise ValueError("Select a baseline before deleting it.")
    desktop_api.delete_baseline(normalized_id)

def submit_baseline(
    desktop_api: ProjectManagementSchedulingDesktopApi,
    baseline_id: str,
) -> None:
    normalized_id = (baseline_id or "").strip()
    if not normalized_id:
        raise ValueError("Select a baseline before submitting it.")
    desktop_api.submit_baseline(
        SchedulingBaselineSubmitCommand(baseline_id=normalized_id)
    )

def approve_baseline(
    desktop_api: ProjectManagementSchedulingDesktopApi,
    baseline_id: str,
) -> None:
    normalized_id = (baseline_id or "").strip()
    if not normalized_id:
        raise ValueError("Select a baseline before approving it.")
    desktop_api.approve_baseline(
        SchedulingBaselineApproveCommand(baseline_id=normalized_id)
    )

def reject_baseline(
    desktop_api: ProjectManagementSchedulingDesktopApi,
    baseline_id: str,
) -> None:
    normalized_id = (baseline_id or "").strip()
    if not normalized_id:
        raise ValueError("Select a baseline before rejecting it.")
    desktop_api.reject_baseline(
        SchedulingBaselineRejectCommand(baseline_id=normalized_id)
    )

def recalculate_schedule(
    desktop_api: ProjectManagementSchedulingDesktopApi,
    project_id: str,
) -> None:
    normalized_id = (project_id or "").strip()
    if not normalized_id:
        raise ValueError("Select a project before recalculating the schedule.")
    desktop_api.recalculate_schedule(normalized_id)

def apply_resource_leveling(
    desktop_api: ProjectManagementSchedulingDesktopApi,
    project_id: str,
) -> None:
    normalized_id = (project_id or "").strip()
    if not normalized_id:
        raise ValueError("Select a project before applying resource leveling.")
    desktop_api.apply_resource_leveling(normalized_id)

def calculate_working_days(
    desktop_api: ProjectManagementSchedulingDesktopApi,
    payload: dict[str, Any],
) -> str:
    calculation = desktop_api.calculate_working_days(
        SchedulingWorkingDayCalculationCommand(
            start_date=require_date(
                payload,
                "startDate",
                "Start date must use YYYY-MM-DD.",
            ),
            working_days=require_int(
                payload,
                "workingDays",
                "Working days must be a whole number.",
            ),
        )
    )
    return (
        f"Result: Start {calculation.start_date.isoformat()} + "
        f"{calculation.working_days} working days = "
        f"{calculation.result_date.isoformat()} "
        f"(skipped {calculation.skipped_non_working_days} non-working days)."
    )

__all__ = [
    "create_baseline",
    "delete_baseline",
    "submit_baseline",
    "approve_baseline",
    "reject_baseline",
    "recalculate_schedule",
    "apply_resource_leveling",
    "calculate_working_days",
]
