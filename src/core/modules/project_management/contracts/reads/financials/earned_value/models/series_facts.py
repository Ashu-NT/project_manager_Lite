from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.core.modules.project_management.contracts.reads.financials.snapshot.models.snapshot_facts import (
    FinanceSnapshotFacts,
)


@dataclass(frozen=True, slots=True)
class EvmBaselineTaskFact:
    task_id: str
    baseline_start: date | None
    baseline_finish: date | None
    baseline_duration_days: int
    baseline_planned_cost: Decimal


@dataclass(frozen=True, slots=True)
class EvmSeriesFacts:
    finance: FinanceSnapshotFacts
    baseline_id: str | None
    baseline_tasks: tuple[EvmBaselineTaskFact, ...]
