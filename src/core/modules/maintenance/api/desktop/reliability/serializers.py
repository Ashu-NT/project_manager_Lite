from __future__ import annotations

from src.core.modules.maintenance.api.desktop.planner.serializers import (
    format_timestamp_label,
)
from src.core.modules.maintenance.api.desktop.reliability.models import (
    MaintenanceFailureSymptomOptionDescriptor,
    MaintenanceReliabilityInsightRowDescriptor,
    MaintenanceReliabilityRecurringRowDescriptor,
    MaintenanceReliabilitySuggestionRowDescriptor,
)
from src.core.modules.maintenance.api.desktop._support import code_name_label


def serialize_failure_symptom_option(row) -> MaintenanceFailureSymptomOptionDescriptor:
    failure_code = str(getattr(row, "failure_code", "") or "")
    name = str(getattr(row, "name", "") or "")
    return MaintenanceFailureSymptomOptionDescriptor(
        value=failure_code,
        label=code_name_label(failure_code, name),
        failure_code=failure_code,
        name=name,
        is_active=bool(getattr(row, "is_active", True)),
    )


def serialize_suggestion_row(row) -> MaintenanceReliabilitySuggestionRowDescriptor:
    return MaintenanceReliabilitySuggestionRowDescriptor(
        match_scope_label=str(getattr(row, "match_scope", "") or "").title(),
        root_cause_name=str(getattr(row, "root_cause_name", "") or "-"),
        occurrence_count=int(getattr(row, "occurrence_count", 0) or 0),
        total_downtime_minutes=int(getattr(row, "total_downtime_minutes", 0) or 0),
        latest_occurrence_at_label=format_timestamp_label(
            getattr(row, "latest_occurrence_at", None),
        ),
    )


def serialize_insight_row(row) -> MaintenanceReliabilityInsightRowDescriptor:
    return MaintenanceReliabilityInsightRowDescriptor(
        failure_name=str(getattr(row, "failure_name", "") or "-"),
        root_cause_name=str(getattr(row, "root_cause_name", "") or "-"),
        work_order_count=int(getattr(row, "work_order_count", 0) or 0),
        total_downtime_minutes=int(getattr(row, "total_downtime_minutes", 0) or 0),
        open_work_orders=int(getattr(row, "open_work_orders", 0) or 0),
    )


def serialize_recurring_row(row) -> MaintenanceReliabilityRecurringRowDescriptor:
    anchor_code = str(getattr(row, "anchor_code", "") or "")
    anchor_name = str(getattr(row, "anchor_name", "") or "")
    anchor_label = anchor_code
    if anchor_code and anchor_name:
        anchor_label = f"{anchor_code} - {anchor_name}"
    elif anchor_name:
        anchor_label = anchor_name
    mean_interval_hours = getattr(row, "mean_interval_hours", None)
    if mean_interval_hours in (None, ""):
        mean_interval_hours_label = "n/a"
    else:
        try:
            mean_interval_hours_label = f"{float(mean_interval_hours):.2f}"
        except (TypeError, ValueError):
            mean_interval_hours_label = str(mean_interval_hours)
    return MaintenanceReliabilityRecurringRowDescriptor(
        anchor_label=anchor_label or "-",
        failure_name=str(getattr(row, "failure_name", "") or "-"),
        leading_root_cause_name=str(
            getattr(row, "leading_root_cause_name", "") or "-"
        ),
        occurrence_count=int(getattr(row, "occurrence_count", 0) or 0),
        open_work_orders=int(getattr(row, "open_work_orders", 0) or 0),
        mean_interval_hours_label=mean_interval_hours_label,
    )


__all__ = [
    "serialize_failure_symptom_option",
    "serialize_insight_row",
    "serialize_recurring_row",
    "serialize_suggestion_row",
]
