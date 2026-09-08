from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.core.modules.project_management.domain.enums import ProjectStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectCreated:
    tenant_id: str | None
    organization_id: str
    project_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectProfileUpdated:
    tenant_id: str | None
    organization_id: str
    project_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectStatusChanged:
    tenant_id: str | None
    organization_id: str
    project_id: str
    status: ProjectStatus
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRemoved:
    tenant_id: str | None
    organization_id: str
    project_id: str
    occurred_at: datetime


__all__ = [
    "ProjectCreated",
    "ProjectProfileUpdated",
    "ProjectStatusChanged",
    "ProjectRemoved",
]
