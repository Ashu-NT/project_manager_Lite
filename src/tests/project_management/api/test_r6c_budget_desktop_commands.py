from __future__ import annotations

from pathlib import Path

from src.core.modules.project_management.api.desktop.financials import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.application.financials.budgets.dto.commands.budget_lifecycle import (
    FinancialCreateBudgetVersionCommand,
    FinancialVersionedBudgetCommand,
)
from src.core.modules.project_management.application.financials.budgets.dto.commands.budget_lines import (
    FinancialAddBudgetLineCommand,
)
from src.core.modules.project_management.application.financials.budgets.dto.responses.mutations import (
    FinancialBudgetLineMutationDto,
    FinancialBudgetMutationDto,
)


class _BudgetLifecycleCommands:
    def __init__(self, calls) -> None:
        self.calls = calls

    def create_budget(
        self, command: FinancialCreateBudgetVersionCommand
    ) -> FinancialBudgetMutationDto:
        self.calls.append(("create_budget", (command,), {}))
        return FinancialBudgetMutationDto(
            budget_id="budget-1",
            project_id=command.project_id,
            status="draft",
            row_version=1,
        )


class _BudgetLineCommands:
    def __init__(self, calls) -> None:
        self.calls = calls

    def add_line(
        self, command: FinancialAddBudgetLineCommand
    ) -> FinancialBudgetLineMutationDto:
        self.calls.append(("add_line", (command,), {}))
        return FinancialBudgetLineMutationDto(
            budget_line_id="line-1", budget_id=command.budget_id, row_version=1
        )


class _BudgetApprovalCommands:
    def __init__(self, calls) -> None:
        self.calls = calls

    def request_budget_approval(
        self, command: FinancialVersionedBudgetCommand
    ) -> FinancialBudgetMutationDto:
        self.calls.append(("request_budget_approval", (command,), {}))
        return FinancialBudgetMutationDto(
            budget_id=command.budget_id,
            project_id="project-1",
            status="submitted",
            row_version=command.expected_version,
            approval_request_id="approval-1",
        )


class _Boundary:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []
        self.lifecycle = _BudgetLifecycleCommands(self.calls)
        self.lines = _BudgetLineCommands(self.calls)
        self.approval = _BudgetApprovalCommands(self.calls)
        self.command_count = 0

    def budget_lifecycle(self, command):
        self.command_count += 1
        return command(self.lifecycle)

    def budget_lines(self, command):
        self.command_count += 1
        return command(self.lines)

    def budget_approval(self, command):
        self.command_count += 1
        return command(self.approval)


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

    assert created == FinancialBudgetMutationDto("budget-1", "project-1", "draft", 1)
    assert line == FinancialBudgetLineMutationDto("line-1", created.budget_id, 1)
    assert requested.status == "submitted"
    assert requested.approval_request_id == "approval-1"
    assert boundary.command_count == 3
    create_call = next(call for call in boundary.calls if call[0] == "create_budget")
    assert create_call[1][0].project_id == "project-1"
    add_call = next(call for call in boundary.calls if call[0] == "add_line")
    assert add_call[1][0].amount == "1250.50"
    assert add_call[2] == {}
    assert any(call[0] == "request_budget_approval" for call in boundary.calls)


def test_qml_budget_commands_use_explicit_typed_controller_slots() -> None:
    controller = Path(
        "src/ui_qml/modules/project_management/controllers/financials/"
        "financials_workspace_controller.py"
    ).read_text(encoding="utf-8")
    host = Path(
        "src/ui_qml/modules/project_management/qml/workspaces/financials/shared/dialogs/"
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
