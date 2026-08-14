from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class FinancialsMetricViewModel:
    label: str
    value: str
    supporting_text: str

@dataclass(frozen=True)
class FinancialsOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[FinancialsMetricViewModel, ...]

@dataclass(frozen=True)
class FinancialsSelectorOptionViewModel:
    value: str
    label: str


@dataclass(frozen=True)
class FinancialsManualActualOptionsViewModel:
    currency_code: str = ""
    cost_codes: tuple[FinancialsSelectorOptionViewModel, ...] = field(default_factory=tuple)
    entry_kinds: tuple[FinancialsSelectorOptionViewModel, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class FinancialsRecordViewModel:
    id: str
    title: str
    status_label: str
    subtitle: str
    supporting_text: str
    meta_text: str
    can_primary_action: bool = True
    can_secondary_action: bool = True
    can_tertiary_action: bool = False
    state: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class FinancialsDetailFieldViewModel:
    label: str
    value: str
    supporting_text: str = ""

@dataclass(frozen=True)
class FinancialsDetailViewModel:
    id: str = ""
    title: str = ""
    status_label: str = ""
    subtitle: str = ""
    description: str = ""
    empty_state: str = ""
    fields: tuple[FinancialsDetailFieldViewModel, ...] = field(default_factory=tuple)
    state: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class FinancialsCollectionViewModel:
    title: str
    subtitle: str
    empty_state: str = ""
    items: tuple[FinancialsRecordViewModel, ...] = field(default_factory=tuple)
    page: int = 1
    page_size: int = 50
    total: int = 0

@dataclass(frozen=True)
class FinancialsForecastMetricViewModel:
    label: str
    value: str
    color_hint: str = ""  # "success", "warning", "danger", or ""

@dataclass(frozen=True)
class FinancialsForecastViewModel:
    basis_label: str = ""
    budget_label: str = ""
    actual_label: str = ""
    etc_label: str = ""
    eac_label: str = ""
    vac_label: str = ""
    is_over_budget: bool = False
    has_approved_forecast: bool = False
    forecast_revision: int | None = None
    forecast_as_of_label: str = ""
    alert_message: str = ""
    metrics: tuple[FinancialsForecastMetricViewModel, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class FinancialsCommitmentSummaryViewModel:
    approved_budget_label: str = ""
    posted_actual_label: str = ""
    open_commitment_label: str = ""
    available_after_commitment_label: str = ""
    commitment_rate_pct: float = 0.0

@dataclass(frozen=True)
class BaselineVarianceRowViewModel:
    task_id: str
    task_name: str
    start_variance_days: int
    finish_variance_days: int
    cost_variance: str
    cost_variance_label: str
    tone: str = "default"

@dataclass(frozen=True)
class FinancialsWorkspaceViewModel:
    overview: FinancialsOverviewViewModel
    project_options: tuple[FinancialsSelectorOptionViewModel, ...] = field(default_factory=tuple)
    task_options: tuple[FinancialsSelectorOptionViewModel, ...] = field(default_factory=tuple)
    manual_actual_options: FinancialsManualActualOptionsViewModel = field(
        default_factory=FinancialsManualActualOptionsViewModel
    )
    selected_project_id: str = ""
    cashflow: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    ledger: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    actual_sort_key: str = "metaText"
    actual_sort_direction: str = "desc"
    source_analytics: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    cost_type_analytics: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    forecast: FinancialsForecastViewModel = field(default_factory=FinancialsForecastViewModel)
    selected_forecast_id: str = ""
    forecast_versions: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    forecast_lines: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    selected_change_id: str = ""
    financial_changes: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    financial_change_impacts: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    commitment_summary: FinancialsCommitmentSummaryViewModel = field(default_factory=FinancialsCommitmentSummaryViewModel)
    commitments: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    commitment_sort_key: str = "metaText"
    commitment_sort_direction: str = "desc"
    baseline_variance: tuple[BaselineVarianceRowViewModel, ...] = field(default_factory=tuple)
    selected_baseline_id: str = ""
    baseline_versions: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    variance_basis: FinancialsDetailViewModel = field(default_factory=FinancialsDetailViewModel)
    report_basis: FinancialsDetailViewModel = field(default_factory=FinancialsDetailViewModel)
    financial_profile: FinancialsDetailViewModel = field(default_factory=FinancialsDetailViewModel)
    budget_versions: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    budget_lines: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    rate_cards: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    rate_lines: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    planned_cost_versions: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    planned_cost_lines: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    billing_profile: FinancialsDetailViewModel = field(default_factory=FinancialsDetailViewModel)
    billing_schedule: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    billing_preparations: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    notes: tuple[str, ...] = field(default_factory=tuple)
    empty_state: str = ""

__all__ = [
    "BaselineVarianceRowViewModel",
    "FinancialsCollectionViewModel",
    "FinancialsCommitmentSummaryViewModel",
    "FinancialsDetailFieldViewModel",
    "FinancialsDetailViewModel",
    "FinancialsForecastMetricViewModel",
    "FinancialsForecastViewModel",
    "FinancialsMetricViewModel",
    "FinancialsManualActualOptionsViewModel",
    "FinancialsOverviewViewModel",
    "FinancialsRecordViewModel",
    "FinancialsSelectorOptionViewModel",
    "FinancialsWorkspaceViewModel",
]
