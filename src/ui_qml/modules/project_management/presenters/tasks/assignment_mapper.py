from __future__ import annotations

from decimal import Decimal

from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskRecordViewModel,
    TaskSelectorOptionViewModel,
)
from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_decimal_amount,
)


def to_assignment_record_view_model(assignment) -> TaskRecordViewModel:
    allocation_percent = float(assignment.allocation_percent or 0.0)
    hours_logged = assignment.hours_logged or "0"
    hours_label = format_decimal_amount(hours_logged, grouping=False)
    planned_hours = getattr(assignment, "allocated_planned_hours", None) or "0"
    planned_label = format_decimal_amount(planned_hours, grouping=False)
    remaining = _decimal(planned_hours) - _decimal(hours_logged)
    remaining_label = format_decimal_amount(str(remaining), grouping=False)
    state = {
        "assignmentId": assignment.id,
        "taskId": assignment.task_id,
        "resourceId": assignment.resource_id,
        "resourceName": assignment.resource_name,
        "allocationPercent": f"{allocation_percent:.1f}",
        "hoursLogged": hours_logged,
        "plannedHours": planned_hours,
        "remainingHours": str(remaining),
        "projectResourceId": assignment.project_resource_id or "",
        "responseStatus": assignment.response_status,
        "responseStatusLabel": assignment.response_status_label,
        "canManage": bool(assignment.can_manage),
        "canAccept": bool(assignment.can_accept),
        "canDecline": bool(assignment.can_decline),
        "version": int(getattr(assignment, "version", 1) or 1),
        "projectResourceVersion": int(
            getattr(assignment, "project_resource_version", 1) or 1
        ),
        # Authoritative calendar-based capacity facts for this assignment's
        # own current commitment (docs §44) -- rendered as-is, never
        # recalculated in QML.
        "capacityKnown": bool(getattr(assignment, "capacity_known", False)),
        "capacityStatus": getattr(assignment, "capacity_status", "UNKNOWN"),
        "capacityStatusLabel": getattr(
            assignment, "capacity_status_label", "Capacity unknown"
        ),
        "availableCapacityLabel": getattr(
            assignment, "available_capacity_hours_label", ""
        ),
        "committedCapacityLabel": getattr(
            assignment, "committed_capacity_hours_label", ""
        ),
        "capacityHeadroomLabel": getattr(
            assignment, "capacity_headroom_hours_label", ""
        ),
        "peakUtilizationPercent": float(
            getattr(assignment, "peak_utilization_percent", 0.0) or 0.0
        ),
        "remainingPlannedLabel": getattr(
            assignment, "remaining_planned_hours_label", f"{remaining_label} h"
        ),
    }
    return TaskRecordViewModel(
        id=assignment.id,
        title=assignment.resource_name,
        status_label=assignment.response_status_label,
        subtitle="Resource assignment",
        supporting_text=f"{hours_label} h logged of {planned_label} h planned "
        f"({remaining_label} h remaining)",
        meta_text=f"{allocation_percent:.1f}%",
        state=state,
    )


def to_assignment_table_row(view_model: TaskRecordViewModel) -> dict[str, object]:
    """Flatten an assignment's TaskRecordViewModel.state into the top-level
    row shape the shared DataTable/DynamicTableModel expects (columns bind
    to top-level row keys, not nested state) -- see §5's Resource/
    Allocation/Planned Work/Actual/Remaining/Capacity Status columns."""
    state = view_model.state or {}
    return {
        "id": view_model.id,
        "resourceName": view_model.title,
        "responseStatusLabel": view_model.status_label,
        "allocationLabel": f"{state.get('allocationPercent', '0')}%",
        "plannedLabel": f"{format_decimal_amount(state.get('plannedHours', '0'), grouping=False)} h",
        "actualLabel": f"{format_decimal_amount(state.get('hoursLogged', '0'), grouping=False)} h",
        "remainingLabel": state.get("remainingPlannedLabel", "0 h"),
        "capacityStatus": state.get("capacityStatus", "UNKNOWN"),
        "capacityStatusLabel": state.get("capacityStatusLabel", "Capacity unknown"),
        "state": state,
    }


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def build_assignment_options(
    desktop_api,
    project_id: str | None,
) -> tuple[TaskSelectorOptionViewModel, ...]:
    try:
        options = desktop_api.list_project_resources(project_id)
    except Exception:
        return ()
    return tuple(
        TaskSelectorOptionViewModel(value=option.value, label=option.label)
        for option in options
    )


def build_time_assignment_options(
    assignments,
) -> tuple[TaskSelectorOptionViewModel, ...]:
    options: list[TaskSelectorOptionViewModel] = []
    for assignment in assignments:
        resource_name = str(
            getattr(assignment, "resource_name", "")
            or getattr(assignment, "resource_id", "")
            or "Assignment"
        )
        allocation_percent = float(getattr(assignment, "allocation_percent", 0.0) or 0.0)
        label = (
            f"{resource_name} | {allocation_percent:g}% allocation"
            if allocation_percent > 0
            else resource_name
        )
        options.append(
            TaskSelectorOptionViewModel(
                value=str(getattr(assignment, "id", "") or ""),
                label=label,
            )
        )
    return tuple(options)
