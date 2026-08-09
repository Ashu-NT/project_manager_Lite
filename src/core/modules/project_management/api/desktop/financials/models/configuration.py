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
    budget_versions: tuple[FinancialConfigurationRecordDto, ...] = ()
    budget_lines: tuple[FinancialConfigurationRecordDto, ...] = ()
    rate_cards: tuple[FinancialConfigurationRecordDto, ...] = ()
    rate_lines: tuple[FinancialConfigurationRecordDto, ...] = ()
    planned_cost_versions: tuple[FinancialConfigurationRecordDto, ...] = ()
    planned_cost_lines: tuple[FinancialConfigurationRecordDto, ...] = ()


__all__ = [
    "FinancialConfigurationFieldDto",
    "FinancialConfigurationRecordDto",
    "FinancialConfigurationWorkspaceDto",
    "FinancialProfileDto",
]
