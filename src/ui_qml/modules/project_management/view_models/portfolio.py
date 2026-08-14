from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class PortfolioMetricViewModel:
    label: str
    value: str
    supporting_text: str

@dataclass(frozen=True)
class PortfolioOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[PortfolioMetricViewModel, ...]

@dataclass(frozen=True)
class PortfolioSelectorOptionViewModel:
    value: str
    label: str

@dataclass(frozen=True)
class PortfolioRecordViewModel:
    id: str
    title: str
    status_label: str
    subtitle: str
    supporting_text: str
    meta_text: str
    can_primary_action: bool = True
    can_secondary_action: bool = True
    can_tertiary_action: bool = False
    state: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class PortfolioCollectionViewModel:
    title: str
    subtitle: str
    empty_state: str
    items: tuple[PortfolioRecordViewModel, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class PortfolioPagedCollectionViewModel(PortfolioCollectionViewModel):
    """A PortfolioCollectionViewModel whose items are one authoritative
    server-paginated page (R3.3). total is the complete filtered count, not
    len(items) -- never derive a KPI from len(items) on one of these."""

    total: int = 0
    page: int = 1
    page_size: int = 25
    sort_key: str = ""
    sort_direction: str = "asc"
    search_text: str = ""

@dataclass(frozen=True)
class PortfolioSummaryFieldViewModel:
    label: str
    value: str
    supporting_text: str = ""

@dataclass(frozen=True)
class PortfolioSummaryViewModel:
    title: str = ""
    subtitle: str = ""
    empty_state: str = ""
    fields: tuple[PortfolioSummaryFieldViewModel, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class PortfolioWorkspaceViewModel:
    overview: PortfolioOverviewViewModel
    intake_status_options: tuple[PortfolioSelectorOptionViewModel, ...] = field(default_factory=tuple)
    template_options: tuple[PortfolioSelectorOptionViewModel, ...] = field(default_factory=tuple)
    project_options: tuple[PortfolioSelectorOptionViewModel, ...] = field(default_factory=tuple)
    scenario_options: tuple[PortfolioSelectorOptionViewModel, ...] = field(default_factory=tuple)
    dependency_type_options: tuple[PortfolioSelectorOptionViewModel, ...] = field(default_factory=tuple)
    selected_intake_status_filter: str = "all"
    selected_scenario_id: str = ""
    selected_base_scenario_id: str = ""
    selected_compare_scenario_id: str = ""
    intake_items: PortfolioPagedCollectionViewModel = field(default_factory=lambda: PortfolioPagedCollectionViewModel("", "", ""))
    templates: PortfolioCollectionViewModel = field(default_factory=lambda: PortfolioCollectionViewModel("", "", ""))
    scenarios: PortfolioCollectionViewModel = field(default_factory=lambda: PortfolioCollectionViewModel("", "", ""))
    evaluation: PortfolioSummaryViewModel = field(default_factory=PortfolioSummaryViewModel)
    comparison: PortfolioSummaryViewModel = field(default_factory=PortfolioSummaryViewModel)
    heatmap: PortfolioPagedCollectionViewModel = field(default_factory=lambda: PortfolioPagedCollectionViewModel("", "", ""))
    dependencies: PortfolioPagedCollectionViewModel = field(default_factory=lambda: PortfolioPagedCollectionViewModel("", "", ""))
    recent_actions: PortfolioCollectionViewModel = field(default_factory=lambda: PortfolioCollectionViewModel("", "", ""))
    capacity_pool: PortfolioCollectionViewModel = field(default_factory=lambda: PortfolioCollectionViewModel("", "", ""))
    top_at_risk_projects: PortfolioCollectionViewModel = field(default_factory=lambda: PortfolioCollectionViewModel("", "", ""))
    hot_project_count: int = 0
    dependency_count: int = 0
    active_tab: str = "executive"
    active_template_summary: str = ""
    empty_state: str = ""

__all__ = [
    "PortfolioCollectionViewModel",
    "PortfolioMetricViewModel",
    "PortfolioOverviewViewModel",
    "PortfolioPagedCollectionViewModel",
    "PortfolioRecordViewModel",
    "PortfolioSelectorOptionViewModel",
    "PortfolioSummaryFieldViewModel",
    "PortfolioSummaryViewModel",
    "PortfolioWorkspaceViewModel",
]
