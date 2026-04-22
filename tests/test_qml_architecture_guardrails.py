from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
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
