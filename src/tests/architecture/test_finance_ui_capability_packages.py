from __future__ import annotations

import ast

import pytest

from src.tests.path_rewrites import REPO_ROOT

UI = REPO_ROOT / "src/ui_qml/modules/project_management"
QML = UI / "qml/workspaces/financials"


@pytest.mark.parametrize(
    "capability",
    ["budgets", "forecasts", "financial_changes", "invoicing", "rate_cards", "cost", "governance"],
)
def test_finance_write_capability_has_colocated_adapters(capability: str) -> None:
    assert (UI / "presenters/financials" / capability / "commands.py").is_file()
    assert (UI / "controllers/financials" / capability / "mutation_mixin.py").is_file()
    assert (QML / capability / "dialogs/qmldir").is_file()


def test_finance_qml_registrations_match_capability_paths() -> None:
    for directory in QML.rglob("qmldir"):
        lines = directory.read_text(encoding="utf-8").splitlines()
        module = ".".join(directory.parent.relative_to(UI / "qml").parts)
        assert lines[0] == f"module {module}"
        registered = set()
        for line in lines[1:]:
            name, version, filename = line.split()
            assert version == "1.0"
            assert filename == name + ".qml"
            assert (directory.parent / filename).is_file()
            registered.add(filename)
        assert registered == {p.name for p in directory.parent.glob("*.qml")}


def test_finance_retired_flat_paths_have_no_compatibility_modules() -> None:
    assert not (QML / "FinancialsColumnConfig.js").exists()
    for folder in ("sections", "dialogs", "panels"):
        assert not (QML / folder).exists()
    for layer in ("controllers", "presenters"):
        root = UI / layer / "financials"
        expected = "financials_workspace_controller.py" if layer == "controllers" else "financials_workspace_presenter.py"
        assert {p.name for p in root.glob("*.py")} == {"__init__.py", expected}
        assert not list(root.rglob("command_handler.py"))


def test_shared_mutation_boundary_does_not_own_capability_commands() -> None:
    source = (UI / "controllers/financials/shared/financials_mutation_mixin.py").read_text(encoding="utf-8")
    methods = {node.name for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef)}
    assert methods == {"_run_finance_mutation"}
