from __future__ import annotations

import ast
from pathlib import Path

from src.tests.path_rewrites import REPO_ROOT

ROOT = REPO_ROOT
SRC_ROOT = ROOT / "src"
UI_QML_ROOT = SRC_ROOT / "ui_qml"
CORE_ROOT = SRC_ROOT / "core"


def _python_files(root: Path):
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _imports_from(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    return imports


def test_core_does_not_import_qml_or_widget_ui() -> None:
    violations: list[tuple[str, str]] = []

    for path in _python_files(CORE_ROOT):
        for imported in _imports_from(path):
            if imported == "src.ui_qml" or imported.startswith("src.ui_qml."):
                violations.append((str(path.relative_to(ROOT)), imported))
            if imported == "src.ui" or imported.startswith("src.ui."):
                violations.append((str(path.relative_to(ROOT)), imported))

    assert not violations, f"Core imports UI layers: {violations}"


def test_qml_python_layer_does_not_import_legacy_widget_ui_or_infrastructure() -> None:
    violations: list[tuple[str, str]] = []

    for path in _python_files(UI_QML_ROOT):
        for imported in _imports_from(path):
            if imported == "src.ui" or imported.startswith("src.ui."):
                violations.append((str(path.relative_to(ROOT)), imported))
            if ".infrastructure." in imported or imported.endswith(".infrastructure"):
                violations.append((str(path.relative_to(ROOT)), imported))
            if ".repositories" in imported or imported.endswith(".repositories"):
                violations.append((str(path.relative_to(ROOT)), imported))
            if ".contracts.reads" in imported or ".persistence.reads" in imported:
                violations.append((str(path.relative_to(ROOT)), imported))

    assert not violations, f"QML Python layer imports forbidden layers: {violations}"


def test_qml_python_layer_does_not_use_qt_widgets() -> None:
    violations: list[tuple[str, str]] = []

    for path in _python_files(UI_QML_ROOT):
        for imported in _imports_from(path):
            if imported == "PySide6.QtWidgets" or imported.startswith("PySide6.QtWidgets."):
                violations.append((str(path.relative_to(ROOT)), imported))

    assert not violations, f"QML Python layer imports QtWidgets: {violations}"


def test_module_desktop_apis_do_not_import_qml() -> None:
    violations: list[tuple[str, str]] = []

    for desktop_api_root in CORE_ROOT.glob("modules/*/api/desktop"):
        for path in _python_files(desktop_api_root):
            for imported in _imports_from(path):
                if imported == "src.ui_qml" or imported.startswith("src.ui_qml."):
                    violations.append((str(path.relative_to(ROOT)), imported))

    assert not violations, f"Module desktop APIs import QML: {violations}"


def test_qml_files_do_not_reference_repositories_or_orm() -> None:
    forbidden_snippets = (
        "repository",
        "repositories",
        "sqlalchemy",
        "sessionlocal",
        "infrastructure.persistence",
    )
    violations: list[tuple[str, str]] = []

    for path in UI_QML_ROOT.rglob("*.qml"):
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for snippet in forbidden_snippets:
            if snippet in text:
                violations.append((str(path.relative_to(ROOT)), snippet))

    assert not violations, f"QML files reference persistence concerns: {violations}"


def test_qml_files_do_not_use_parent_relative_imports() -> None:
    violations: list[str] = []

    for path in UI_QML_ROOT.rglob("*.qml"):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="ignore").splitlines(),
            start=1,
        ):
            stripped = line.strip()
            if stripped.startswith('import "') and "../" in stripped:
                violations.append(f"{path.relative_to(ROOT)}:{lineno}")

    assert not violations, f"QML files use parent relative imports: {violations}"


def test_qml_workspace_controller_properties_use_typed_controller_types() -> None:
    violations: list[str] = []

    for path in UI_QML_ROOT.rglob("*.qml"):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="ignore").splitlines(),
            start=1,
        ):
            stripped = line.strip()
            if not stripped.startswith("property QtObject "):
                continue
            if "controller" in stripped.lower():
                violations.append(f"{path.relative_to(ROOT)}:{lineno}:{stripped}")

    assert not violations, f"QML controller properties still use generic QtObject: {violations}"


def test_project_management_qml_does_not_use_generic_pm_catalog_var_binding() -> None:
    violations: list[str] = []

    for path in (UI_QML_ROOT / "modules" / "project_management").rglob("*.qml"):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="ignore").splitlines(),
            start=1,
        ):
            stripped = line.strip()
            if stripped.startswith("property var pmCatalog"):
                violations.append(f"{path.relative_to(ROOT)}:{lineno}:{stripped}")

    assert not violations, f"Project management QML still uses generic pmCatalog bindings: {violations}"


def test_project_management_qml_uses_shared_buttons_for_workspace_actions() -> None:
    pm_qml_root = UI_QML_ROOT / "modules" / "project_management" / "qml"
    violations: list[str] = []

    for path in pm_qml_root.rglob("*.qml"):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="ignore").splitlines(),
            start=1,
        ):
            stripped = line.strip()
            if stripped.startswith("Button {"):
                violations.append(f"{path.relative_to(ROOT)}:{lineno}:{stripped}")

    assert not violations, f"Project management QML still uses raw Button controls: {violations}"


def test_project_management_qml_has_no_noop_sort_handlers() -> None:
    pm_qml_root = UI_QML_ROOT / "modules" / "project_management" / "qml"
    violations: list[str] = []

    forbidden_snippets = (
        "onSortRequested: function(key) {}",
        "onSortRequested: function(key) { /* client-side sort future */ }",
    )

    for path in pm_qml_root.rglob("*.qml"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for snippet in forbidden_snippets:
            if snippet in text:
                violations.append(f"{path.relative_to(ROOT)}:{snippet}")

    assert not violations, f"Project management QML still has dead sort handlers: {violations}"


def test_project_management_qml_has_no_noop_export_handlers() -> None:
    pm_qml_root = UI_QML_ROOT / "modules" / "project_management" / "qml"
    violations: list[str] = []

    forbidden_snippets = (
        "onExportRequested: {}",
        "onExportRequested: { /* future */ }",
    )

    for path in pm_qml_root.rglob("*.qml"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for snippet in forbidden_snippets:
            if snippet in text:
                violations.append(f"{path.relative_to(ROOT)}:{snippet}")

    assert not violations, f"Project management QML still has dead export handlers: {violations}"


def test_project_management_controllers_have_no_pass_export_methods() -> None:
    controller_root = UI_QML_ROOT / "modules" / "project_management" / "controllers"
    violations: list[str] = []

    for path in controller_root.rglob("*.py"):
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for index, line in enumerate(lines[:-1]):
            stripped = line.strip()
            if stripped.startswith("def export") and lines[index + 1].strip() == "pass":
                violations.append(f"{path.relative_to(ROOT)}:{index + 1}")

    assert not violations, f"Project management controllers still have dead export methods: {violations}"


def test_project_management_qml_has_no_raw_standard_button_dialogs() -> None:
    pm_qml_root = UI_QML_ROOT / "modules" / "project_management" / "qml"
    violations: list[str] = []

    for path in pm_qml_root.rglob("*.qml"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "standardButtons:" in text:
            violations.append(str(path.relative_to(ROOT)))

    assert not violations, f"Project management QML still uses raw standardButtons dialogs: {violations}"
