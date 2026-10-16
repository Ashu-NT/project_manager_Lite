from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from src.core.modules.project_management.contracts.reads.financials.performance.models.performance_facts import (
    PerformanceReportDefinitionFact,
)


@dataclass(frozen=True, slots=True)
class FinancialReportsDto:
    project_id: str = ""
    as_of_date: date | None = None
    currency_code: str = ""
    budget_revision: int | None = None
    forecast_revision: int | None = None
    forecast_as_of: date | None = None
    definitions: tuple[PerformanceReportDefinitionFact, ...] = field(default_factory=tuple)
