from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from core.modules.maintenance_management.domain import MaintenanceWorkOrder, MaintenanceWorkOrderStatus
from core.modules.maintenance_management.reporting import (
    MaintenanceRecurringFailurePattern,
    MaintenanceReliabilityDashboard,
    MaintenanceRootCauseInsight,
)
from core.platform.report_runtime import MetricBlock, MetricRow, ReportDocument, ReportSection, TableBlock, TextBlock


@dataclass(frozen=True)
class MaintenanceReportLookups:
    site_codes: dict[str, str]
    asset_labels: dict[str, str]
    system_labels: dict[str, str]
    location_labels: dict[str, str]
    failure_labels: dict[str, str]


def build_backlog_report_document(
    *,
    dashboard: MaintenanceReliabilityDashboard,
    work_orders: list[MaintenanceWorkOrder],
    lookups: MaintenanceReportLookups,
) -> ReportDocument:
    overdue = [
        row
        for row in work_orders
        if row.planned_end is not None and _to_utc(row.planned_end) < datetime.now(timezone.utc)
    ]
    return ReportDocument(
        title="Maintenance Backlog Report",
        sections=(
            ReportSection(
                title="Summary",
                blocks=(
                    MetricBlock(
                        title="Backlog Summary",
                        rows=(
                            MetricRow("Open work orders", len(work_orders)),
                            MetricRow("Overdue work orders", len(overdue)),
                            MetricRow(
                                "Emergency work orders",
                                sum(1 for row in work_orders if getattr(row.priority, "value", row.priority) == "EMERGENCY"),
                            ),
                            MetricRow(
                                "Shutdown-required work orders",
                                sum(1 for row in work_orders if row.requires_shutdown),
                            ),
                        ),
                    ),
                    MetricBlock(
                        title="Reliability Snapshot",
                        rows=tuple(MetricRow(metric.label, metric.value) for metric in dashboard.summary),
                    ),
                ),
            ),
            ReportSection(
                title="Backlog",
                blocks=(
                    TableBlock(
                        title="Open Work Orders",
                        columns=(
                            "Work Order",
                            "Status",
                            "Priority",
                            "Type",
                            "Site",
                            "Asset",
                            "System",
                            "Location",
                            "Planned End",
                            "Failure Code",
                            "Root Cause",
                        ),
                        rows=tuple(
                            (
                                row.work_order_code,
                                getattr(row.status, "value", row.status),
                                getattr(row.priority, "value", row.priority),
                                getattr(row.work_order_type, "value", row.work_order_type),
                                lookups.site_codes.get(row.site_id, ""),
                                lookups.asset_labels.get(row.asset_id or "", ""),
                                lookups.system_labels.get(row.system_id or "", ""),
                                lookups.location_labels.get(row.location_id or "", ""),
                                _timestamp(row.planned_end),
                                _failure_label(lookups, row.failure_code),
                                _failure_label(lookups, row.root_cause_code),
                            )
                            for row in work_orders
                        ),
                    ),
                ),
            ),
            ReportSection(
                title="Reliability Signals",
                blocks=(
                    _root_cause_table("Top Root Causes", dashboard.top_root_causes),
                    _recurring_failure_table("Recurring Failure Patterns", dashboard.recurring_failures),
                ),
            ),
        ),
    )


def build_downtime_report_document(
    *,
    dashboard: MaintenanceReliabilityDashboard,
    downtime_rows: list[tuple],
    recurring_patterns: list[MaintenanceRecurringFailurePattern],
) -> ReportDocument:
    return ReportDocument(
        title="Maintenance Downtime Report",
        sections=(
            ReportSection(
                title="Summary",
                blocks=(
                    MetricBlock(
                        title="Downtime Snapshot",
                        rows=tuple(MetricRow(metric.label, metric.value) for metric in dashboard.summary),
                    ),
                    MetricBlock(
                        title="Downtime By Type",
                        rows=tuple(MetricRow(metric.label, metric.value) for metric in dashboard.downtime_by_type),
                    ),
                ),
            ),
            ReportSection(
                title="Events",
                blocks=(
                    TableBlock(
                        title="Downtime Events",
                        columns=(
                            "Started",
                            "Ended",
                            "Duration Min",
                            "Type",
                            "Reason",
                            "Work Order",
                            "Asset",
                            "System",
                            "Impact Notes",
                        ),
                        rows=tuple(downtime_rows),
                    ),
                ),
            ),
            ReportSection(
                title="Recurring Impact",
                blocks=(
                    _recurring_failure_table("Recurring Downtime Patterns", recurring_patterns),
                ),
            ),
        ),
    )


