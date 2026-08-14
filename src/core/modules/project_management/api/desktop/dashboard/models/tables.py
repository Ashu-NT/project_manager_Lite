from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProjectDashboardOperationalTabDescriptor:
    id: str
    label: str
    count: int = 0
    route_id: str = ""


@dataclass(frozen=True)
class ProjectDashboardTableColumnDescriptor:
    key: str
    label: str
    flex: int = 1
    min_width: int = 120
    sortable: bool = False
    visible: bool = True
    column_type: str = "text"


@dataclass(frozen=True)
class ProjectDashboardTableRowDescriptor:
    id: str
    values: dict[str, Any] = field(default_factory=dict)
    route_id: str = ""
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProjectDashboardOperationalTableDescriptor:
    id: str
    title: str
    subtitle: str = ""
    empty_state: str = ""
    collection_semantics: str = "complete"
    supports_search: bool = True
    supports_pagination: bool = True
    columns: tuple[ProjectDashboardTableColumnDescriptor, ...] = field(default_factory=tuple)
    rows: tuple[ProjectDashboardTableRowDescriptor, ...] = field(default_factory=tuple)
    # Populated only for genuinely SCALABLE tables (server-paginated) --
    # see ProjectManagementDashboardDesktopApi.list_delayed_tasks_page().
    # total_count is the authoritative filtered count, never len(rows).
    page: int = 1
    page_size: int = 25
    total_count: int = 0
    sort_key: str = ""
    sort_direction: str = "asc"
    search_text: str = ""


__all__ = [
    "ProjectDashboardOperationalTabDescriptor",
    "ProjectDashboardTableColumnDescriptor",
    "ProjectDashboardTableRowDescriptor",
    "ProjectDashboardOperationalTableDescriptor",
]
