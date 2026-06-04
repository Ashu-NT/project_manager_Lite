from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProjectDashboardSectionItemDescriptor:
    id: str
    title: str
    status_label: str = ""
    subtitle: str = ""
    supporting_text: str = ""
    meta_text: str = ""
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProjectDashboardSectionDescriptor:
    title: str
    subtitle: str = ""
    empty_state: str = ""
    items: tuple[ProjectDashboardSectionItemDescriptor, ...] = field(default_factory=tuple)


__all__ = ["ProjectDashboardSectionDescriptor", "ProjectDashboardSectionItemDescriptor"]
