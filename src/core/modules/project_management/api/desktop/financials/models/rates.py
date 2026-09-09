from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FinancialRateTableRecordDto:
    id: str
    title: str
    status_label: str
    subtitle: str
    supporting_text: str
    meta_text: str
    state: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class FinancialRateCardDetailDto:
    id: str = ""
    title: str = ""
    status_label: str = ""
    subtitle: str = ""
    fields: tuple[tuple[str, str, str], ...] = ()
    state: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class FinancialRateWorkspaceDto:
    selected_rate_card_id: str = ""
    selected_rate_card: FinancialRateCardDetailDto = field(
        default_factory=FinancialRateCardDetailDto
    )
    cards: tuple[FinancialRateTableRecordDto, ...] = ()
    card_page: int = 1
    card_page_size: int = 50
    card_total: int = 0
    card_sort_key: str = "title"
    card_sort_direction: str = "asc"
    lines: tuple[FinancialRateTableRecordDto, ...] = ()
    line_page: int = 1
    line_page_size: int = 50
    line_total: int = 0
    line_sort_key: str = "title"
    line_sort_direction: str = "asc"
    card_search: str = ""
    card_scope: str = ""
    card_status: str = ""
    line_search: str = ""
    line_rate_type: str = ""
    line_status: str = ""
    line_effective_status: str = ""
    as_of: str = ""
    can_create_rate_card: bool = False


@dataclass(frozen=True, slots=True)
class FinancialRateMutationDto:
    rate_card_id: str
    rate_line_id: str = ""
    version: int = 1


__all__ = [
    "FinancialRateCardDetailDto",
    "FinancialRateTableRecordDto",
    "FinancialRateMutationDto",
    "FinancialRateWorkspaceDto",
]
