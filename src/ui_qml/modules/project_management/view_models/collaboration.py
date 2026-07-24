from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class CollaborationMetricViewModel:
    label: str
    value: str
    supporting_text: str

@dataclass(frozen=True)
class CollaborationOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[CollaborationMetricViewModel, ...]

@dataclass(frozen=True)
class CollaborationRecordViewModel:
    id: str
    title: str
    status_label: str
    subtitle: str
    supporting_text: str
    meta_text: str
    can_primary_action: bool = False
    can_secondary_action: bool = False
    can_tertiary_action: bool = False
    state: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class CollaborationCollectionViewModel:
    title: str
    subtitle: str
    empty_state: str
    items: tuple[CollaborationRecordViewModel, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class CollaborationOptionViewModel:
    value: str
    label: str

@dataclass(frozen=True)
class CollaborationContextViewModel:
    project_options: tuple[CollaborationOptionViewModel, ...] = field(default_factory=tuple)
    team_options: tuple[CollaborationOptionViewModel, ...] = field(default_factory=tuple)
    period_options: tuple[CollaborationOptionViewModel, ...] = field(default_factory=tuple)
    unread_options: tuple[CollaborationOptionViewModel, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class CollaborationPanelTabViewModel:
    id: str
    label: str
    count: int = 0

@dataclass(frozen=True)
class CollaborationDetailFieldViewModel:
    label: str
    value: str

@dataclass(frozen=True)
class CollaborationDetailViewModel:
    id: str
    title: str
    status_label: str
    subtitle: str
    description: str
    state: dict[str, Any] = field(default_factory=dict)
    fields: tuple[CollaborationDetailFieldViewModel, ...] = field(default_factory=tuple)
    activity: CollaborationCollectionViewModel = field(
        default_factory=lambda: CollaborationCollectionViewModel("", "", "", ())
    )
    related_items: CollaborationCollectionViewModel = field(
        default_factory=lambda: CollaborationCollectionViewModel("", "", "", ())
    )
    audit: CollaborationCollectionViewModel = field(
        default_factory=lambda: CollaborationCollectionViewModel("", "", "", ())
    )

@dataclass(frozen=True)
class CollaborationWorkspaceViewModel:
    overview: CollaborationOverviewViewModel
    notifications: CollaborationCollectionViewModel
    inbox: CollaborationCollectionViewModel
    recent_activity: CollaborationCollectionViewModel
    active_presence: CollaborationCollectionViewModel
    context: CollaborationContextViewModel = field(default_factory=CollaborationContextViewModel)
    panel_tabs: tuple[CollaborationPanelTabViewModel, ...] = field(default_factory=tuple)
    mentions: CollaborationCollectionViewModel = field(
        default_factory=lambda: CollaborationCollectionViewModel("", "", "", ())
    )
    approvals: CollaborationCollectionViewModel = field(
        default_factory=lambda: CollaborationCollectionViewModel("", "", "", ())
    )
    activity_feed: CollaborationCollectionViewModel = field(
        default_factory=lambda: CollaborationCollectionViewModel("", "", "", ())
    )
    team_updates: CollaborationCollectionViewModel = field(
        default_factory=lambda: CollaborationCollectionViewModel("", "", "", ())
    )
    empty_state: str = ""

__all__ = [
    "CollaborationCollectionViewModel",
    "CollaborationContextViewModel",
    "CollaborationDetailFieldViewModel",
    "CollaborationDetailViewModel",
    "CollaborationMetricViewModel",
    "CollaborationOptionViewModel",
    "CollaborationOverviewViewModel",
    "CollaborationPanelTabViewModel",
    "CollaborationRecordViewModel",
    "CollaborationWorkspaceViewModel",
]
