"""Project, baseline, period, and view option builders."""

from __future__ import annotations

from src.core.modules.project_management.application.dashboard import PORTFOLIO_SCOPE_ID
from src.core.modules.project_management.api.desktop.dashboard.models.snapshot import (
    ProjectDashboardSelectorOptionDescriptor,
)


def build_project_options(project_service=None) -> tuple[ProjectDashboardSelectorOptionDescriptor, ...]:
    options = [ProjectDashboardSelectorOptionDescriptor(value=PORTFOLIO_SCOPE_ID, label="Portfolio Overview")]
    if project_service is None:
        return tuple(options)
    try:
        projects = project_service.list_projects()
    except Exception:
        return tuple(options)
    options.extend(
        ProjectDashboardSelectorOptionDescriptor(value=p.id, label=p.name) for p in projects
    )
    return tuple(options)


def resolve_project_id(
    project_id: str | None,
    project_options: tuple[ProjectDashboardSelectorOptionDescriptor, ...],
) -> str:
    normalized = (project_id or "").strip()
    option_values = {o.value for o in project_options}
    if normalized and normalized in option_values:
        return normalized
    for o in project_options:
        if o.value != PORTFOLIO_SCOPE_ID:
            return o.value
    return PORTFOLIO_SCOPE_ID


def build_baseline_options(
    selected_project_id: str,
    baseline_service=None,
) -> tuple[ProjectDashboardSelectorOptionDescriptor, ...]:
    _latest = ProjectDashboardSelectorOptionDescriptor(value="", label="Latest baseline")
    if selected_project_id == PORTFOLIO_SCOPE_ID:
        return (ProjectDashboardSelectorOptionDescriptor(value="", label="Portfolio view"),)
    if baseline_service is None:
        return (_latest,)
    try:
        baselines = baseline_service.list_baselines(selected_project_id)
    except Exception:
        return (_latest,)
    return (
        _latest,
        *(
            ProjectDashboardSelectorOptionDescriptor(
                value=b.id,
                label=f"{b.name} ({b.created_at.strftime('%Y-%m-%d %H:%M')})",
            )
            for b in baselines
        ),
    )


def resolve_baseline_id(
    baseline_id: str | None,
    baseline_options: tuple[ProjectDashboardSelectorOptionDescriptor, ...],
) -> str:
    normalized = (baseline_id or "").strip()
    return normalized if normalized in {o.value for o in baseline_options} else ""


def build_period_options() -> tuple[ProjectDashboardSelectorOptionDescriptor, ...]:
    return (
        ProjectDashboardSelectorOptionDescriptor("all", "All Horizon"),
        ProjectDashboardSelectorOptionDescriptor("30d", "30 Days"),
        ProjectDashboardSelectorOptionDescriptor("60d", "60 Days"),
        ProjectDashboardSelectorOptionDescriptor("90d", "90 Days"),
        ProjectDashboardSelectorOptionDescriptor("180d", "180 Days"),
    )


def resolve_period_key(
    period_key: str | None,
    period_options: tuple[ProjectDashboardSelectorOptionDescriptor, ...],
) -> str:
    normalized = (period_key or "").strip().lower()
    return normalized if normalized in {o.value for o in period_options} else "90d"


def build_view_options() -> tuple[ProjectDashboardSelectorOptionDescriptor, ...]:
    return (
        ProjectDashboardSelectorOptionDescriptor("executive", "Executive View"),
        ProjectDashboardSelectorOptionDescriptor("pmo", "PMO View"),
        ProjectDashboardSelectorOptionDescriptor("project_manager", "Project Manager View"),
        ProjectDashboardSelectorOptionDescriptor("resource_manager", "Resource Manager View"),
        ProjectDashboardSelectorOptionDescriptor("financial", "Financial View"),
    )


def resolve_view_key(
    view_key: str | None,
    view_options: tuple[ProjectDashboardSelectorOptionDescriptor, ...],
) -> str:
    normalized = (view_key or "").strip().lower()
    return normalized if normalized in {o.value for o in view_options} else "executive"


def project_label_for_id(
    project_id: str,
    project_options: tuple[ProjectDashboardSelectorOptionDescriptor, ...],
) -> str:
    for o in project_options:
        if o.value == project_id:
            return o.label
    return "Dashboard"


def baseline_label_for_id(
    baseline_id: str,
    baseline_options: tuple[ProjectDashboardSelectorOptionDescriptor, ...],
) -> str:
    for o in baseline_options:
        if o.value == baseline_id:
            return o.label
    return baseline_options[0].label if baseline_options else "Latest baseline"


__all__ = [
    "baseline_label_for_id",
    "build_baseline_options",
    "build_period_options",
    "build_project_options",
    "build_view_options",
    "project_label_for_id",
    "resolve_baseline_id",
    "resolve_period_key",
    "resolve_project_id",
    "resolve_view_key",
]
