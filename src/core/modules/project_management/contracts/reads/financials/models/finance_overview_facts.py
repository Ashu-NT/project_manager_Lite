from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from .finance_snapshot_facts import FinanceControlFact


@dataclass(frozen=True, slots=True)
class FinanceOverviewFacts:
    tenant_id: str
    organization_id: str
    project_id: str
    as_of: date
    currency_code: str
    control: FinanceControlFact
    approved_budget_id: str | None
    approved_budget_revision: int | None
    approved_budget_at: datetime | None
    approved_forecast_id: str | None
    approved_forecast_revision: int | None
    approved_forecast_as_of: date | None

    @property
    def approved_budget(self) -> Decimal:
        return self.control.approved_budget

    @property
    def posted_actual(self) -> Decimal:
        return self.control.posted_actual

    @property
    def open_commitment(self) -> Decimal:
        return self.control.open_commitment

    @property
    def forecast_etc(self) -> Decimal | None:
        return self.control.forecast_etc

    @property
    def estimate_at_completion(self) -> Decimal | None:
        return self.control.estimate_at_completion

    @property
    def variance_at_completion(self) -> Decimal | None:
        return self.control.variance_at_completion

    @property
    def available_after_commitment(self) -> Decimal:
        return self.control.committed_available


__all__ = ["FinanceOverviewFacts"]
