from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FinancialConfigurationFieldDto:
    label: str
    value: str
    supporting_text: str = ""


@dataclass(frozen=True)
class FinancialConfigurationRecordDto:
    id: str
    title: str
    status_label: str
    subtitle: str
    supporting_text: str
    meta_text: str
    state: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class FinancialProfileDto:
    project_id: str = ""
    title: str = "Financial Profile"
    status_label: str = "Not configured"
    subtitle: str = "Project-level currency, controls, and billing policy."
    fields: tuple[FinancialConfigurationFieldDto, ...] = ()


@dataclass(frozen=True)
class FinancialConfigurationWorkspaceDto:
    profile: FinancialProfileDto = field(default_factory=FinancialProfileDto)
    selected_budget_id: str = ""
    can_create_budget_version: bool = False
    budget_versions: tuple[FinancialConfigurationRecordDto, ...] = ()
    budget_version_page: int = 1
    budget_version_page_size: int = 50
    budget_version_total: int = 0
    budget_version_sort_key: str = "revision"
    budget_version_sort_direction: str = "desc"
    budget_lines: tuple[FinancialConfigurationRecordDto, ...] = ()
    budget_line_page: int = 1
    budget_line_page_size: int = 50
    budget_line_total: int = 0
    budget_line_sort_key: str = "metaText"
    budget_line_sort_direction: str = "desc"
    rate_cards: tuple[FinancialConfigurationRecordDto, ...] = ()
    rate_lines: tuple[FinancialConfigurationRecordDto, ...] = ()
    rate_line_page: int = 1
    rate_line_page_size: int = 50
    rate_line_total: int = 0
    selected_planned_cost_version_id: str = ""
    planned_cost_versions: tuple[FinancialConfigurationRecordDto, ...] = ()
    planned_cost_version_page: int = 1
    planned_cost_version_page_size: int = 50
    planned_cost_version_total: int = 0
    planned_cost_version_sort_key: str = "revision"
    planned_cost_version_sort_direction: str = "desc"
    planned_cost_lines: tuple[FinancialConfigurationRecordDto, ...] = ()
    planned_cost_line_page: int = 1
    planned_cost_line_page_size: int = 50
    planned_cost_line_total: int = 0
    planned_cost_line_sort_key: str = "title"
    planned_cost_line_sort_direction: str = "asc"


__all__ = [
    "FinancialConfigurationFieldDto",
    "FinancialConfigurationRecordDto",
    "FinancialConfigurationWorkspaceDto",
    "FinancialProfileDto",
]
