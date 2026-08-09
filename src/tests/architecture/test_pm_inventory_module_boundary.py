from __future__ import annotations

import ast
from pathlib import Path


PM_ROOT = Path("src/core/modules/project_management")
INVENTORY_ROOT = Path("src/core/modules/inventory_procurement")
PM_PACKAGE = "src.core.modules.project_management"
INVENTORY_PACKAGE = "src.core.modules.inventory_procurement"


def _direct_imports(root: Path, forbidden_package: str) -> list[str]:
    violations: list[str] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported: tuple[str, ...] = ()
            if isinstance(node, ast.ImportFrom) and node.module:
                imported = (node.module,)
            elif isinstance(node, ast.Import):
                imported = tuple(alias.name for alias in node.names)
            for module_name in imported:
                if module_name == forbidden_package or module_name.startswith(
                    f"{forbidden_package}."
                ):
                    violations.append(f"{path}:{node.lineno} imports {module_name}")
    return violations


def test_pm_and_inventory_modules_do_not_import_each_other() -> None:
    violations = [
        *_direct_imports(PM_ROOT, INVENTORY_PACKAGE),
        *_direct_imports(INVENTORY_ROOT, PM_PACKAGE),
    ]

    assert not violations, (
        "PM and Inventory are independent bounded contexts. Put cross-module adapters in "
        "composition/integration infrastructure and exchange typed serialized contracts:\n"
        + "\n".join(violations)
    )

