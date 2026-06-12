from __future__ import annotations
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ProjectRequisitionDesktopDto:
    id: str
    requisition_number: str
    status: str
    status_label: str
    purpose: str
    needed_by_date: date | None
    priority: str
    notes: str


@dataclass(frozen=True)
class ProjectProcurementCommitmentSummary:
    project_id: str
    total_requisitions: int
    open_count: int
    approved_count: int
    closed_count: int
    cancelled_count: int


__all__ = ["ProjectProcurementCommitmentSummary", "ProjectRequisitionDesktopDto"]
