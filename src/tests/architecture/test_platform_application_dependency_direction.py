"""Platform application code must not depend on concrete infrastructure."""

from __future__ import annotations

import ast

from src.tests.path_rewrites import REPO_ROOT

APPLICATION_ROOT = REPO_ROOT / "src" / "core" / "platform" / "application"


def test_platform_application_does_not_import_infrastructure() -> None:
    violations: list[str] = []
    for path in APPLICATION_ROOT.rglob("*.py"):
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
                    violations.append(
                        f"{path.relative_to(APPLICATION_ROOT)}:{node.lineno}: {module}"
                    )
    assert not violations, "\n".join(violations)
