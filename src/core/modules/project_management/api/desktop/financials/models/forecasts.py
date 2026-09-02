from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class FinancialForecastTableRecordDto:
    id: str
    title: str
    status_label: str
    subtitle: str
    supporting_text: str
    meta_text: str
    state: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class FinancialForecastDetailDto:
    id: str = ""
    title: str = ""
    status_label: str = ""
    subtitle: str = ""
    fields: tuple[tuple[str, str, str], ...] = ()
    state: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class FinancialForecastWorkspaceDto:
    selected_forecast_id: str = ""
    selected_forecast: FinancialForecastDetailDto = field(
        default_factory=FinancialForecastDetailDto
    )
    versions: tuple[FinancialForecastTableRecordDto, ...] = ()
    version_page: int = 1
    version_page_size: int = 50
    version_total: int = 0
    version_sort_key: str = "revision"
    version_sort_direction: str = "desc"
    lines: tuple[FinancialForecastTableRecordDto, ...] = ()
    line_page: int = 1
    line_page_size: int = 50
    line_total: int = 0
    line_sort_key: str = "title"
    line_sort_direction: str = "asc"
    version_search: str = ""
    version_status: str = ""
    generation_mode: str = ""
    line_search: str = ""
    line_source_type: str = ""
    show_generate: bool = False
    can_generate: bool = False
    generate_disabled_reason: str = ""


@dataclass(frozen=True, slots=True)
class FinancialForecastMutationDto:
    forecast_id: str
    project_id: str
    status: str
    row_version: int
    approval_request_id: str = ""


__all__ = [
    "FinancialForecastDetailDto",
    "FinancialForecastTableRecordDto",
    "FinancialForecastMutationDto",
    "FinancialForecastWorkspaceDto",
]