def build_execution_overview_report_document(
    *,
    work_orders: list[MaintenanceWorkOrder],
    lookups: MaintenanceReportLookups,
    days: int,
) -> ReportDocument:
    completed = [row for row in work_orders if row.status in {MaintenanceWorkOrderStatus.COMPLETED, MaintenanceWorkOrderStatus.VERIFIED, MaintenanceWorkOrderStatus.CLOSED}]
    in_progress = [row for row in work_orders if row.status == MaintenanceWorkOrderStatus.IN_PROGRESS]
    release_ready = [
        row
        for row in work_orders
        if row.status in {
            MaintenanceWorkOrderStatus.RELEASED,
            MaintenanceWorkOrderStatus.SCHEDULED,
        }
    ]
    start_lead_values = [
        (_to_utc(row.actual_start) - _requested_at(row)).total_seconds() / 3600.0
        for row in work_orders
        if _requested_at(row) is not None and row.actual_start is not None
    ]
    completion_lead_values = [
        (_completion_at(row) - _requested_at(row)).total_seconds() / 3600.0
        for row in completed
        if _requested_at(row) is not None and _completion_at(row) is not None
    ]
    repair_values = [
        (_to_utc(row.actual_end) - _to_utc(row.actual_start)).total_seconds() / 3600.0
        for row in work_orders
        if row.actual_start is not None and row.actual_end is not None
    ]
    return ReportDocument(
        title="Maintenance Execution Overview",
        sections=(
            ReportSection(
                title="Summary",
                blocks=(
                    MetricBlock(
                        title="Execution KPIs",
                        rows=(
                            MetricRow("Window", f"{days} days"),
                            MetricRow("Work orders in window", len(work_orders)),
                            MetricRow("Completed / closed", len(completed)),
                            MetricRow("In progress", len(in_progress)),
                            MetricRow("Release ready", len(release_ready)),
                            MetricRow("Average start lead hours", _mean(start_lead_values)),
                            MetricRow("Average completion lead hours", _mean(completion_lead_values)),
                            MetricRow("Average repair hours", _mean(repair_values)),
                        ),
                    ),
                ),
            ),
            ReportSection(
                title="Execution Detail",
                blocks=(
                    TableBlock(
                        title="Work Order Execution",
                        columns=(
                            "Work Order",
                            "Status",
                            "Priority",
                            "Site",
                            "Asset",
                            "Requested",
                            "Actual Start",
                            "Actual End",
                            "Downtime Min",
                            "Assigned Employee",
                        ),
                        rows=tuple(
                            (
                                row.work_order_code,
                                getattr(row.status, "value", row.status),
                                getattr(row.priority, "value", row.priority),
                                lookups.site_codes.get(row.site_id, ""),
                                lookups.asset_labels.get(row.asset_id or "", ""),
                                _timestamp(_requested_at(row)),
                                _timestamp(row.actual_start),
                                _timestamp(row.actual_end),
                                int(row.downtime_minutes or 0),
                                row.assigned_employee_id or "",
                            )
                            for row in work_orders
                        ),
                    ),
                ),
            ),
        ),
    )


