from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class InventoryDashboardMetricViewModel:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class InventoryDashboardOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[InventoryDashboardMetricViewModel, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class InventoryDashboardRowViewModel:
    id: str
    title: str
    subtitle: str = ""
    status_label: str = ""
    supporting_text: str = ""
    meta_text: str = ""
    tone: str = "default"


@dataclass(frozen=True)
class InventoryDashboardSectionViewModel:
    title: str
    subtitle: str = ""
    empty_state: str = ""
    rows: tuple[InventoryDashboardRowViewModel, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class InventoryDashboardWorkspaceViewModel:
    overview: InventoryDashboardOverviewViewModel
    context_label: str = ""
    sections: tuple[InventoryDashboardSectionViewModel, ...] = field(default_factory=tuple)
    empty_state: str = ""


__all__ = [
    "InventoryDashboardMetricViewModel",
    "InventoryDashboardOverviewViewModel",
    "InventoryDashboardRowViewModel",
    "InventoryDashboardSectionViewModel",
    "InventoryDashboardWorkspaceViewModel",
]
