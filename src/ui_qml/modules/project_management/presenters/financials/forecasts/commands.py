from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    FinancialGenerateForecastCommand,
    FinancialManualEtcCommand,
    FinancialRiskContingencyCommand,
    FinancialVersionedForecastCommand,
)
from src.core.platform.api.desktop.approval.approval import PlatformApprovalDesktopApi
from src.core.platform.api.desktop.approval.models.approval import (
    ApprovalDecisionCommand,
)
from src.ui_qml.modules.project_management.presenters.financials.shared.validation import (
    optional_text,
    require_date,
    require_decimal,
    require_text,
)


def generate_forecast(desktop_api, payload: dict[str, Any]):
    manual = tuple(
        FinancialManualEtcCommand(
            cost_code_id=require_text(item, "costCodeId", "Select a manual ETC cost code."),
            task_id=optional_text(item, "taskId"),
            description=require_text(item, "description", "Manual ETC description is required."),
            amount=require_decimal(item, "amount", "Manual ETC amount must be a valid number."),
            period_start=optional_text(item, "periodStart") or "",
            period_end=optional_text(item, "periodEnd") or "",
        )
        for item in list(payload.get("manualEstimates") or [])
    )
    contingencies = tuple(
        FinancialRiskContingencyCommand(
            risk_id=require_text(item, "riskId", "Select an eligible project Risk."),
            cost_code_id=require_text(item, "costCodeId", "Select a contingency cost code."),
            task_id=optional_text(item, "taskId"),
            description=optional_text(item, "description") or "",
            amount=require_decimal(item, "amount", "Contingency amount must be a valid number."),
            period_start=optional_text(item, "periodStart") or "",
            period_end=optional_text(item, "periodEnd") or "",
        )
        for item in list(payload.get("riskContingencies") or [])
    )
    return desktop_api.generate_forecast(
        FinancialGenerateForecastCommand(
            project_id=require_text(payload, "projectId", "Select a project before generating a Forecast."),
            name=require_text(payload, "name", "Forecast name is required."),
            as_of_date=require_date(
                payload, "asOfDate", "Forecast as-of date must use YYYY-MM-DD."
            ).isoformat(),
            notes=optional_text(payload, "notes") or "",
            manual_estimates=manual,
            risk_contingencies=contingencies,
        )
    )


def submit_forecast(desktop_api, forecast_id: str, version: int, notes: str):
    return desktop_api.submit_forecast(
        FinancialVersionedForecastCommand(
            forecast_id=str(forecast_id or "").strip(),
            expected_version=int(version),
            notes=str(notes or "").strip(),
        )
    )


def request_forecast_approval(desktop_api, forecast_id: str, version: int, notes: str):
    return desktop_api.request_forecast_approval(
        FinancialVersionedForecastCommand(
            forecast_id=str(forecast_id or "").strip(),
            expected_version=int(version),
            notes=str(notes or "").strip(),
        )
    )


def decide_forecast_approval(
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
    result = approval_api.approve_and_apply(command) if approve else approval_api.reject(command)
    if not result.ok:
        raise RuntimeError(
            result.error.message
            if result.error is not None
            else "The Forecast approval decision could not be completed."
        )
