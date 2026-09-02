from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class PlannedCostSnapshotCalculated:

    tenant_id: str
    organization_id: str
    project_id: str
    planned_cost_version_id: str
    occurred_at: datetime


__all__ = ["PlannedCostSnapshotCalculated"]
