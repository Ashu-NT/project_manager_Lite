from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class FinancialCostCodeOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True, slots=True)
class FinancialManualActualOptionsDto:
    currency_code: str = ""
    entry_kinds: tuple[FinancialCostCodeOptionDescriptor, ...] = field(
        default_factory=lambda: (
            FinancialCostCodeOptionDescriptor("actual", "Actual"),
            FinancialCostCodeOptionDescriptor("adjustment", "Adjustment"),
        )
    )


@dataclass(frozen=True, slots=True)
class FinancialCostEntryDto:
    id: str
    project_id: str
    description: str
    entry_kind: str
    status: str
    amount: str
    amount_label: str
    currency_code: str
    transaction_date: str
    cost_code_id: str
    task_id: str
    resource_id: str
    source_label: str
    source_module: str
    source_type: str
    source_owned: bool
    posting_date: str
    financial_period_id: str
    row_version: int
    can_edit: bool
    can_delete: bool
    can_submit: bool
    can_approve: bool
    can_reject: bool
    can_post: bool
    can_reverse: bool
    approval_action: str
    read_only_reason: str


@dataclass(frozen=True, slots=True)
class FinancialCostEntryPageDto:
    items: tuple[FinancialCostEntryDto, ...] = ()
    total: int = 0
    offset: int = 0
    limit: int = 50
    sort_key: str = "metaText"
    sort_direction: str = "desc"
    can_create_manual_actual: bool = False


@dataclass(frozen=True, slots=True)
class FinancialCostEntryApprovalDto:
    outcome: str
    entry_id: str
    project_id: str
    status: str
    row_version: int
    approval_request_id: str = ""


@dataclass(frozen=True, slots=True)
class FinancialPostingFailureDto:
    id: str
    event_id: str
    source_id: str
    source_revision: int
    resource_id: str
    work_date: str
    status: str
    failure_code: str
    failure_message: str
    failure_category: str
    corrective_action: str
    attempt_count: int
    max_attempts: int
    retryable: bool
    updated_at: str


@dataclass(frozen=True, slots=True)
class FinancialPostingFailurePageDto:
    items: tuple[FinancialPostingFailureDto, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 50
    sort_key: str = "updated"
    sort_direction: str = "desc"


__all__ = [
    "FinancialCostCodeOptionDescriptor",
    "FinancialCostEntryApprovalDto",
    "FinancialCostEntryDto",
    "FinancialCostEntryPageDto",
    "FinancialManualActualOptionsDto",
    "FinancialPostingFailureDto",
    "FinancialPostingFailurePageDto",
]
