from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FinancialBillingTableRecordDto:
    id: str
    title: str
    status_label: str
    subtitle: str
    supporting_text: str
    meta_text: str
    state: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class FinancialBillingDetailDto:
    id: str = ""
    title: str = ""
    status_label: str = ""
    subtitle: str = ""
    description: str = ""
    fields: tuple[tuple[str, str, str], ...] = ()
    state: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class FinancialBillingReadWorkspaceDto:
    profile: FinancialBillingDetailDto = field(default_factory=FinancialBillingDetailDto)
    selected_preparation_id: str = ""
    selected_preparation: FinancialBillingDetailDto = field(default_factory=FinancialBillingDetailDto)
    schedule: tuple[FinancialBillingTableRecordDto, ...] = ()
    schedule_page: int = 1
    schedule_page_size: int = 50
    schedule_total: int = 0
    schedule_sort_key: str = "supportingText"
    schedule_sort_direction: str = "asc"
    preparations: tuple[FinancialBillingTableRecordDto, ...] = ()
    preparation_page: int = 1
    preparation_page_size: int = 50
    preparation_total: int = 0
    preparation_sort_key: str = "metaText"
    preparation_sort_direction: str = "desc"
    lines: tuple[FinancialBillingTableRecordDto, ...] = ()
    line_page: int = 1
    line_page_size: int = 50
    line_total: int = 0
    line_sort_key: str = "metaText"
    line_sort_direction: str = "asc"
    schedule_search: str = ""
    schedule_status: str = ""
    schedule_source_state: str = ""
    preparation_search: str = ""
    preparation_status: str = ""
    preparation_method: str = ""
    preparation_approval_status: str = ""
    preparation_delivery_state: str = ""
    preparation_correction_state: str = ""
    line_search: str = ""
    line_source_type: str = ""
    line_source_state: str = ""


@dataclass(frozen=True)
class FinancialAccountingStatusPageDto:
    items: tuple[FinancialBillingTableRecordDto, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 50
    sort_key: str = "metaText"
    sort_direction: str = "desc"


__all__ = [
    "FinancialBillingDetailDto",
    "FinancialAccountingStatusPageDto",
    "FinancialBillingReadWorkspaceDto",
    "FinancialBillingTableRecordDto",
]
