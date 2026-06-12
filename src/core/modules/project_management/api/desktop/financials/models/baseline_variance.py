from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class BaselineVarianceRecordDto:
    task_id: str
    task_name: str
    start_variance_days: int
    finish_variance_days: int
    cost_variance: float
    cost_variance_label: str
    tone: str


__all__ = ["BaselineVarianceRecordDto"]
