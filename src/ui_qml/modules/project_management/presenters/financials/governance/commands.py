from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    FinancialChangeCostCodeStatusCommand,
    FinancialCostCodeRestrictionCommand,
    FinancialCreateCostCodeCommand,
    FinancialTransitionProfileCommand,
    FinancialUpdateCostCodeCommand,
    FinancialUpdateProfileCommand,
    ProjectManagementFinancialsDesktopApi,
)
from src.ui_qml.modules.project_management.presenters.financials.shared.commands import (
    _optional_date,
)
from src.ui_qml.modules.project_management.presenters.financials.shared.validation import (
    optional_text,
    require_int,
    require_text,
)


def create_cost_code(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    payload: dict[str, Any],
) -> None:
    desktop_api.create_cost_code(
        FinancialCreateCostCodeCommand(
            project_id=require_text(
                payload, "projectId", "Select a project before creating a cost code."
            ),
            code=require_text(payload, "code", "Cost code is required."),
            name=require_text(payload, "name", "Cost-code name is required."),
            description=optional_text(payload, "description") or "",
            parent_id=optional_text(payload, "parentId"),
            external_system=optional_text(payload, "externalSystem"),
            external_reference=optional_text(payload, "externalReference"),
            effective_from=_optional_date(payload, "effectiveFrom"),
            effective_to=_optional_date(payload, "effectiveTo"),
        )
    )


def update_financial_profile(desktop_api, payload: dict[str, Any]) -> None:
    desktop_api.update_financial_profile(
        FinancialUpdateProfileCommand(
            project_id=require_text(payload, "projectId", "Select a project."),
            expected_version=require_int(payload, "version", "Profile version is required."),
            currency_code=require_text(payload, "currency", "Currency is required.").upper(),
            billing_method=require_text(payload, "billingMethod", "Billing method is required."),
            budget_control_mode=require_text(payload, "budgetControlMode", "Budget control is required."),
            cost_code_policy=require_text(payload, "costCodePolicy", "Cost-code policy is required."),
            financial_start_date=_optional_date(payload, "financialStartDate"),
            financial_end_date=_optional_date(payload, "financialEndDate"),
            is_funded=bool(payload.get("isFunded", False)),
            is_billable=bool(payload.get("isBillable", False)),
            default_cost_code_id=optional_text(payload, "defaultCostCodeId"),
        )
    )


def transition_financial_profile(desktop_api, payload: dict[str, Any]) -> None:
    desktop_api.transition_financial_profile(
        FinancialTransitionProfileCommand(
            project_id=require_text(payload, "projectId", "Select a project."),
            expected_version=require_int(payload, "version", "Profile version is required."),
            target_status=require_text(payload, "targetStatus", "Target status is required."),
        )
    )


def update_cost_code(desktop_api, payload: dict[str, Any]) -> None:
    desktop_api.update_cost_code(
        FinancialUpdateCostCodeCommand(
            cost_code_id=require_text(payload, "costCodeId", "Select a cost code."),
            expected_version=require_int(payload, "version", "Cost-code version is required."),
            code=require_text(payload, "code", "Cost code is required."),
            name=require_text(payload, "name", "Cost-code name is required."),
            description=optional_text(payload, "description") or "",
            parent_id=optional_text(payload, "parentId"),
            external_system=optional_text(payload, "externalSystem"),
            external_reference=optional_text(payload, "externalReference"),
            effective_from=_optional_date(payload, "effectiveFrom"),
            effective_to=_optional_date(payload, "effectiveTo"),
        )
    )


def change_cost_code_status(desktop_api, payload: dict[str, Any]) -> None:
    desktop_api.change_cost_code_status(
        FinancialChangeCostCodeStatusCommand(
            cost_code_id=require_text(payload, "costCodeId", "Select a cost code."),
            expected_version=require_int(payload, "version", "Cost-code version is required."),
            activate=bool(payload.get("activate", False)),
        )
    )


def add_cost_code_restriction(desktop_api, payload: dict[str, Any]) -> None:
    desktop_api.add_cost_code_restriction(
        FinancialCostCodeRestrictionCommand(
            project_id=require_text(payload, "projectId", "Select a project."),
            cost_code_id=require_text(payload, "costCodeId", "Select a cost code."),
        )
    )


def remove_cost_code_restriction(desktop_api, payload: dict[str, Any]) -> None:
    desktop_api.remove_cost_code_restriction(
        FinancialCostCodeRestrictionCommand(
            project_id=require_text(payload, "projectId", "Select a project."),
            cost_code_id=require_text(payload, "costCodeId", "Select a cost code."),
        )
    )
