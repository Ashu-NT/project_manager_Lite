from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.core.modules.project_management.domain.financials.forecast import (
    ForecastLine,
    ForecastSourceDecision,
    ProjectForecast,
)


@dataclass(frozen=True, slots=True)
class ForecastGenerationResult:
    forecast: ProjectForecast
    lines: tuple[ForecastLine, ...]
    decisions: tuple[ForecastSourceDecision, ...]
    planned_total: Decimal
    posted_actual_offset: Decimal
    open_commitment_total: Decimal
    remaining_plan_total: Decimal
    manual_etc_total: Decimal
    risk_contingency_total: Decimal
    etc_total: Decimal