def build_pm_compliance_report_document(
    *,
    preventive_rows: list[MaintenanceWorkOrder],
    lookups: MaintenanceReportLookups,
    days: int,
) -> ReportDocument:
    now = datetime.now(timezone.utc)
    due_rows = [
        row
        for row in preventive_rows
        if row.planned_end is not None and _to_utc(row.planned_end) <= now
    ]
    compliant_rows = [
        row
        for row in due_rows
        if row.status in {MaintenanceWorkOrderStatus.COMPLETED, MaintenanceWorkOrderStatus.VERIFIED, MaintenanceWorkOrderStatus.CLOSED}
    ]
    overdue_rows = [
        row
        for row in due_rows
        if row.status not in {MaintenanceWorkOrderStatus.COMPLETED, MaintenanceWorkOrderStatus.VERIFIED, MaintenanceWorkOrderStatus.CLOSED}
    ]
    compliance_rate = round((len(compliant_rows) / len(due_rows)) * 100.0, 2) if due_rows else 100.0
    return ReportDocument(
        title="Preventive Maintenance Compliance Report",
        sections=(
            ReportSection(
                title="Summary",
                blocks=(
                    MetricBlock(
                        title="Compliance KPIs",
                        rows=(
                            MetricRow("Window", f"{days} days"),
                            MetricRow("Preventive work orders", len(preventive_rows)),
                            MetricRow("Due preventive work orders", len(due_rows)),
                            MetricRow("Compliant preventive work orders", len(compliant_rows)),
                            MetricRow("Overdue preventive work orders", len(overdue_rows)),
                            MetricRow("Compliance rate %", compliance_rate),
                        ),
                    ),
                    TextBlock(
                        title="Interpretation",
                        body="Compliance is based on preventive work orders with due dates in the selected window and counts completed, verified, or closed work as compliant.",
                    ),
                ),
            ),
            ReportSection(
                title="Preventive Work",
                blocks=(
                    TableBlock(
                        title="Preventive Work Orders",
                        columns=(
                            "Work Order",
                            "Status",
                            "Priority",
                            "Site",
                            "Asset",
                            "Planned Start",
                            "Planned End",
                            "Actual End",
                            "Overdue",
                        ),
                        rows=tuple(
                            (
                                row.work_order_code,
                                getattr(row.status, "value", row.status),
                                getattr(row.priority, "value", row.priority),
                                lookups.site_codes.get(row.site_id, ""),
                                lookups.asset_labels.get(row.asset_id or "", ""),
                                _timestamp(row.planned_start),
                                _timestamp(row.planned_end),
                                _timestamp(row.actual_end),
                                "Yes"
                                if row.planned_end is not None
                                and _to_utc(row.planned_end) <= now
                                and row.status not in {MaintenanceWorkOrderStatus.COMPLETED, MaintenanceWorkOrderStatus.VERIFIED, MaintenanceWorkOrderStatus.CLOSED}
                                else "No",
                            )
                            for row in preventive_rows
                        ),
                    ),
                ),
            ),
        ),
    )


def _root_cause_table(title: str, rows: tuple[MaintenanceRootCauseInsight, ...] | list[MaintenanceRootCauseInsight]) -> TableBlock:
    return TableBlock(
        title=title,
        columns=(
            "Failure",
            "Root Cause",
            "Work Orders",
            "Downtime Min",
            "Avg Downtime",
            "Open Work",
            "Latest",
        ),
        rows=tuple(
            (
                row.failure_name or row.failure_code,
                row.root_cause_name or row.root_cause_code,
                row.work_order_count,
                row.total_downtime_minutes,
                row.average_downtime_minutes,
                row.open_work_orders,
                _timestamp(row.latest_occurrence_at),
            )
            for row in rows
        ),
    )


def _recurring_failure_table(
    title: str,
    rows: tuple[MaintenanceRecurringFailurePattern, ...] | list[MaintenanceRecurringFailurePattern],
) -> TableBlock:
    return TableBlock(
        title=title,
        columns=(
            "Anchor",
            "Failure",
            "Leading Root Cause",
            "Occurrences",
            "Open Work",
            "Downtime Min",
            "Mean Interval Hr",
            "Mean Repair Hr",
            "Last Occurrence",
        ),
        rows=tuple(
            (
                row.anchor_name or row.anchor_code,
                row.failure_name or row.failure_code,
                row.leading_root_cause_name or row.leading_root_cause_code,
                row.occurrence_count,
                row.open_work_orders,
                row.total_downtime_minutes,
                row.mean_interval_hours if row.mean_interval_hours is not None else "",
                row.mean_repair_hours if row.mean_repair_hours is not None else "",
                _timestamp(row.last_occurrence_at),
            )
            for row in rows
        ),
    )


def _failure_label(lookups: MaintenanceReportLookups, code: str) -> str:
    if not code:
        return ""
    return lookups.failure_labels.get(code, code)


def _completion_at(row: MaintenanceWorkOrder):
    return _to_utc(row.closed_at or row.actual_end)


def _requested_at(row: MaintenanceWorkOrder):
    return _to_utc(getattr(row, "created_at", None))


def _mean(values: list[float]) -> float | str:
    if not values:
        return "n/a"
    return round(sum(values) / len(values), 2)


def _timestamp(value) -> str:
    resolved = _to_utc(value)
    return resolved.isoformat() if resolved is not None else ""


def _to_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


__all__ = [
    "MaintenanceReportLookups",
    "build_backlog_report_document",
    "build_downtime_report_document",
    "build_execution_overview_report_document",
    "build_pm_compliance_report_document",
]
