from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class CostPhasingQuery:
    date_from: date
    date_to: date
    granularity: str = "month"


@dataclass(frozen=True, slots=True)
class CostPhasingPeriodFact:
    period_key: str
    period_start: date
    period_end: date
    planned_cost: Decimal
    open_commitment: Decimal
    posted_actual: Decimal
    forecast_cost: Decimal
    exposure: Decimal
    currency_code: str


@dataclass(frozen=True, slots=True)
class CostPhasingFacts:
    tenant_id: str
    organization_id: str
    project_id: str
    as_of_date: date
    date_from: date
    date_to: date
    granularity: str
    currency_code: str
    approved_budget_id: str | None
    approved_budget_revision: int | None
    approved_forecast_id: str | None
    approved_forecast_revision: int | None
    approved_forecast_as_of: date | None
    periods: tuple[CostPhasingPeriodFact, ...]


@dataclass(frozen=True, slots=True)
class PerformanceEvmFact:
    project_id: str
    as_of_date: date
    availability: str
    unavailable_reason: str
    baseline_id: str | None
    budget_revision: int | None
    forecast_revision: int | None
    forecast_as_of: date | None
    currency_code: str
    bac: float | None
    pv: float | None
    ev: float | None
    ac: float | None
    cv: float | None
    sv: float | None
    cpi: float | None
    spi: float | None
    etc: float | None
    eac: float | None
    vac: float | None
    tcpi_bac: float | None
    tcpi_eac: float | None
    notes: str
    calculation_precision: str = "binary_float_debt"


@dataclass(frozen=True, slots=True)
class PerformanceVarianceMetricFact:
    metric_code: str
    display_name: str
    value: Decimal | None
    currency_code: str | None
    unit: str
    sign_convention: str
    as_of_date: date
    source_revision: str
    availability: str
    unavailable_reason: str = ""


@dataclass(frozen=True, slots=True)
class PerformanceVarianceFacts:
    project_id: str
    as_of_date: date
    currency_code: str
    budget_revision: int | None
    forecast_revision: int | None
    forecast_as_of: date | None
    selected_baseline_id: str
    selected_baseline_label: str
    compared_baseline_id: str
    baseline_versions: tuple[object, ...]
    baseline_records: tuple[object, ...]
    metrics: tuple[PerformanceVarianceMetricFact, ...]


@dataclass(frozen=True, slots=True)
class PerformanceReportDefinitionFact:
    report_code: str
    display_name: str
    formats: tuple[str, ...]
    authority_label: str
    requires_sensitive_finance: bool = False
    requires_profitability: bool = False


@dataclass(frozen=True, slots=True)
class PerformanceReportsFacts:
    project_id: str
    as_of_date: date
    currency_code: str
    budget_revision: int | None
    forecast_revision: int | None
    forecast_as_of: date | None
    definitions: tuple[PerformanceReportDefinitionFact, ...]


__all__ = [
    "CostPhasingFacts",
    "CostPhasingPeriodFact",
    "CostPhasingQuery",
    "PerformanceEvmFact",
    "PerformanceReportDefinitionFact",
    "PerformanceReportsFacts",
    "PerformanceVarianceFacts",
    "PerformanceVarianceMetricFact",
]
