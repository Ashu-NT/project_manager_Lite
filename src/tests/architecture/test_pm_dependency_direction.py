"""Keep PM business layers independent of concrete adapters."""

import ast
from pathlib import Path

import pytest

PM_ROOT = Path(__file__).resolve().parents[2] / "core/modules/project_management"


@pytest.mark.parametrize("layer", ("application", "domain", "contracts"))
def test_pm_business_layers_do_not_import_infrastructure(layer: str) -> None:
    violations: list[str] = []
    for path in (PM_ROOT / layer).rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                modules = (node.module or "",)
            elif isinstance(node, ast.Import):
                modules = tuple(alias.name for alias in node.names)
            else:
                continue
            for module in modules:
                if ".infrastructure" in module or module.startswith("src.infra"):
                    violations.append(f"{path.relative_to(PM_ROOT)}:{node.lineno}: {module}")
    assert not violations, "\n".join(violations)


@pytest.mark.parametrize("package", ("contracts/ports", "gateway"))
def test_pm_boundary_contracts_do_not_import_other_module_implementations(package: str) -> None:
    violations: list[str] = []
    for path in (PM_ROOT / package).rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                modules = (node.module or "",)
            elif isinstance(node, ast.Import):
                modules = tuple(alias.name for alias in node.names)
            else:
                continue
            for module in modules:
                other_business_module = module.startswith("src.core.modules.") and not (
                    module == "src.core.modules.project_management"
                    or module.startswith("src.core.modules.project_management.")
                )
                concrete_adapter = ".infrastructure" in module or module.startswith("src.infra")
                if other_business_module or concrete_adapter:
                    violations.append(f"{path.relative_to(PM_ROOT)}:{node.lineno}: {module}")
    assert not violations, "\n".join(violations)


def test_pm_gateways_do_not_depend_on_pm_application_or_desktop() -> None:
    violations: list[str] = []
    for path in (PM_ROOT / "gateway").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                modules = (node.module or "",)
            elif isinstance(node, ast.Import):
                modules = tuple(alias.name for alias in node.names)
            else:
                continue
            for module in modules:
                if module.startswith((
                    "src.core.modules.project_management.application",
                    "src.core.modules.project_management.api",
                    "src.ui_qml",
                )):
                    violations.append(f"{path.relative_to(PM_ROOT)}:{node.lineno}: {module}")
    assert not violations, "\n".join(violations)
