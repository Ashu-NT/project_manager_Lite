from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    FinancialAddBudgetLineCommand,
    FinancialCreateBudgetSuccessorCommand,
    FinancialCreateBudgetVersionCommand,
    FinancialDeleteBudgetLineCommand,
    FinancialUpdateBudgetCommand,
    FinancialUpdateBudgetLineCommand,
    FinancialVersionedBudgetCommand,
    FinancialCreateCostCodeCommand,
    FinancialCreateManualActualCommand,
    FinancialDecideActualCommand,
    FinancialPostActualCommand,
    FinancialReverseActualCommand,
    FinancialUpdateActualDraftCommand,
    FinancialVersionedActualCommand,
    ProjectManagementFinancialsDesktopApi,
)
from src.core.platform.api.desktop.approval.approval import PlatformApprovalDesktopApi
from src.core.platform.api.desktop.approval.models.approval import ApprovalDecisionCommand

from .validation import (
    optional_text,
    require_date,
    require_decimal,
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
        )
    )


def create_budget_version(desktop_api, project_id: str, name: str, currency: str):
    return desktop_api.create_budget_version(
        FinancialCreateBudgetVersionCommand(
            project_id=str(project_id or "").strip(),
            name=str(name or "").strip(),
            currency_code=str(currency or "").strip().upper(),
        )
    )


def create_budget_successor(desktop_api, predecessor_id: str, name: str):
    return desktop_api.create_budget_successor(
        FinancialCreateBudgetSuccessorCommand(
            predecessor_budget_id=str(predecessor_id or "").strip(),
            name=str(name or "").strip(),
        )
    )


def update_budget(desktop_api, budget_id: str, version: int, name: str, notes: str):
    return desktop_api.update_budget(
        FinancialUpdateBudgetCommand(
            budget_id=str(budget_id or "").strip(),
            expected_version=int(version),
            name=str(name or "").strip(),
            notes=str(notes or "").strip(),
        )
    )


def delete_budget(desktop_api, budget_id: str, version: int) -> None:
    desktop_api.delete_budget(
        FinancialVersionedBudgetCommand(
            budget_id=str(budget_id or "").strip(), expected_version=int(version)
        )
    )


def add_budget_line(
    desktop_api,
    budget_id: str,
    parent_version: int,
    cost_code_id: str,
    task_id: str,
    description: str,
    amount: str,
    currency: str,
):
    return desktop_api.add_budget_line(
        FinancialAddBudgetLineCommand(
            budget_id=str(budget_id or "").strip(),
            expected_parent_version=int(parent_version),
            cost_code_id=str(cost_code_id or "").strip(),
            task_id=str(task_id or "").strip() or None,
            description=str(description or "").strip(),
            amount=str(amount or "").strip(),
            currency_code=str(currency or "").strip().upper(),
        )
    )


def update_budget_line(
    desktop_api,
    line_id: str,
    line_version: int,
    parent_version: int,
    cost_code_id: str,
    task_id: str,
    description: str,
    amount: str,
    currency: str,
):
    return desktop_api.update_budget_line(
        FinancialUpdateBudgetLineCommand(
            budget_line_id=str(line_id or "").strip(),
            expected_version=int(line_version),
            expected_parent_version=int(parent_version),
            cost_code_id=str(cost_code_id or "").strip(),
            task_id=str(task_id or "").strip() or None,
            description=str(description or "").strip(),
            amount=str(amount or "").strip(),
            currency_code=str(currency or "").strip().upper(),
        )
    )


def delete_budget_line(
    desktop_api, line_id: str, line_version: int, parent_version: int
) -> None:
    desktop_api.delete_budget_line(
        FinancialDeleteBudgetLineCommand(
            budget_line_id=str(line_id or "").strip(),
            expected_version=int(line_version),
            expected_parent_version=int(parent_version),
        )
    )


def submit_budget(desktop_api, budget_id: str, version: int, notes: str):
    return desktop_api.submit_budget(
        FinancialVersionedBudgetCommand(
            budget_id=str(budget_id or "").strip(),
            expected_version=int(version),
            notes=str(notes or "").strip(),
        )
    )


def request_budget_approval(desktop_api, budget_id: str, version: int, notes: str):
    return desktop_api.request_budget_approval(
        FinancialVersionedBudgetCommand(
            budget_id=str(budget_id or "").strip(),
            expected_version=int(version),
            notes=str(notes or "").strip(),
        )
    )


def close_budget(desktop_api, budget_id: str, version: int, notes: str):
    return desktop_api.close_budget(
        FinancialVersionedBudgetCommand(
            budget_id=str(budget_id or "").strip(),
            expected_version=int(version),
            notes=str(notes or "").strip(),
        )
    )


def decide_budget_approval(
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
            else "The Budget approval decision could not be completed."
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


__all__ = [
    "add_budget_line",
    "approve_actual",
    "close_budget",
    "create_budget_successor",
    "create_budget_version",
    "create_cost_code",
    "create_manual_actual",
    "decide_budget_approval",
    "delete_budget",
    "delete_budget_line",
    "post_actual",
    "reject_actual",
    "reverse_actual",
    "submit_actual",
    "submit_budget",
    "request_budget_approval",
    "update_budget",
    "update_budget_line",
]
