from __future__ import annotations

from dataclasses import dataclass, field

from src.core.modules.project_management.api.desktop.financials.models.baseline_variance import BaselineVarianceRecordDto


@dataclass(frozen=True)
class FinancialForecastVersionDto:
    id: str
    name: str
    status: str
    status_label: str
    revision: int
    row_version: int
    currency_code: str
    as_of_label: str
    generation_mode_label: str
    approved_at_label: str
    notes: str


@dataclass(frozen=True)
class FinancialForecastLineDto:
    id: str
    description: str
    amount_label: str
    source_kind_label: str
    source_type_label: str
    cost_code_id: str
    task_id: str
    source_reference_label: str
    source_snapshot_label: str
    period_label: str


@dataclass(frozen=True)
class FinancialChangeDto:
    id: str
    title: str
    status: str
    status_label: str
    revision: int
    effective_date_label: str
    reason: str
    description: str
    base_budget_label: str
    base_forecast_label: str
    applied_budget_id: str
    applied_forecast_id: str
    applied_schedule_count: int
    applied_at_label: str


@dataclass(frozen=True)
class FinancialChangeImpactDto:
    id: str
    impact_type_label: str
    description: str
    amount_label: str
    cost_code_id: str
    task_id: str
    target_label: str
    schedule_label: str
    applied_reference_label: str


@dataclass(frozen=True)
class FinancialBaselineVersionDto:
    id: str
    name: str
    status: str
    status_label: str
    version: int
    created_at_label: str
    approved_at_label: str


@dataclass(frozen=True)
class FinancialBaselineVarianceDto:
    baselines: tuple[FinancialBaselineVersionDto, ...] = field(default_factory=tuple)
    selected_baseline_id: str = ""
    selected_baseline_label: str = ""
    compared_baseline_id: str = ""
    records: tuple[BaselineVarianceRecordDto, ...] = field(default_factory=tuple)


__all__ = [
    "FinancialBaselineVarianceDto",
    "FinancialBaselineVersionDto",
    "FinancialChangeDto",
    "FinancialChangeImpactDto",
    "FinancialForecastLineDto",
    "FinancialForecastVersionDto",
]
