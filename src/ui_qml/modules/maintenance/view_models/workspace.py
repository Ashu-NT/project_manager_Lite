from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaintenanceWorkspaceViewModel:
    route_id: str
    title: str
    summary: str
    migration_status: str
    legacy_runtime_status: str


__all__ = ["MaintenanceWorkspaceViewModel"]
