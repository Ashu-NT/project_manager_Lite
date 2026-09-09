from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

from src.core.modules.project_management.application.financials.governance import (
    FinanceGovernanceCommandBoundary,
    FinanceGovernedServicePort,
)


PM_ROOT = Path("src/core/modules/project_management")
DESKTOP_API = PM_ROOT / "api/desktop/financials/api.py"
BOUNDARY = (
    PM_ROOT
    / "application/financials/governance/command_boundary.py"
)
RUNTIME_RESOLVER = PM_ROOT / "api/desktop_runtime/service_resolver.py"
PROJECT_REGISTRY = Path("src/infra/composition/project_registry.py")
FINANCIAL_DIALOG_HOST = Path(
    "src/ui_qml/modules/project_management/qml/workspaces/financials/dialogs/"
    "FinancialsDialogHost.qml"
)


def _python_identifiers(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    identifiers: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            identifiers.add(node.id)
        elif isinstance(node, ast.Attribute):
            identifiers.add(node.attr)
    return identifiers


def test_finance_governance_boundary_has_one_transaction_contract() -> None:
    source = BOUNDARY.read_text(encoding="utf-8")
    assert source.count("uow.commit()") == 1
    assert "_project_id" not in source

    for family in (
        "budget",
        "forecast_version",
        "forecast_generation",
        "financial_change",
        "planned_cost",
        "commitment",
        "cost_entry",
        "financial_setup",
        "rate_card",
        "billing_profile",
        "billing_preparation",
    ):
        signature = inspect.signature(
            getattr(FinanceGovernanceCommandBoundary, family)
        )
        assert tuple(signature.parameters) == ("self", "command")

    assert not hasattr(FinanceGovernedServicePort, "_project_id")


def test_r6c_desktop_runtime_has_no_superseded_write_service_dependencies() -> None:
    source = RUNTIME_RESOLVER.read_text(encoding="utf-8")
    assert "ForecastVersionService" not in source
    assert "FinancialChangeService" not in source
    assert "forecast_version_service" not in source
    assert "financial_change_service" not in source


def test_r6c_desktop_commands_are_typed_at_the_desktop_boundary() -> None:
    tree = ast.parse(DESKTOP_API.read_text(encoding="utf-8"), filename=str(DESKTOP_API))
    governed_methods: list[ast.FunctionDef] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if any(
            isinstance(child, ast.Attribute)
            and child.attr == "_require_finance_governance_commands"
            for child in ast.walk(node)
        ):
            governed_methods.append(node)

    assert governed_methods
    for method in governed_methods:
        command = next(
            (argument for argument in method.args.args if argument.arg == "command"),
            None,
        )
        assert command is not None, method.name
        assert command.annotation is not None, method.name
        assert ast.unparse(command.annotation).startswith("Financial"), method.name


def test_r6c_approval_participants_have_one_apply_and_reject_registration() -> None:
    source = PROJECT_REGISTRY.read_text(encoding="utf-8")
    for process in ("budget.approve", "forecast.approve", "financial_change.apply"):
        assert len(
            re.findall(
                rf'register_apply_handler\(\s*"{re.escape(process)}"',
                source,
            )
        ) == 1
        assert len(
            re.findall(
                rf'register_reject_handler\(\s*"{re.escape(process)}"',
                source,
            )
        ) == 1


def test_r6c_has_no_retired_process_local_finance_signals() -> None:
    retired = {
        "budgets_changed",
        "forecasts_changed",
        "financial_changes_changed",
        "financial_setup_changed",
    }
    identifiers: set[str] = set()
    for path in Path("src").rglob("*.py"):
        if "tests" not in path.parts:
            identifiers.update(_python_identifiers(path))
    assert retired.isdisjoint(identifiers)


def test_r6c_has_no_financial_change_submission_uow_or_direct_task_orm_path() -> None:
    retired_names = {
        "financial_change_submission_unit_of_work.py",
        "financial_change_submission_uow.py",
    }
    assert not any(path.name in retired_names for path in PM_ROOT.rglob("*.py"))

    change_paths = (
        PM_ROOT / "application/financials/financial_changes/service.py",
        PM_ROOT / "infrastructure/approval/financial_change_apply_participant.py",
    )
    for path in change_paths:
        assert "TaskORM" not in path.read_text(encoding="utf-8")


def test_r6c_qml_has_no_retired_cost_code_dialog_alias() -> None:
    assert (
        "openCreateCostCodeDialog"
        not in FINANCIAL_DIALOG_HOST.read_text(encoding="utf-8")
    )
