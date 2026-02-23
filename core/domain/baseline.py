from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from core.domain.identifiers import generate_id


@dataclass
class ProjectBaseline:
    id: str
    project_id: str
    name: str
    created_at: date

    @staticmethod
    def create(project_id: str, name: str) -> "ProjectBaseline":
        return ProjectBaseline(
            id=generate_id(),
            project_id=project_id,
            name=name.strip() or "Baseline",
            created_at=date.today(),
        )


@dataclass
class BaselineTask:
    id: str
    baseline_id: str
    task_id: str
    baseline_start: Optional[date]
    baseline_finish: Optional[date]
    baseline_duration_days: int
    baseline_planned_cost: float = 0.0

    @staticmethod
    def create(
        baseline_id: str,
        task_id: str,
        baseline_start: Optional[date],
        baseline_finish: Optional[date],
        baseline_duration_days: int,
        baseline_planned_cost: float,
    ) -> "BaselineTask":
        return BaselineTask(
            id=generate_id(),
            baseline_id=baseline_id,
            task_id=task_id,
            baseline_start=baseline_start,
            baseline_finish=baseline_finish,
            baseline_duration_days=max(0, baseline_duration_days),
            baseline_planned_cost=max(0.0, baseline_planned_cost),
        )


__all__ = ["ProjectBaseline", "BaselineTask"]
