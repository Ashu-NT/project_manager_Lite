from __future__ import annotations

from decimal import Decimal

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_hours,
)
from src.core.modules.project_management.api.desktop.tasks.models.assignment import (
    TaskAssignmentDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.services.capacity_status_labels import (
    capacity_status_label,
)
from src.core.modules.project_management.api.desktop.tasks.services.resource_lookup_service import (
    resource_name_for_assignment,
)
from src.core.platform.finance.money import canonical_decimal_text


def serialize_assignment(
    assignment,
    *,
    resources_by_id: dict[str, object],
    can_manage: bool = False,
    can_accept: bool = False,
    can_decline: bool = False,
    project_resource_version: int = 1,
    capacity_fact=None,
) -> TaskAssignmentDesktopDto:
    allocated_planned_hours = Decimal(str(getattr(assignment, "allocated_planned_hours", 0) or 0))
    hours_logged = Decimal(str(getattr(assignment, "hours_logged", 0) or 0))
    remaining_planned_hours = allocated_planned_hours - hours_logged

    capacity_known = False
    capacity_status = "UNKNOWN"
    available_capacity_hours_label = ""
    committed_capacity_hours_label = ""
    capacity_headroom_hours_label = ""
    peak_utilization_percent = 0.0
    if capacity_fact is not None:
        capacity_status = capacity_fact.capacity_status
        capacity_known = capacity_fact.effective_available_capacity_hours is not None
        peak_utilization_percent = round(capacity_fact.peak_utilization_percent or 0.0, 1)
        committed_capacity_hours_label = format_hours(
            capacity_fact.resulting_committed_capacity_hours
        )
        if capacity_known:
            available_capacity_hours_label = format_hours(
                capacity_fact.effective_available_capacity_hours
            )
            capacity_headroom_hours_label = format_hours(
                capacity_fact.effective_available_capacity_hours
                - capacity_fact.resulting_committed_capacity_hours
            )

    return TaskAssignmentDesktopDto(
        id=assignment.id,
        task_id=assignment.task_id,
        resource_id=assignment.resource_id,
        resource_name=resource_name_for_assignment(
            assignment,
            resources_by_id=resources_by_id,
        ),
        allocation_percent=float(getattr(assignment, "allocation_percent", 0.0) or 0.0),
        hours_logged=canonical_decimal_text(hours_logged),
        project_resource_id=getattr(assignment, "project_resource_id", None),
        response_status=getattr(assignment, "response_status", "pending") or "pending",
        response_status_label=(getattr(assignment, "response_status", "pending") or "pending").title(),
        can_manage=bool(can_manage),
        can_accept=bool(can_accept),
        can_decline=bool(can_decline),
        allocated_planned_hours=canonical_decimal_text(allocated_planned_hours),
        version=int(getattr(assignment, "version", 1) or 1),
        project_resource_version=int(project_resource_version or 1),
        capacity_known=capacity_known,
        capacity_status=capacity_status,
        capacity_status_label=capacity_status_label(capacity_status),
        available_capacity_hours_label=available_capacity_hours_label,
        committed_capacity_hours_label=committed_capacity_hours_label,
        capacity_headroom_hours_label=capacity_headroom_hours_label,
        peak_utilization_percent=peak_utilization_percent,
        remaining_planned_hours_label=format_hours(remaining_planned_hours),
    )


__all__ = ["serialize_assignment"]
