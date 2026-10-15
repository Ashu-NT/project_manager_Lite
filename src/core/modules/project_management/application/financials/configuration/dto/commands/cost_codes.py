from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True, slots=True)
class FinancialCreateCostCodeCommand:
    project_id: str | None = field(default=None, kw_only=True)
    code: str
    name: str
    description: str = ""
    parent_id: str | None = None
    external_system: str | None = None
    external_reference: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None


@dataclass(frozen=True, slots=True)
class FinancialUpdateCostCodeCommand:
    cost_code_id: str
    expected_version: int
    code: str
    name: str
    description: str
    parent_id: str | None
    external_system: str | None
    external_reference: str | None
    effective_from: date | None
    effective_to: date | None


@dataclass(frozen=True, slots=True)
class FinancialChangeCostCodeStatusCommand:
    cost_code_id: str
    expected_version: int
    activate: bool


@dataclass(frozen=True, slots=True)
class FinancialCostCodeRestrictionCommand:
    project_id: str
    cost_code_id: str
