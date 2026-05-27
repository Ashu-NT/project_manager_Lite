from __future__ import annotations

from src.core.modules.maintenance.api.desktop.dashboard.models import (
    MaintenanceDashboardBacklogRowDescriptor,
    MaintenanceDashboardRecurringRowDescriptor,
    MaintenanceDashboardRootCauseRowDescriptor,
)
from src.core.modules.maintenance.api.desktop.planner.serializers import (
    format_timestamp_label,
)


def serialize_backlog_row(*, group: str, metric) -> MaintenanceDashboardBacklogRowDescriptor:
    return MaintenanceDashboardBacklogRowDescriptor(
        group=group,
        label=str(getattr(metric, "label", "") or "-"),
        value=str(getattr(metric, "value", 0)),
    )


def serialize_root_cause_row(row) -> MaintenanceDashboardRootCauseRowDescriptor:
    return MaintenanceDashboardRootCauseRowDescriptor(
        failure_name=str(getattr(row, "failure_name", "") or "-"),
        root_cause_name=str(getattr(row, "root_cause_name", "") or "-"),
        work_order_count=int(getattr(row, "work_order_count", 0) or 0),
        total_downtime_minutes=int(getattr(row, "total_downtime_minutes", 0) or 0),
        latest_occurrence_at_label=format_timestamp_label(
            getattr(row, "latest_occurrence_at", None),
        ),
        open_work_orders=int(getattr(row, "open_work_orders", 0) or 0),
    )


def serialize_recurring_row(row) -> MaintenanceDashboardRecurringRowDescriptor:
    anchor_code = str(getattr(row, "anchor_code", "") or "")
    anchor_name = str(getattr(row, "anchor_name", "") or "")
    anchor_label = anchor_code
    if anchor_code and anchor_name:
        anchor_label = f"{anchor_code} - {anchor_name}"
    elif anchor_name:
        anchor_label = anchor_name
    return MaintenanceDashboardRecurringRowDescriptor(
        anchor_label=anchor_label or "-",
        failure_name=str(getattr(row, "failure_name", "") or "-"),
        leading_root_cause_name=str(
            getattr(row, "leading_root_cause_name", "") or "-"
        ),
        occurrence_count=int(getattr(row, "occurrence_count", 0) or 0),
        open_work_orders=int(getattr(row, "open_work_orders", 0) or 0),
        total_downtime_minutes=int(getattr(row, "total_downtime_minutes", 0) or 0),
        mean_interval_hours_label=_metric_text(getattr(row, "mean_interval_hours", None)),
    )


def _metric_text(value) -> str:
    if value in (None, ""):
        return "n/a"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


__all__ = [
    "serialize_backlog_row",
    "serialize_recurring_row",
    "serialize_root_cause_row",
]
