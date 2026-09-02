from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FinancialManualEtcCommand:
    cost_code_id: str
    amount: str
    description: str
    task_id: str | None = None
    period_start: str = ""
    period_end: str = ""


@dataclass(frozen=True, slots=True)
class FinancialRiskContingencyCommand:
    risk_id: str
    cost_code_id: str
    amount: str
    description: str = ""
    task_id: str | None = None
    period_start: str = ""
    period_end: str = ""


@dataclass(frozen=True, slots=True)
class FinancialGenerateForecastCommand:
    project_id: str
    name: str
    as_of_date: str
    notes: str = ""
    manual_estimates: tuple[FinancialManualEtcCommand, ...] = ()
    risk_contingencies: tuple[FinancialRiskContingencyCommand, ...] = ()


@dataclass(frozen=True, slots=True)
class FinancialVersionedForecastCommand:
    forecast_id: str
    expected_version: int
    notes: str = ""


__all__ = [
    "FinancialGenerateForecastCommand",
    "FinancialManualEtcCommand",
    "FinancialRiskContingencyCommand",
    "FinancialVersionedForecastCommand",
]
