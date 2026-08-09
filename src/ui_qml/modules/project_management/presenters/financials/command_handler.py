from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    FinancialCreateManualActualCommand,
    ProjectManagementFinancialsDesktopApi,
)

from .validation import (
    optional_text,
    require_date,
    require_decimal,
    require_text,
)

def create_manual_actual(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    payload: dict[str, Any],
) -> None:
    command = FinancialCreateManualActualCommand(
        project_id=require_text(payload, "projectId", "Select a project before creating an actual."),
        command_id=require_text(payload, "commandId", "Financial command ID is required."),
        description=require_text(payload, "description", "Description is required."),
        amount=require_decimal(payload, "amount", "Amount must be a valid number."),
        currency_code=require_text(payload, "currency", "Currency is required."),
        transaction_date=require_date(
            payload, "transactionDate", "Transaction date must use YYYY-MM-DD."
        ),
        cost_code_id=require_text(payload, "costCodeId", "Select a cost code."),
        entry_kind=optional_text(payload, "entryKind") or "actual",
        task_id=optional_text(payload, "taskId"),
        resource_id=optional_text(payload, "resourceId"),
    )
    desktop_api.create_manual_actual(command)


__all__ = ["create_manual_actual"]
