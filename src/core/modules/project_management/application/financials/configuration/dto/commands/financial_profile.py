from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.application.financials.configuration._command_values import (
    PROFILE_FIELD_UNSET,
    ProfileFieldUnset,
)


@dataclass(frozen=True, slots=True)
class FinancialUpdateProfileCommand:
    project_id: str
    expected_version: int
    currency_code: str | ProfileFieldUnset = PROFILE_FIELD_UNSET
    billing_method: str | ProfileFieldUnset = PROFILE_FIELD_UNSET
    budget_control_mode: str | ProfileFieldUnset = PROFILE_FIELD_UNSET
    cost_code_policy: str | ProfileFieldUnset = PROFILE_FIELD_UNSET
    financial_start_date: date | None | ProfileFieldUnset = PROFILE_FIELD_UNSET
    financial_end_date: date | None | ProfileFieldUnset = PROFILE_FIELD_UNSET
    is_funded: bool | ProfileFieldUnset = PROFILE_FIELD_UNSET
    is_billable: bool | ProfileFieldUnset = PROFILE_FIELD_UNSET
    default_cost_code_id: str | None | ProfileFieldUnset = PROFILE_FIELD_UNSET


@dataclass(frozen=True, slots=True)
class FinancialTransitionProfileCommand:
    project_id: str
    expected_version: int
    target_status: str
