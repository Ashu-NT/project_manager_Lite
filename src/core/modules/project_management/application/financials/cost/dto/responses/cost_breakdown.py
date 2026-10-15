from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class CostSourceRow:
    source_key: str
    source_label: str
    planned: Decimal
    committed: Decimal
    actual: Decimal
    forecast: Decimal


@dataclass
class CostSourceBreakdown:
    project_id: str
    project_currency: str | None
    rows: list[CostSourceRow]
    total_planned: Decimal
    total_committed: Decimal
    total_actual: Decimal
    notes: list[str]


@dataclass
class CostBreakdownRow:
    cost_type: str
    currency: str
    planned: Decimal
    actual: Decimal


__all__ = ['CostSourceRow', 'CostSourceBreakdown', 'CostBreakdownRow']
