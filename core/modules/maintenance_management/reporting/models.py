from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ReportMetric:
    label: str
    value: object


@dataclass(frozen=True)
class MaintenanceRootCauseInsight:
    failure_code: str
    failure_name: str
    root_cause_code: str
    root_cause_name: str
    work_order_count: int
    total_downtime_minutes: int
    average_downtime_minutes: float
    latest_occurrence_at: datetime | None = None
    open_work_orders: int = 0


@dataclass(frozen=True)
class MaintenanceRootCauseSuggestion:
    root_cause_code: str
    root_cause_name: str
    match_scope: str
    occurrence_count: int
    total_downtime_minutes: int
    latest_occurrence_at: datetime | None = None


@dataclass(frozen=True)
class MaintenanceRecurringFailurePattern:
    anchor_type: str
    anchor_id: str
    anchor_code: str
    anchor_name: str
    failure_code: str
    failure_name: str
    leading_root_cause_code: str
    leading_root_cause_name: str
    occurrence_count: int
    open_work_orders: int
    total_downtime_minutes: int
    mean_interval_hours: float | None = None
    mean_repair_hours: float | None = None
    first_occurrence_at: datetime | None = None
    last_occurrence_at: datetime | None = None


@dataclass(frozen=True)
class MaintenanceReliabilityDashboard:
    title: str
    filters: tuple[ReportMetric, ...] = field(default_factory=tuple)
    summary: tuple[ReportMetric, ...] = field(default_factory=tuple)
    backlog_by_status: tuple[ReportMetric, ...] = field(default_factory=tuple)
    backlog_by_priority: tuple[ReportMetric, ...] = field(default_factory=tuple)
    downtime_by_type: tuple[ReportMetric, ...] = field(default_factory=tuple)
    top_root_causes: tuple[MaintenanceRootCauseInsight, ...] = field(default_factory=tuple)
    recurring_failures: tuple[MaintenanceRecurringFailurePattern, ...] = field(default_factory=tuple)


__all__ = [
    "MaintenanceRecurringFailurePattern",
    "MaintenanceReliabilityDashboard",
    "MaintenanceRootCauseInsight",
    "MaintenanceRootCauseSuggestion",
    "ReportMetric",
]
