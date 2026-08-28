from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class BaselineVarianceRecordDto:
    task_id: str
    task_name: str
    start_variance_days: int
    finish_variance_days: int
    cost_variance: str
    cost_variance_label: str
    tone: str


@dataclass(frozen=True)
class FinancialBaselineVersionDto:
    id: str
    name: str
    status: str
    status_label: str
    version: int
    created_at_label: str
    approved_at_label: str


__all__ = ["BaselineVarianceRecordDto", "FinancialBaselineVersionDto"]
