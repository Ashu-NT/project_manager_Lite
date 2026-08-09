from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class FinancialCostCodeOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True, slots=True)
class FinancialManualActualOptionsDto:
    currency_code: str = ""
    cost_codes: tuple[FinancialCostCodeOptionDescriptor, ...] = ()
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
    posting_date: str
    financial_period_id: str
    row_version: int
    can_edit: bool
    can_delete: bool
    can_submit: bool
    can_approve: bool
    can_post: bool
    can_reverse: bool


@dataclass(frozen=True, slots=True)
class FinancialCostEntryPageDto:
    items: tuple[FinancialCostEntryDto, ...] = ()
    total: int = 0
    offset: int = 0
    limit: int = 50


@dataclass(frozen=True, slots=True)
class FinancialCostEntryApprovalDto:
    outcome: str
    entry_id: str
    project_id: str
    status: str
    row_version: int
    approval_request_id: str = ""


__all__ = [
    "FinancialCostCodeOptionDescriptor",
    "FinancialCostEntryApprovalDto",
    "FinancialCostEntryDto",
    "FinancialCostEntryPageDto",
    "FinancialManualActualOptionsDto",
]
