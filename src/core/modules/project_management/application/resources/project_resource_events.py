from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectResourceAssignmentChanged:
    """A `ProjectResource` (project<->resource assignment row) was added, updated, toggled
    active/inactive, or removed -- a real mutation of the `resources` module's own aggregate,
    never a Project-entity field change. Reuses Project's own `PROJECT_DETAIL_SCOPE_CODE`
    ViewInvalidation target (the affected project's resourcing genuinely went stale), rather than
    inventing a parallel Resource-owned ViewInvalidation category for a single narrow fact."""

    tenant_id: str | None
    organization_id: str
    project_id: str
    occurred_at: datetime


__all__ = ["ProjectResourceAssignmentChanged"]
