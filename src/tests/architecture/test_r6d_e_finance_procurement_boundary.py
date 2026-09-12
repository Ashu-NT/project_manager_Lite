import ast
from pathlib import Path


PM_FINANCE = Path("src/core/modules/project_management/application/financials")
INNER_SERVICES = (
    PM_FINANCE / "procurement_consumer.py",
    PM_FINANCE / "commitments/commitment_service.py",
)


def test_finance_procurement_projection_does_not_import_source_or_accounting_implementation():
    forbidden = (
        "src.core.modules.inventory_procurement.application",
        "src.core.modules.inventory_procurement.infrastructure",
        "src.core.modules.accounting.application",
        "src.core.modules.accounting.infrastructure",
    )
    for path in PM_FINANCE.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = [
            node.module for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        ]
        imports.extend(
            alias.name for node in ast.walk(tree)
            if isinstance(node, ast.Import) for alias in node.names
        )
        assert not any(
            imported == prefix or imported.startswith(prefix + ".")
            for imported in imports for prefix in forbidden
        ), path


def test_procurement_projection_inner_services_do_not_commit_or_rollback():
    for path in INNER_SERVICES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        forbidden_calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"commit", "rollback"}
        ]
        assert not forbidden_calls, path
