from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    FinancialAddBudgetLineCommand,
    FinancialCreateBudgetSuccessorCommand,
    FinancialCreateBudgetVersionCommand,
    FinancialDeleteBudgetLineCommand,
    FinancialUpdateBudgetCommand,
    FinancialUpdateBudgetLineCommand,
    FinancialVersionedBudgetCommand,
)
from src.core.platform.api.desktop.approval.approval import PlatformApprovalDesktopApi
from src.core.platform.api.desktop.approval.models.approval import (
    ApprovalDecisionCommand,
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
