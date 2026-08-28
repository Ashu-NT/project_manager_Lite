from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FinancialChangeTableRecordDto:
    id: str
    title: str
    status_label: str
    subtitle: str
    supporting_text: str
    meta_text: str
    state: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class FinancialChangeDetailDto:
    id: str = ""
    title: str = ""
    status_label: str = ""
    subtitle: str = ""
    description: str = ""
    fields: tuple[tuple[str, str, str], ...] = ()
    state: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class FinancialChangeWorkspaceDto:
    selected_change_id: str = ""
    selected_change: FinancialChangeDetailDto = field(
        default_factory=FinancialChangeDetailDto
    )
    changes: tuple[FinancialChangeTableRecordDto, ...] = ()
    change_page: int = 1
    change_page_size: int = 50
    change_total: int = 0
    change_sort_key: str = "metaText"
    change_sort_direction: str = "desc"
    impacts: tuple[FinancialChangeTableRecordDto, ...] = ()
    impact_page: int = 1
    impact_page_size: int = 50
    impact_total: int = 0
    impact_sort_key: str = "metaText"
    impact_sort_direction: str = "asc"
    change_search: str = ""
    change_status: str = ""
    change_approval_status: str = ""
    change_applied_state: str = ""
    impact_search: str = ""
    impact_type: str = ""
    impact_applied_state: str = ""


__all__ = [
    "FinancialChangeDetailDto",
    "FinancialChangeTableRecordDto",
    "FinancialChangeWorkspaceDto",
]
