from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.ui_qml.platform.view_models.runtime import PlatformMetricViewModel


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
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlatformWorkspaceActionListViewModel:
    title: str
    subtitle: str = ""
    empty_state: str = ""
    items: tuple[PlatformWorkspaceActionItemViewModel, ...] = field(default_factory=tuple)


__all__ = [
    "PlatformWorkspaceActionItemViewModel",
    "PlatformWorkspaceActionListViewModel",
    "PlatformWorkspaceOverviewViewModel",
    "PlatformWorkspaceRowViewModel",
    "PlatformWorkspaceSectionViewModel",
]
