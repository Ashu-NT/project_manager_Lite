"""Finance and its dashboard consumers must not depend outward on adapters."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PM = Path(__file__).resolve().parents[2] / "core/modules/project_management"


@pytest.mark.parametrize("area", ["application/financials", "application/dashboard", "domain/financials"])
def test_finance_authority_dependencies_point_inward(area: str) -> None:
    violations = []
    for path in (PM / area).rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
            if isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            elif isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            else:
                continue
            for module in modules:
                forbidden = (".infrastructure", "src.infra", "src.ui_qml", ".api.")
                if area.startswith("domain/"):
                    forbidden += (".application",)
                if any(part in module for part in forbidden):
                    violations.append(f"{path.relative_to(PM)}:{node.lineno}: {module}")
    assert not violations, "\n".join(violations)


def test_reporting_model_compatibility_paths_are_retired() -> None:
    reporting = PM / "infrastructure/reporting"
    assert not (reporting / "models.py").exists()
    assert "application." not in (reporting / "models/__init__.py").read_text()
    assert "application." not in (reporting / "__init__.py").read_text()
