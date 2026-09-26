from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    FinancialChangeImpactCommand,
    FinancialCreateChangeCommand,
    FinancialRemoveChangeImpactCommand,
    FinancialSubmitChangeCommand,
    FinancialUpdateChangeCommand,
    FinancialUpdateChangeImpactCommand,
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


def create_financial_change(desktop_api, payload: dict[str, Any]):
    return desktop_api.create_financial_change(
        FinancialCreateChangeCommand(
            project_id=require_text(
                payload, "projectId", "Select a project before creating a Change Request."
            ),
            title=require_text(payload, "title", "Change title is required."),
            reason=require_text(payload, "reason", "Change reason is required."),
            description=optional_text(payload, "description") or "",
            effective_date=require_date(
                payload, "effectiveDate", "Effective date must use YYYY-MM-DD."
            ).isoformat(),
        )
    )


def update_financial_change(desktop_api, payload: dict[str, Any]):
    return desktop_api.update_financial_change(
        FinancialUpdateChangeCommand(
            change_id=require_text(payload, "changeId", "Select a Change Request."),
            expected_version=require_int(
                payload, "rowVersion", "Change version is required."
            ),
            title=require_text(payload, "title", "Change title is required."),
            reason=require_text(payload, "reason", "Change reason is required."),
            description=optional_text(payload, "description") or "",
            effective_date=require_date(
                payload, "effectiveDate", "Effective date must use YYYY-MM-DD."
            ).isoformat(),
        )
    )


def _impact_fields(payload: dict[str, Any]) -> dict[str, Any]:
    impact_type = require_text(payload, "impactType", "Impact type is required.")
    amount = require_decimal(
        payload, "amount", "Impact amount must be a valid number."
    )
    return {
        "change_id": require_text(payload, "changeId", "Select a Change Request."),
        "expected_change_version": require_int(
            payload, "changeVersion", "Change version is required."
        ),
        "impact_type": impact_type,
        "description": require_text(
            payload, "description", "Impact description is required."
        ),
        "amount": format(amount, "f"),
        "currency_code": (optional_text(payload, "currency") or "").upper(),
        "cost_code_id": optional_text(payload, "costCodeId"),
        "task_id": optional_text(payload, "taskId"),
        "target_line_id": optional_text(payload, "targetLineId"),
        "schedule_start": optional_text(payload, "scheduleStart") or "",
        "schedule_finish": optional_text(payload, "scheduleFinish") or "",
    }


def add_financial_change_impact(desktop_api, payload: dict[str, Any]):
    return desktop_api.add_financial_change_impact(
        FinancialChangeImpactCommand(**_impact_fields(payload))
    )


def update_financial_change_impact(desktop_api, payload: dict[str, Any]):
    return desktop_api.update_financial_change_impact(
        FinancialUpdateChangeImpactCommand(
            impact_id=require_text(payload, "impactId", "Select an impact."),
            expected_impact_version=require_int(
                payload, "impactVersion", "Impact version is required."
            ),
            **_impact_fields(payload),
        )
    )


def remove_financial_change_impact(desktop_api, payload: dict[str, Any]):
    return desktop_api.remove_financial_change_impact(
        FinancialRemoveChangeImpactCommand(
            impact_id=require_text(payload, "impactId", "Select an impact."),
            expected_impact_version=require_int(
                payload, "impactVersion", "Impact version is required."
            ),
            expected_change_version=require_int(
                payload, "changeVersion", "Change version is required."
            ),
        )
    )


def submit_financial_change(desktop_api, payload: dict[str, Any]):
    return desktop_api.submit_financial_change(
        FinancialSubmitChangeCommand(
            change_id=require_text(payload, "changeId", "Select a Change Request."),
            expected_version=require_int(
                payload, "rowVersion", "Change version is required."
            ),
        )
    )


def decide_financial_change_approval(
    approval_api: PlatformApprovalDesktopApi | None,
    request_id: str,
    *,
    approve: bool,
    note: str,
) -> None:
    if approval_api is None:
        raise RuntimeError("Platform approval API is not connected.")
    command = ApprovalDecisionCommand(
        request_id=str(request_id or "").strip(),
        note=str(note or "").strip() or None,
    )
    result = (
        approval_api.approve_and_apply(command)
        if approve
        else approval_api.reject(command)
    )
    if not result.ok:
        raise RuntimeError(
            result.error.message
            if result.error is not None
            else "The Financial Change decision could not be completed."
        )
