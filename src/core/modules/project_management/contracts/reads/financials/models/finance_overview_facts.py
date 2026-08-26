from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class FinanceOverviewFacts:
    tenant_id: str
    organization_id: str
    project_id: str
    as_of: date
    currency_code: str
    approved_budget: Decimal
    approved_budget_id: str | None
    approved_budget_revision: int | None
    approved_budget_at: datetime | None
    posted_actual: Decimal
    open_commitment: Decimal
    forecast_etc: Decimal | None
    approved_forecast_id: str | None
    approved_forecast_revision: int | None
    approved_forecast_as_of: date | None

    @property
    def estimate_at_completion(self) -> Decimal | None:
        if self.forecast_etc is None:
            return None
        return self.posted_actual + self.forecast_etc

    @property
    def variance_at_completion(self) -> Decimal | None:
        eac = self.estimate_at_completion
        return None if eac is None else self.approved_budget - eac

    @property
    def available_after_commitment(self) -> Decimal:
        return self.approved_budget - self.posted_actual - self.open_commitment


__all__ = ["FinanceOverviewFacts"]
