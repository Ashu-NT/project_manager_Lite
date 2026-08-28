from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .baseline_variance import BaselineVarianceRecordDto
from .baseline_variance import FinancialBaselineVersionDto
from .snapshots import FinancialPeriodRowDto


@dataclass(frozen=True, slots=True)
class FinancialPerformanceMetricDto:
    code: str
    label: str
    value: str | None
    value_label: str
    supporting_text: str
    availability: str = "available"
    tone: str = "default"


@dataclass(frozen=True, slots=True)
class FinancialEvmDto:
    project_id: str = ""
    as_of_date: date | None = None
    availability: str = "no_data"
    unavailable_reason: str = ""
    baseline_id: str = ""
    budget_revision: int | None = None
    forecast_revision: int | None = None
    forecast_as_of: date | None = None
    currency_code: str = ""
    calculation_precision: str = "binary_float_r6e_debt"
    metrics: tuple[FinancialPerformanceMetricDto, ...] = field(default_factory=tuple)
    notes: str = ""


@dataclass(frozen=True, slots=True)
class FinancialVarianceWorkspaceDto:
    project_id: str = ""
    as_of_date: date | None = None
    currency_code: str = ""
    budget_revision: int | None = None
    forecast_revision: int | None = None
    forecast_as_of: date | None = None
    selected_baseline_id: str = ""
    selected_baseline_label: str = ""
    compared_baseline_id: str = ""
    baselines: tuple[FinancialBaselineVersionDto, ...] = field(default_factory=tuple)
    records: tuple[BaselineVarianceRecordDto, ...] = field(default_factory=tuple)
    metrics: tuple[FinancialPerformanceMetricDto, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class FinancialCostPhasingDto:
    project_id: str = ""
    as_of_date: date | None = None
    date_from: date | None = None
    date_to: date | None = None
    granularity: str = "month"
    currency_code: str = ""
    approved_budget_id: str = ""
    approved_budget_revision: int | None = None
    approved_forecast_id: str = ""
    approved_forecast_revision: int | None = None
    approved_forecast_as_of: date | None = None
    periods: tuple[FinancialPeriodRowDto, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class FinancialReportDefinitionDto:
    report_code: str
    display_name: str
    formats: tuple[str, ...]
    authority_label: str
    requires_sensitive_finance: bool = False
    requires_profitability: bool = False


@dataclass(frozen=True, slots=True)
class FinancialReportsDto:
    project_id: str = ""
    as_of_date: date | None = None
    currency_code: str = ""
    budget_revision: int | None = None
    forecast_revision: int | None = None
    forecast_as_of: date | None = None
    definitions: tuple[FinancialReportDefinitionDto, ...] = field(default_factory=tuple)


__all__ = [
    "FinancialCostPhasingDto",
    "FinancialEvmDto",
    "FinancialPerformanceMetricDto",
    "FinancialReportDefinitionDto",
    "FinancialReportsDto",
    "FinancialVarianceWorkspaceDto",
]
