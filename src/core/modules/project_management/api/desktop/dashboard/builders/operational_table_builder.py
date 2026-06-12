"""Operational table and tab builders."""

from __future__ import annotations
from datetime import date
from typing import Any

from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
    as_register_entry_severity,
    as_register_entry_status,
    as_register_entry_type,
)
from src.core.platform.approval.domain import ApprovalStatus
from src.core.modules.project_management.api.desktop.dashboard.models.tables import (
    ProjectDashboardOperationalTabDescriptor,
    ProjectDashboardOperationalTableDescriptor,
    ProjectDashboardTableColumnDescriptor,
    ProjectDashboardTableRowDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.formatters.number_formatter import (
    fmt_float, fmt_int, fmt_percent,
)
from src.core.modules.project_management.api.desktop.dashboard.formatters.date_formatter import (
    coerce_utc_datetime, fmt_date, fmt_utc_datetime,
)
from src.core.modules.project_management.api.desktop.dashboard.formatters.period_formatter import (
    period_cutoff_date,
)

_COL = ProjectDashboardTableColumnDescriptor


def build_preview_operational_tables() -> tuple[ProjectDashboardOperationalTableDescriptor, ...]:
    preview_columns = (
        _COL("title", "Item", 3, 220, True),
        _COL("statusLabel", "Status", 0, 96, False, True, "status"),
        _COL("summary", "Summary", 2, 180),
    )
    return (
        ProjectDashboardOperationalTableDescriptor(
            id="delayed_tasks", title="Delayed Tasks",
            subtitle="Operational rows appear here when the dashboard API is connected.",
            empty_state="No delayed-task rows are available in preview mode.",
            columns=preview_columns,
        ),
    )


def build_operational_tabs(
    tables: tuple[ProjectDashboardOperationalTableDescriptor, ...],
) -> tuple[ProjectDashboardOperationalTabDescriptor, ...]:
    return tuple(
        ProjectDashboardOperationalTabDescriptor(
            id=t.id, label=t.title, count=len(t.rows),
            route_id=(t.rows[0].route_id if t.rows else ""),
        )
        for t in tables
    )


def build_operational_tables(
    *,
    dashboard_data: Any,
    pending_approvals: tuple[Any, ...],
    selected_period_key: str,
    portfolio_mode: bool,
    register_service=None,
) -> tuple[ProjectDashboardOperationalTableDescriptor, ...]:
    if portfolio_mode:
        return (
            _build_portfolio_health_table(dashboard_data),
            _build_portfolio_delayed_table(dashboard_data, selected_period_key=selected_period_key),
            _build_portfolio_budget_table(dashboard_data),
            _build_resource_overloads_table(dashboard_data),
            _build_pending_approvals_table(pending_approvals),
            _build_milestones_table(dashboard_data),
        )
    return (
        _build_delayed_tasks_table(dashboard_data),
        _build_high_risks_table(dashboard_data, register_service=register_service),
        _build_budget_variances_table(dashboard_data),
        _build_resource_overloads_table(dashboard_data),
        _build_pending_approvals_table(pending_approvals),
        _build_milestones_table(dashboard_data),
    )


def _build_delayed_tasks_table(dashboard_data: Any) -> ProjectDashboardOperationalTableDescriptor:
    rows = tuple(getattr(dashboard_data, "critical_watchlist", []) or [])
    project_id = str(getattr(getattr(dashboard_data, "kpi", None), "project_id", "") or "")
    return ProjectDashboardOperationalTableDescriptor(
        id="delayed_tasks", title="Delayed Tasks",
        subtitle="Critical-path and low-float tasks that need scheduling intervention.",
        empty_state="No delayed or critical-path tasks are active right now.",
        columns=(_COL("taskName", "Activity", 3, 220, True), _COL("owner", "Owner", 2, 140), _COL("finish", "Finish", 1, 108, True), _COL("float", "Float", 1, 90), _COL("late", "Late", 1, 90), _COL("statusLabel", "Status", 0, 96, False, True, "status")),
        rows=tuple(
            ProjectDashboardTableRowDescriptor(id=r.task_id, route_id="project_management.tasks", state={"taskId": r.task_id, "projectId": project_id}, values={"taskName": r.task_name, "owner": r.owner_name or "Unassigned", "finish": fmt_date(r.finish_date), "float": f"{fmt_int(r.total_float_days or 0)} d", "late": f"{fmt_int(r.late_by_days or 0)} d", "statusLabel": r.status_label})
            for r in rows
        ),
    )


def _build_portfolio_delayed_table(dashboard_data: Any, *, selected_period_key: str) -> ProjectDashboardOperationalTableDescriptor:
    rows = list(getattr(dashboard_data, "upcoming_tasks", []) or [])
    cutoff = period_cutoff_date(selected_period_key)
    if cutoff is not None:
        rows = [r for r in rows if r.start_date is None or r.start_date >= cutoff]
    return ProjectDashboardOperationalTableDescriptor(
        id="delayed_tasks", title="Delayed Tasks",
        subtitle="Cross-project upcoming and delayed work in the selected horizon.",
        empty_state="No cross-project delayed tasks are visible right now.",
        columns=(_COL("taskName", "Task", 3, 220, True), _COL("start", "Start", 1, 108, True), _COL("finish", "Finish", 1, 108, True), _COL("owner", "Owner", 2, 140), _COL("statusLabel", "Status", 0, 96, False, True, "status")),
        rows=tuple(
            ProjectDashboardTableRowDescriptor(id=r.task_id, route_id="project_management.tasks", state={"taskId": r.task_id, "projectId": getattr(r, "project_id", "")}, values={"taskName": r.name, "start": fmt_date(r.start_date), "finish": fmt_date(r.end_date), "owner": r.main_resource or "Unassigned", "statusLabel": "Late" if r.is_late else "Tracked"})
            for r in rows
        ),
    )


def _build_high_risks_table(dashboard_data: Any, *, register_service=None) -> ProjectDashboardOperationalTableDescriptor:
    project_id = str(getattr(getattr(dashboard_data, "kpi", None), "project_id", "") or "")
    risk_rows: list[Any] = []
    if register_service is not None and project_id:
        try:
            risk_rows = sorted(
                register_service.list_entries(project_id=project_id, entry_type=RegisterEntryType.RISK),
                key=lambda i: (0 if i.severity == RegisterEntrySeverity.CRITICAL else 1, 0 if i.status == RegisterEntryStatus.OPEN else 1, i.due_date or date.max, str(i.title or "").casefold()),
            )
        except Exception:
            risk_rows = []
    return ProjectDashboardOperationalTableDescriptor(
        id="high_risks", title="High Risks",
        subtitle="Register risks that need active mitigation and escalation follow-through.",
        empty_state="No high-risk register entries are visible right now.",
        columns=(_COL("title", "Risk", 3, 220, True), _COL("severityLabel", "Severity", 0, 96, False, True, "status"), _COL("owner", "Owner", 2, 140), _COL("dueDate", "Due", 1, 108, True), _COL("statusLabel", "Status", 0, 110, False, True, "status"), _COL("response", "Response", 3, 220)),
        rows=tuple(
            ProjectDashboardTableRowDescriptor(id=i.id, route_id="project_management.register", state={"entryId": i.id, "projectId": i.project_id}, values={"title": i.title, "severityLabel": as_register_entry_severity(i.severity).value.title(), "owner": i.owner_name or "Unassigned", "dueDate": fmt_date(i.due_date), "statusLabel": as_register_entry_status(i.status).value.replace("_", " ").title(), "response": i.response_plan or i.impact_summary or i.description or ""})
            for i in risk_rows
            if i.severity in (RegisterEntrySeverity.HIGH, RegisterEntrySeverity.CRITICAL) and i.status in (RegisterEntryStatus.OPEN, RegisterEntryStatus.IN_REVIEW)
        ),
    )


def _build_portfolio_health_table(dashboard_data: Any) -> ProjectDashboardOperationalTableDescriptor:
    rankings = tuple(getattr(getattr(dashboard_data, "portfolio", None), "project_rankings", []) or [])
    return ProjectDashboardOperationalTableDescriptor(
        id="project_health", title="Projects at Risk",
        subtitle="Portfolio ranking by delivery pressure, late tasks, and cost variance.",
        empty_state="No project ranking data is available yet.",
        columns=(_COL("projectName", "Project", 3, 220, True), _COL("projectStatus", "Status", 0, 96, False, True, "status"), _COL("progress", "Progress", 1, 100), _COL("late", "Late", 1, 90), _COL("critical", "Critical", 1, 90), _COL("riskScore", "Risk Score", 1, 100, True), _COL("costVariance", "Cost Var.", 1, 110, True)),
        rows=tuple(
            ProjectDashboardTableRowDescriptor(id=r.project_id, route_id="project_management.projects", state={"projectId": r.project_id}, values={"projectName": r.project_name, "projectStatus": r.project_status, "progress": fmt_percent(r.progress_percent, 0), "late": fmt_int(r.late_tasks), "critical": fmt_int(r.critical_tasks), "riskScore": fmt_float(r.risk_score, 1), "costVariance": fmt_float(r.cost_variance, 0)})
            for r in rankings
        ),
    )


def _build_budget_variances_table(dashboard_data: Any) -> ProjectDashboardOperationalTableDescriptor:
    sources = getattr(dashboard_data, "cost_sources", None)
    rows = tuple(getattr(sources, "rows", []) or []) if sources is not None else ()
    return ProjectDashboardOperationalTableDescriptor(
        id="budget_variances", title="Budget Variances",
        subtitle="Budget lines with actual, committed, and planned cost visibility.",
        empty_state="No budget variance rows are available yet.",
        columns=(_COL("source", "Budget Line", 3, 200, True), _COL("planned", "Planned", 1, 110, True), _COL("actual", "Actual", 1, 110, True), _COL("variance", "Variance", 1, 110, True), _COL("committed", "Committed", 1, 110, True), _COL("statusLabel", "Status", 0, 96, False, True, "status")),
        rows=tuple(
            ProjectDashboardTableRowDescriptor(id=f"cost-source-{idx}", route_id="project_management.financials", values={"source": r.source_label, "planned": fmt_float(r.planned, 0), "actual": fmt_float(r.actual, 0), "variance": fmt_float(float(r.actual or 0.0) - float(r.planned or 0.0), 0), "committed": fmt_float(r.committed, 0), "statusLabel": "Watch" if float(r.actual or 0.0) > float(r.planned or 0.0) else "Healthy"})
            for idx, r in enumerate(rows, start=1)
        ),
    )


def _build_portfolio_budget_table(dashboard_data: Any) -> ProjectDashboardOperationalTableDescriptor:
    rankings = tuple(getattr(getattr(dashboard_data, "portfolio", None), "project_rankings", []) or [])
    return ProjectDashboardOperationalTableDescriptor(
        id="budget_variances", title="Budget Variances",
        subtitle="Projects with the highest portfolio cost-variance exposure.",
        empty_state="No portfolio budget-variance rows are available yet.",
        columns=(_COL("projectName", "Project", 3, 220, True), _COL("projectStatus", "Status", 0, 96, False, True, "status"), _COL("costVariance", "Cost Var.", 1, 110, True), _COL("late", "Late", 1, 90, True), _COL("critical", "Critical", 1, 90, True)),
        rows=tuple(
            ProjectDashboardTableRowDescriptor(id=r.project_id, route_id="project_management.financials", state={"projectId": r.project_id}, values={"projectName": r.project_name, "projectStatus": r.project_status, "costVariance": fmt_float(r.cost_variance, 0), "late": fmt_int(r.late_tasks), "critical": fmt_int(r.critical_tasks)})
            for r in rankings
        ),
    )


def _build_resource_overloads_table(dashboard_data: Any) -> ProjectDashboardOperationalTableDescriptor:
    rows = tuple(getattr(dashboard_data, "resource_load", []) or [])

    def _util(r):
        return float(getattr(r, "utilization_percent", getattr(r, "total_allocation_percent", 0.0)) or 0.0)

    return ProjectDashboardOperationalTableDescriptor(
        id="resource_overloads", title="Resource Overloads",
        subtitle="Utilization and overload hotspots across assigned delivery resources.",
        empty_state="No resource loading data is available yet.",
        columns=(_COL("resourceName", "Resource", 3, 180, True), _COL("utilization", "Utilization", 2, 180, False, True, "progress"), _COL("allocation", "Allocation", 1, 100), _COL("capacity", "Capacity", 1, 100), _COL("tasks", "Tasks", 1, 80, True), _COL("statusLabel", "Status", 0, 96, False, True, "status")),
        rows=tuple(
            ProjectDashboardTableRowDescriptor(id=r.resource_id, route_id="project_management.resources", state={"resourceId": r.resource_id}, values={"resourceName": r.resource_name, "utilization": {"value": min(max(_util(r) / 100.0, 0.0), 2.0), "label": fmt_percent(_util(r), 0)}, "allocation": fmt_percent(r.total_allocation_percent, 0), "capacity": fmt_percent(r.capacity_percent, 0), "tasks": fmt_int(r.tasks_count), "statusLabel": "Overloaded" if _util(r) > 100.0 else "Balanced"})
            for r in rows
        ),
    )


def _build_pending_approvals_table(pending_approvals: tuple[Any, ...]) -> ProjectDashboardOperationalTableDescriptor:
    from src.api.desktop.platform._approval_labels import approval_context_label, approval_display_label, approval_module_label
    return ProjectDashboardOperationalTableDescriptor(
        id="pending_approvals", title="Pending Approvals",
        subtitle="Governed changes waiting for decision or application.",
        empty_state="No pending approvals are active right now.",
        columns=(_COL("request", "Request", 3, 240, True), _COL("module", "Module", 1, 120), _COL("context", "Context", 2, 180), _COL("requestedBy", "Requested By", 1, 120), _COL("requestedAt", "Requested At", 1, 132, True), _COL("statusLabel", "Status", 0, 96, False, True, "status")),
        rows=tuple(
            ProjectDashboardTableRowDescriptor(id=req.id, route_id="platform.control", state={"requestId": req.id, "projectId": req.project_id or ""}, values={"request": approval_display_label(req), "module": approval_module_label(req), "context": approval_context_label(req), "requestedBy": req.requested_by_username or "Unknown", "requestedAt": fmt_utc_datetime(coerce_utc_datetime(getattr(req, "requested_at", None))), "statusLabel": str(getattr(getattr(req, "status", ApprovalStatus.PENDING), "value", getattr(req, "status", ApprovalStatus.PENDING))).replace("_", " ").title()})
            for req in pending_approvals
        ),
    )


def _build_milestones_table(dashboard_data: Any) -> ProjectDashboardOperationalTableDescriptor:
    rows = tuple(getattr(dashboard_data, "milestone_health", []) or [])
    project_id = str(getattr(getattr(dashboard_data, "kpi", None), "project_id", "") or "")
    return ProjectDashboardOperationalTableDescriptor(
        id="milestones", title="Milestone Health",
        subtitle="Delivery checkpoints and schedule slips that require planning attention.",
        empty_state="No milestone health rows are available yet.",
        columns=(_COL("milestone", "Milestone", 3, 220, True), _COL("owner", "Owner", 2, 140), _COL("target", "Target", 1, 108, True), _COL("slip", "Slip", 1, 90, True), _COL("statusLabel", "Status", 0, 96, False, True, "status")),
        rows=tuple(
            ProjectDashboardTableRowDescriptor(id=r.task_id, route_id="project_management.scheduling", state={"taskId": r.task_id, "projectId": project_id}, values={"milestone": r.task_name, "owner": r.owner_name or "Unassigned", "target": fmt_date(r.target_date), "slip": f"{fmt_int(r.slip_days or 0)} d", "statusLabel": r.status_label})
            for r in rows
        ),
    )


__all__ = ["build_operational_tables", "build_operational_tabs", "build_preview_operational_tables"]
