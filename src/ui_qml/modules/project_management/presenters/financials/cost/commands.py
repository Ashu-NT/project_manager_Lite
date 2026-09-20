from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    FinancialCreateManualActualCommand,
    FinancialDecideActualCommand,
    FinancialPostActualCommand,
    FinancialReverseActualCommand,
    FinancialUpdateActualDraftCommand,
    FinancialVersionedActualCommand,
    ProjectManagementFinancialsDesktopApi,
)
from src.ui_qml.modules.project_management.presenters.financials.shared.validation import (
    optional_text,
    require_date,
    require_decimal,
    require_int,
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


def update_actual_draft(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    payload: dict[str, Any],
) -> None:
    desktop_api.update_actual_draft(
        FinancialUpdateActualDraftCommand(
            entry_id=require_text(payload, "entryId", "Select an actual draft to edit."),
            expected_version=require_int(
                payload, "rowVersion", "Entry version is required."
            ),
            description=require_text(payload, "description", "Description is required."),
            amount=require_decimal(payload, "amount", "Amount must be a valid number."),
            currency_code=require_text(payload, "currency", "Currency is required."),
            transaction_date=require_date(
                payload, "transactionDate", "Transaction date must use YYYY-MM-DD."
            ),
            cost_code_id=require_text(payload, "costCodeId", "Select a cost code."),
            task_id=optional_text(payload, "taskId"),
            resource_id=optional_text(payload, "resourceId"),
        )
    )


def delete_actual_draft(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    payload: dict[str, Any],
) -> None:
    desktop_api.delete_actual_draft(
        FinancialVersionedActualCommand(
            entry_id=require_text(payload, "entryId", "Select an actual draft to delete."),
            expected_version=require_int(
                payload, "rowVersion", "Entry version is required."
            ),
        )
    )


def submit_actual(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    payload: dict[str, Any],
) -> None:
    command = FinancialVersionedActualCommand(
        entry_id=require_text(payload, "entryId", "Select an actual entry to submit."),
        expected_version=require_int(payload, "rowVersion", "Entry version is required."),
    )
    desktop_api.submit_actual(command)


def approve_actual(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    payload: dict[str, Any],
) -> None:
    command = FinancialDecideActualCommand(
        entry_id=require_text(payload, "entryId", "Select an actual entry to approve."),
        expected_version=require_int(payload, "rowVersion", "Entry version is required."),
        notes=optional_text(payload, "notes") or "",
    )
    desktop_api.approve_actual(command)


def reject_actual(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    payload: dict[str, Any],
) -> None:
    command = FinancialDecideActualCommand(
        entry_id=require_text(payload, "entryId", "Select an actual entry to reject."),
        expected_version=require_int(payload, "rowVersion", "Entry version is required."),
        notes=optional_text(payload, "notes") or "",
    )
    desktop_api.reject_actual(command)


def post_actual(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    payload: dict[str, Any],
) -> None:
    command = FinancialPostActualCommand(
        entry_id=require_text(payload, "entryId", "Select an actual entry to post."),
        expected_version=require_int(payload, "rowVersion", "Entry version is required."),
        posting_date=require_date(
            payload, "postingDate", "Posting date must use YYYY-MM-DD."
        ),
    )
    desktop_api.post_actual(command)


def reverse_actual(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    payload: dict[str, Any],
) -> None:
    command = FinancialReverseActualCommand(
        entry_id=require_text(payload, "entryId", "Select an actual entry to reverse."),
        expected_version=require_int(payload, "rowVersion", "Entry version is required."),
        command_id=require_text(payload, "commandId", "Financial command ID is required."),
        posting_date=require_date(
            payload, "postingDate", "Posting date must use YYYY-MM-DD."
        ),
        reason=require_text(payload, "reason", "A reversal reason is required."),
    )
    desktop_api.reverse_actual(command)
