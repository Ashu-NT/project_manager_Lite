from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MaintenancePreventiveMetricViewModel:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class MaintenancePreventiveOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[MaintenancePreventiveMetricViewModel, ...] = field(
        default_factory=tuple
    )


@dataclass(frozen=True)
class MaintenancePreventiveWorkspaceViewModel:
    overview: MaintenancePreventiveOverviewViewModel
    queue_state: dict[str, object] = field(default_factory=dict)
    plan_library_state: dict[str, object] = field(default_factory=dict)
    template_library_state: dict[str, object] = field(default_factory=dict)
    plan_form_options: dict[str, object] = field(default_factory=dict)
    plan_task_form_options: dict[str, object] = field(default_factory=dict)
    template_form_options: dict[str, object] = field(default_factory=dict)
    step_form_options: dict[str, object] = field(default_factory=dict)
    empty_state: str = ""


__all__ = [
    "MaintenancePreventiveMetricViewModel",
    "MaintenancePreventiveOverviewViewModel",
    "MaintenancePreventiveWorkspaceViewModel",
]
