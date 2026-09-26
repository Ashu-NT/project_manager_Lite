"""Resolves Project Management's Context Navigation Tree: workspace
destinations grouped and ordered, each carrying its registered route id."""

from __future__ import annotations

from src.ui_qml.modules.project_management.navigation import PM_WORKSPACE_KEYS
from src.ui_qml.shell.context_navigation import (
    ContextNavigationGroupViewModel,
    ContextNavigationItemViewModel,
    ContextNavigationViewModel,
)

_ROOT_GROUP = ""
_WORK_GROUP = "work"
_WORKLOAD_GROUP = "workload_management"
_FINANCE_GROUP = "finance"
_GOVERNANCE_GROUP = "governance"

_GROUP_LABELS: dict[str, str] = {
    _ROOT_GROUP: "",
    _WORK_GROUP: "Work",
    _WORKLOAD_GROUP: "Workload Management",
    _FINANCE_GROUP: "Finance",
    _GOVERNANCE_GROUP: "Governance",
}

_GROUP_ORDER: dict[str, int] = {
    _ROOT_GROUP: 0,
    _WORK_GROUP: 10,
    _WORKLOAD_GROUP: 20,
    _FINANCE_GROUP: 30,
    _GOVERNANCE_GROUP: 40,
}

# (workspace_key, label, icon_key, group_id, order)
_DESTINATIONS: tuple[tuple[str, str, str, str, int], ...] = (
    ("dashboard", "Overview", "dashboard", _ROOT_GROUP, 0),
    ("portfolio", "Portfolio", "portfolio", _ROOT_GROUP, 10),
    ("projects", "Projects", "project", _WORK_GROUP, 0),
    ("tasks", "Tasks", "tasks", _WORK_GROUP, 10),
    ("scheduling", "Planning", "calendar", _WORK_GROUP, 20),
    ("timesheets", "Timesheets", "time", _WORK_GROUP, 30),
    ("resources", "Resources", "resources", _WORKLOAD_GROUP, 0),
    ("review_queue", "Review Queue", "approve", _WORKLOAD_GROUP, 10),
    ("financials", "Finance", "financials", _FINANCE_GROUP, 0),
    ("register", "Register", "register", _GOVERNANCE_GROUP, 0),
    ("collaboration", "Collaboration", "collaboration", _GOVERNANCE_GROUP, 10),
)

assert {row[0] for row in _DESTINATIONS} == set(PM_WORKSPACE_KEYS), (
    "PM context navigation destinations have drifted from PM_WORKSPACE_KEYS"
)


def build_pm_context_navigation() -> ContextNavigationViewModel:
    groups: dict[str, list[ContextNavigationItemViewModel]] = {}
    for workspace_key, label, icon_key, group_id, order in _DESTINATIONS:
        groups.setdefault(group_id, []).append(
            ContextNavigationItemViewModel(
                id=workspace_key,
                label=label,
                icon_key=icon_key,
                route_id=f"project_management.{workspace_key}",
                group_id=group_id,
                order=order,
            )
        )

    group_view_models = [
        ContextNavigationGroupViewModel(
            id=group_id,
            label=_GROUP_LABELS.get(group_id, group_id),
            order=_GROUP_ORDER.get(group_id, 999),
            items=tuple(sorted(items, key=lambda item: item.order)),
        )
        for group_id, items in groups.items()
    ]

    return ContextNavigationViewModel(
        workspace_id="project_management",
        title="Project Management",
        groups=tuple(group_view_models),
    )


__all__ = ["build_pm_context_navigation"]
