from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class FinancialForecastDto:
    project_id: str
    basis: str
    basis_label: str
    budget: str
    budget_label: str
    actual: str
    actual_label: str
    etc: str | None
    etc_label: str
    eac: str | None
    eac_label: str
    vac: str | None
    vac_label: str
    is_over_budget: bool
    has_approved_forecast: bool
    forecast_revision: int | None
    forecast_as_of: date | None


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


__all__ = [
    "FinancialForecastDetailDto",
    "FinancialForecastDto",
    "FinancialForecastTableRecordDto",
    "FinancialForecastWorkspaceDto",
]
