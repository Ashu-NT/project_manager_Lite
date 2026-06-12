from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from src.core.modules.project_management.domain.identifiers import generate_id


class BaselineStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


@dataclass
class ProjectBaseline:
    id: str
    project_id: str
    name: str
    created_at: date
    status: BaselineStatus = BaselineStatus.DRAFT
    version: int = 1
    submitted_by: str | None = None
    submitted_at: date | None = None
    approved_by: str | None = None
    approved_at: date | None = None
    notes: str = ""

    @staticmethod
    def create(project_id: str, name: str) -> "ProjectBaseline":
        return ProjectBaseline(
            id=generate_id(),
            project_id=project_id,
            name=name.strip() or "Baseline",
            created_at=date.today(),
            status=BaselineStatus.DRAFT,
            version=1,
        )

    def submit(self, submitted_by: str, notes: str = "") -> None:
        if self.status != BaselineStatus.DRAFT:
            raise ValueError(f"Cannot submit baseline in status '{self.status.value}'.")
        self.status = BaselineStatus.SUBMITTED
        self.submitted_by = submitted_by
        self.submitted_at = date.today()
        if notes:
            self.notes = notes

    def approve(self, approved_by: str, notes: str = "") -> None:
        if self.status != BaselineStatus.SUBMITTED:
            raise ValueError(f"Cannot approve baseline in status '{self.status.value}'.")
        self.status = BaselineStatus.APPROVED
        self.approved_by = approved_by
        self.approved_at = date.today()
        if notes:
            self.notes = notes

    def reject(self, notes: str = "") -> None:
        if self.status != BaselineStatus.SUBMITTED:
            raise ValueError(f"Cannot reject baseline in status '{self.status.value}'.")
        self.status = BaselineStatus.REJECTED
        if notes:
            self.notes = notes

    def supersede(self) -> None:
        if self.status != BaselineStatus.APPROVED:
            raise ValueError(f"Cannot supersede baseline in status '{self.status.value}'.")
        self.status = BaselineStatus.SUPERSEDED


@dataclass
class BaselineTask:
    id: str
    baseline_id: str
    task_id: str
    task_name: str | None
    baseline_start: date | None
    baseline_finish: date | None
    baseline_duration_days: int
    baseline_planned_cost: float = 0.0

    @staticmethod
    def create(
        baseline_id: str,
        task_id: str,
        task_name: str | None,
        baseline_start: date | None,
        baseline_finish: date | None,
        baseline_duration_days: int,
        baseline_planned_cost: float,
    ) -> "BaselineTask":
        return BaselineTask(
            id=generate_id(),
            baseline_id=baseline_id,
            task_id=task_id,
            task_name=(task_name.strip() if task_name else None),
            baseline_start=baseline_start,
            baseline_finish=baseline_finish,
            baseline_duration_days=max(0, baseline_duration_days),
            baseline_planned_cost=max(0.0, baseline_planned_cost),
        )


@dataclass
class BaselineVarianceRecord:
    """
    Per-task variance snapshot created when a new baseline is approved.

    Compares each task's dates and cost in the new baseline against the
    superseded approved baseline, providing a permanent audit trail of
    how the plan has shifted over time.
    """
    id: str
    project_id: str
    new_baseline_id: str
    superseded_baseline_id: str
    task_id: str
    task_name: str | None
    start_variance_days: int    # (new_start - old_start).days; positive = later
    finish_variance_days: int   # (new_finish - old_finish).days
    cost_variance: float        # new_planned_cost - old_planned_cost
    created_at: date

    @staticmethod
    def create(
        project_id: str,
        new_baseline_id: str,
        superseded_baseline_id: str,
        task_id: str,
        task_name: str | None,
        start_variance_days: int,
        finish_variance_days: int,
        cost_variance: float,
    ) -> "BaselineVarianceRecord":
        return BaselineVarianceRecord(
            id=generate_id(),
            project_id=project_id,
            new_baseline_id=new_baseline_id,
            superseded_baseline_id=superseded_baseline_id,
            task_id=task_id,
            task_name=task_name,
            start_variance_days=start_variance_days,
            finish_variance_days=finish_variance_days,
            cost_variance=cost_variance,
            created_at=date.today(),
        )


__all__ = [
    "BaselineStatus",
    "BaselineVarianceRecord",
    "BaselineTask",
    "ProjectBaseline",
]
