from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.core.modules.project_management.api.desktop import (
    FinancialActivateBillingProfileCommand,
    FinancialAddApprovedTimeBillingSourceCommand,
    FinancialAddBillingScheduleLineCommand,
    FinancialAddCostPlusBillingSourceCommand,
    FinancialAddFixedPriceBillingSourceCommand,
    FinancialCreateBillingPreparationCommand,
    FinancialCreateBillingProfileCommand,
    FinancialMarkBillingScheduleLineReadyCommand,
    FinancialRemoveDraftBillingLineCommand,
    FinancialVersionedBillingPreparationCommand,
)
from src.core.platform.api.desktop.approval.approval import PlatformApprovalDesktopApi
from src.core.platform.api.desktop.approval.models.approval import (
    ApprovalDecisionCommand,
)
from src.ui_qml.modules.project_management.presenters.financials.shared.validation import (
    optional_text,
    require_date,
    require_decimal,
    require_int,
    require_text,
)


def create_billing_profile(desktop_api, payload: dict[str, Any]):
    return desktop_api.create_billing_profile(
        FinancialCreateBillingProfileCommand(
            project_id=require_text(payload, "projectId", "Select a project."),
            contract_reference=require_text(payload, "contractReference", "Contract reference is required."),
            contract_value=require_decimal(payload, "contractValue", "Contract value is required."),
            customer_party_id=optional_text(payload, "customerPartyId"),
            external_customer_reference=optional_text(payload, "externalCustomerReference"),
            purchase_order_reference=optional_text(payload, "purchaseOrderReference"),
            cost_plus_markup_percent=(
                require_decimal(
                    payload, "costPlusMarkupPercent", "Markup must be a number."
                )
                if optional_text(payload, "costPlusMarkupPercent")
                else Decimal(0)
            ),
            payment_terms_days=require_int(payload, "paymentTermsDays", "Payment terms are required."),
            retention_years=require_int(payload, "retentionYears", "Retention years are required."),
        )
    )


def activate_billing_profile(desktop_api, payload: dict[str, Any]):
    return desktop_api.activate_billing_profile(
        FinancialActivateBillingProfileCommand(
            project_id=require_text(payload, "projectId", "Select a project."),
            expected_version=require_int(payload, "version", "Profile version is required."),
        )
    )


def add_billing_schedule_line(desktop_api, payload: dict[str, Any]):
    return desktop_api.add_billing_schedule_line(
        FinancialAddBillingScheduleLineCommand(
            project_id=require_text(payload, "projectId", "Select a project."),
            name=require_text(payload, "name", "Schedule line name is required."),
            amount=require_decimal(payload, "amount", "Schedule amount is required."),
            due_date=require_date(payload, "dueDate", "Due date must use YYYY-MM-DD."),
            task_id=optional_text(payload, "taskId"),
            acceptance_reference=optional_text(payload, "acceptanceReference"),
        )
    )


def mark_billing_schedule_line_ready(desktop_api, payload: dict[str, Any]):
    return desktop_api.mark_billing_schedule_line_ready(
        FinancialMarkBillingScheduleLineReadyCommand(
            line_id=require_text(payload, "lineId", "Select a schedule line."),
            expected_version=require_int(payload, "version", "Schedule line version is required."),
        )
    )


def create_billing_preparation(desktop_api, payload: dict[str, Any]):
    return desktop_api.create_billing_preparation(
        FinancialCreateBillingPreparationCommand(
            project_id=require_text(payload, "projectId", "Select a project."),
            preparation_number=require_text(payload, "preparationNumber", "Preparation number is required."),
            period_start=require_date(payload, "periodStart", "Period start must use YYYY-MM-DD."),
            period_end=require_date(payload, "periodEnd", "Period end must use YYYY-MM-DD."),
            idempotency_key=require_text(payload, "idempotencyKey", "Idempotency key is required."),
            correction_of_preparation_id=optional_text(payload, "correctionOfPreparationId"),
        )
    )


def add_billing_source(desktop_api, payload: dict[str, Any]):
    preparation_id = require_text(payload, "preparationId", "Select a preparation.")
    expected_version = require_int(payload, "version", "Preparation version is required.")
    source_id = require_text(payload, "sourceId", "Select an eligible source.")
    source_type = require_text(payload, "sourceType", "Source type is required.").lower()
    if source_type == "schedule_line":
        return desktop_api.add_fixed_price_billing_source(
            FinancialAddFixedPriceBillingSourceCommand(preparation_id, expected_version, source_id)
        )
    if source_type == "approved_time":
        return desktop_api.add_approved_time_billing_source(
            FinancialAddApprovedTimeBillingSourceCommand(preparation_id, expected_version, source_id)
        )
    if source_type == "posted_cost":
        return desktop_api.add_cost_plus_billing_source(
            FinancialAddCostPlusBillingSourceCommand(preparation_id, expected_version, source_id)
        )
    raise ValueError("Unsupported billing source type.")


def remove_billing_line(desktop_api, payload: dict[str, Any]):
    return desktop_api.remove_draft_billing_line(
        FinancialRemoveDraftBillingLineCommand(
            preparation_id=require_text(payload, "preparationId", "Select a preparation."),
            line_id=require_text(payload, "lineId", "Select a billing line."),
            expected_version=require_int(payload, "version", "Preparation version is required."),
        )
    )


def version_billing_preparation(desktop_api, payload: dict[str, Any], action: str):
    command = FinancialVersionedBillingPreparationCommand(
        preparation_id=require_text(payload, "preparationId", "Select a preparation."),
        expected_version=require_int(payload, "version", "Preparation version is required."),
    )
    return getattr(desktop_api, action)(command)


def decide_billing_approval(
    approval_api: PlatformApprovalDesktopApi | None, request_id: str, *, approve: bool, note: str = ""
) -> None:
    if approval_api is None:
        raise RuntimeError("Platform approval API is not connected.")
    command = ApprovalDecisionCommand(request_id=str(request_id or "").strip(), note=note.strip() or None)
    result = approval_api.approve_and_apply(command) if approve else approval_api.reject(command)
    if not result.ok:
        raise RuntimeError(result.error.message if result.error else "Billing decision failed.")
