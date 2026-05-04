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
class CollaborationWorkspaceViewModel:
    overview: CollaborationOverviewViewModel
    notifications: CollaborationCollectionViewModel
    inbox: CollaborationCollectionViewModel
    recent_activity: CollaborationCollectionViewModel
    active_presence: CollaborationCollectionViewModel
    empty_state: str = ""


__all__ = [
    "CollaborationCollectionViewModel",
    "CollaborationMetricViewModel",
    "CollaborationOverviewViewModel",
    "CollaborationRecordViewModel",
    "CollaborationWorkspaceViewModel",
]
