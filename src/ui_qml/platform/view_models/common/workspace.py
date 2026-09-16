from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PlatformMetricViewModel:
    label: str
    value: str
    supporting_text: str

@dataclass(frozen=True)
class PlatformWorkspaceRowViewModel:
    label: str
    value: str
    supporting_text: str

@dataclass(frozen=True)
class PlatformWorkspaceSectionViewModel:
    title: str
    rows: tuple[PlatformWorkspaceRowViewModel, ...] = field(default_factory=tuple)
    empty_state: str = ""

@dataclass(frozen=True)
class PlatformWorkspaceOverviewViewModel:
    title: str
    subtitle: str
    status_label: str
    metrics: tuple[PlatformMetricViewModel, ...] = field(default_factory=tuple)
    sections: tuple[PlatformWorkspaceSectionViewModel, ...] = field(default_factory=tuple)
    breakdown_cards: tuple[dict, ...] = field(default_factory=tuple)
    recent_activity: tuple[dict, ...] = field(default_factory=tuple)
    # Pre-composed {"title", "subtitle", "emptyState", "items"} dict -- items
    # are already-serialized canonical ActivityFeed shapes, not a
    # PlatformWorkspaceActionListViewModel (that shape backs the full
    # Approval Queue table separately; this is a compact preview).
    approval_actions: dict[str, object] | None = None

@dataclass(frozen=True)
class PlatformWorkspaceActionItemViewModel:
    id: str
    title: str
    status_label: str = ""
    subtitle: str = ""
    supporting_text: str = ""
    meta_text: str = ""
    can_primary_action: bool = False
    can_secondary_action: bool = False
    can_tertiary_action: bool = False
    state: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class PlatformWorkspaceActionListViewModel:
    title: str
    subtitle: str = ""
    empty_state: str = ""
    items: tuple[PlatformWorkspaceActionItemViewModel, ...] = field(default_factory=tuple)
    # Optional server-side pagination metadata. `paginated` is False (and the
    # rest at their defaults) for every existing non-paginated list -- fully
    # backward compatible. `no_results_state` is shown instead of
    # `empty_state` when the dataset itself is non-empty but the current
    # search/filter matched nothing (total > 0, filtered_total == 0).
    paginated: bool = False
    no_results_state: str = ""
    page: int = 1
    page_size: int = 0
    total_count: int = 0
    filtered_total: int = 0

__all__ = [
    "PlatformMetricViewModel",
    "PlatformWorkspaceActionItemViewModel",
    "PlatformWorkspaceActionListViewModel",
    "PlatformWorkspaceOverviewViewModel",
    "PlatformWorkspaceRowViewModel",
    "PlatformWorkspaceSectionViewModel",
]
