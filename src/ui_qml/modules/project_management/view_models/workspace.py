from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectManagementWorkspaceViewModel:
    route_id: str
    title: str
    summary: str
    migration_status: str
    legacy_runtime_status: str


__all__ = ["ProjectManagementWorkspaceViewModel"]
