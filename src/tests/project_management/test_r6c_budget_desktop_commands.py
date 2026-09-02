from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop.financials import (
    FinancialAddBudgetLineCommand,
    FinancialCreateBudgetVersionCommand,
    FinancialVersionedBudgetCommand,
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.application.financials.budgets import (
    BudgetApprovalOutcome,
    BudgetApprovalResult,
)
from src.core.modules.project_management.domain.financials.budget import BudgetStatus


class _BudgetService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def create_budget(self, *args, **kwargs):
        self.calls.append(("create_budget", args, kwargs))
        return SimpleNamespace(
            id="budget-1",
            project_id=args[0],
            status=BudgetStatus.DRAFT,
            row_version=1,
        )

    def add_line(self, *args, **kwargs):
        self.calls.append(("add_line", args, kwargs))
        return SimpleNamespace(id="line-1", budget_id=args[0], row_version=1)

    def request_budget_approval(self, *args, **kwargs):
        self.calls.append(("request_budget_approval", args, kwargs))
        return BudgetApprovalResult(
            outcome=BudgetApprovalOutcome.PENDING_APPROVAL,
            budget_id=args[0],
            project_id="project-1",
            budget_status=BudgetStatus.SUBMITTED,
            row_version=kwargs["expected_version"],
            approval_request_id="approval-1",
        )


class _Boundary:
    def __init__(self) -> None:
        self.service = _BudgetService()
        self.project_ids: list[str | None] = []

    def budget(self, command, *, project_id=None):
        self.project_ids.append(project_id)
        return command(self.service)


def test_typed_budget_commands_route_through_governance_boundary() -> None:
    boundary = _Boundary()
    api = ProjectManagementFinancialsDesktopApi(
        finance_governance_commands=boundary  # type: ignore[arg-type]
    )

    created = api.create_budget_version(
        FinancialCreateBudgetVersionCommand(
            project_id="project-1", name="FY27", currency_code="XAF"
        )
    )
    line = api.add_budget_line(
        FinancialAddBudgetLineCommand(
            budget_id=created.budget_id,
            expected_parent_version=created.row_version,
            cost_code_id="cost-code-1",
            task_id=None,
            description="Engineering",
            amount="1250.50",
            currency_code="XAF",
        )
    )
    requested = api.request_budget_approval(
        FinancialVersionedBudgetCommand(
            budget_id=created.budget_id,
            expected_version=2,
            notes="Ready",
        )
    )

    assert line.budget_id == created.budget_id
    assert requested.approval_request_id == "approval-1"
    assert boundary.project_ids == ["project-1", None, None]
    add_call = next(call for call in boundary.service.calls if call[0] == "add_line")
    assert add_call[2]["amount"] == Decimal("1250.50")
    assert any(call[0] == "request_budget_approval" for call in boundary.service.calls)


def test_qml_budget_commands_use_explicit_typed_controller_slots() -> None:
    controller = Path(
        "src/ui_qml/modules/project_management/controllers/financials/"
        "financials_workspace_controller.py"
    ).read_text(encoding="utf-8")
    host = Path(
        "src/ui_qml/modules/project_management/qml/workspaces/financials/dialogs/"
        "FinancialsDialogHost.qml"
    ).read_text(encoding="utf-8")

    for slot in (
        "createBudgetVersion",
        "createBudgetSuccessor",
        "updateBudget",
        "addBudgetLine",
        "updateBudgetLine",
        "deleteBudgetLine",
        "submitBudget",
        "requestBudgetApproval",
        "decideBudgetApproval",
        "closeBudget",
    ):
        assert f"def {slot}(" in controller
        assert f"workspaceController.{slot}(" in host

    assert "createBudgetVersion(payload" not in host
    assert "addBudgetLine(payload" not in host
