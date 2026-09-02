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
class FinancialsManualActualDefaultsViewModel:
    currency_code: str = ""
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
    manual_actual_defaults: FinancialsManualActualDefaultsViewModel = field(
        default_factory=FinancialsManualActualDefaultsViewModel
    )
    selected_project_id: str = ""
    cost_phasing: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    cost_phasing_basis: FinancialsDetailViewModel = field(default_factory=FinancialsDetailViewModel)
    evm_basis: FinancialsDetailViewModel = field(default_factory=FinancialsDetailViewModel)
    evm_metrics: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    variance_metrics: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    report_definitions: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    ledger: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    activity: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    actual_sort_key: str = "metaText"
    actual_sort_direction: str = "desc"
    selected_forecast_id: str = ""
    selected_forecast: FinancialsDetailViewModel = field(default_factory=FinancialsDetailViewModel)
    forecast_versions: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    forecast_lines: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    forecast_version_sort_key: str = "revision"
    forecast_version_sort_direction: str = "desc"
    forecast_line_sort_key: str = "title"
    forecast_line_sort_direction: str = "asc"
    forecast_version_search: str = ""
    forecast_version_status: str = ""
    forecast_generation_mode: str = ""
    forecast_line_search: str = ""
    forecast_line_source_type: str = ""
    show_generate_forecast: bool = False
    can_generate_forecast: bool = False
    generate_forecast_disabled_reason: str = ""
    selected_change_id: str = ""
    can_create_change: bool = False
    selected_change: FinancialsDetailViewModel = field(default_factory=FinancialsDetailViewModel)
    financial_changes: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    financial_change_impacts: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    change_sort_key: str = "metaText"
    change_sort_direction: str = "desc"
    impact_sort_key: str = "metaText"
    impact_sort_direction: str = "asc"
    change_search: str = ""
    change_status: str = ""
    change_approval_status: str = ""
    change_applied_state: str = ""
    impact_search: str = ""
    impact_type: str = ""
    impact_applied_state: str = ""
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
    selected_budget_id: str = ""
    show_create_budget_version: bool = False
    can_create_budget_version: bool = False
    create_budget_version_disabled_reason: str = ""
    budget_versions: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    budget_lines: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    budget_version_sort_key: str = "revision"
    budget_version_sort_direction: str = "desc"
    budget_line_sort_key: str = "metaText"
    budget_line_sort_direction: str = "desc"
    rate_cards: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    rate_lines: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    selected_rate_card_id: str = ""
    selected_rate_card: FinancialsDetailViewModel = field(default_factory=FinancialsDetailViewModel)
    rate_card_sort_key: str = "title"
    rate_card_sort_direction: str = "asc"
    rate_line_sort_key: str = "title"
    rate_line_sort_direction: str = "asc"
    rate_card_search: str = ""
    rate_card_scope: str = ""
    rate_card_status: str = ""
    rate_line_search: str = ""
    rate_line_rate_type: str = ""
    rate_line_status: str = ""
    rate_line_effective_status: str = ""
    selected_planned_cost_version_id: str = ""
    planned_cost_versions: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    planned_cost_lines: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    planned_cost_version_sort_key: str = "revision"
    planned_cost_version_sort_direction: str = "desc"
    planned_cost_line_sort_key: str = "title"
    planned_cost_line_sort_direction: str = "asc"
    billing_profile: FinancialsDetailViewModel = field(default_factory=FinancialsDetailViewModel)
    billing_schedule: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    billing_preparations: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    selected_billing_preparation_id: str = ""
    selected_billing_preparation: FinancialsDetailViewModel = field(default_factory=FinancialsDetailViewModel)
    billing_preparation_lines: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    billing_schedule_sort_key: str = "supportingText"
    billing_schedule_sort_direction: str = "asc"
    billing_preparation_sort_key: str = "metaText"
    billing_preparation_sort_direction: str = "desc"
    billing_line_sort_key: str = "metaText"
    billing_line_sort_direction: str = "asc"
    billing_schedule_search: str = ""
    billing_schedule_status: str = ""
    billing_schedule_source_state: str = ""
    billing_preparation_search: str = ""
    billing_preparation_status: str = ""
    billing_preparation_method: str = ""
    billing_preparation_approval_status: str = ""
    billing_preparation_delivery_state: str = ""
    billing_preparation_correction_state: str = ""
    billing_line_search: str = ""
    billing_line_source_type: str = ""
    billing_line_source_state: str = ""
    commercial_projection: FinancialsDetailViewModel = field(
        default_factory=FinancialsDetailViewModel
    )
    empty_state: str = ""

__all__ = [
    "BaselineVarianceRowViewModel",
    "FinancialsCollectionViewModel",
    "FinancialsCommitmentSummaryViewModel",
    "FinancialsDetailFieldViewModel",
    "FinancialsDetailViewModel",
    "FinancialsMetricViewModel",
    "FinancialsManualActualDefaultsViewModel",
    "FinancialsOverviewViewModel",
    "FinancialsRecordViewModel",
    "FinancialsSelectorOptionViewModel",
    "FinancialsWorkspaceViewModel",
]
