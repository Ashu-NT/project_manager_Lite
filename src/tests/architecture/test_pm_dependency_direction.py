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
