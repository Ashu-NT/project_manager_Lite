from __future__ import annotations

from dataclasses import dataclass, field

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


__all__ = [
    "PlatformWorkspaceOverviewViewModel",
    "PlatformWorkspaceRowViewModel",
    "PlatformWorkspaceSectionViewModel",
]
