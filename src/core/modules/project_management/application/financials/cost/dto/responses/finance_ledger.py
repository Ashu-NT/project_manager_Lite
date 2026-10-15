from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class ProjectFinanceLedgerRow:
    project_id: str
    source_key: str
    source_label: str
    cost_type: str
    stage: str
    amount: Decimal
    currency: str | None
    occurred_on: date | None
    reference_type: str
    reference_id: str
    reference_label: str
    task_id: str | None
    task_name: str | None
    resource_id: str | None
    resource_name: str | None
    cost_code_id: str | None
    source_type: str | None
    financial_period_id: str | None
    period_start: date | None
    period_end: date | None
    included_in_policy: bool


__all__ = ['ProjectFinanceLedgerRow']
