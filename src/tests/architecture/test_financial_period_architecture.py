from __future__ import annotations

import ast
from pathlib import Path

from src.infra.persistence.orm import Base


def test_financial_period_table_has_direct_scope_rls_and_catalog_constraints() -> None:
    table = Base.metadata.tables["financial_periods"]

    assert not table.c.tenant_id.nullable
    assert not table.c.organization_id.nullable
    assert table.info.get("rls_scope") == "tenant_organization"
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("tenant_id", "organization_id", "code") in unique_columns
    assert (
        "tenant_id",
        "organization_id",
        "fiscal_year",
        "period_number",
    ) in unique_columns


def test_platform_period_domain_is_business_module_and_operational_calendar_independent() -> None:
    root = Path("src/core/platform/domain/finance/periods")
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.py"))

    assert "src.core.modules" not in source
    assert "time_management" not in source
    assert "sqlalchemy" not in source.lower()


def test_financial_period_foundation_contains_no_reopen_transition_code() -> None:
    roots = (
        Path("src/core/platform/domain/finance/periods"),
        Path("src/core/platform/application/finance"),
        Path("src/core/platform/api/desktop/finance"),
    )
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for root in roots
        for path in root.rglob("*.py")
    )

    assert "def reopen" not in source
    assert "reopen_period" not in source


def test_financial_period_authority_is_split_without_compatibility_service() -> None:
    root = Path("src/core/platform/application/finance")
    assert not (root / "financial_period_service.py").exists()
    query_source = (root / "queries/financial_period_query.py").read_text(encoding="utf-8")
    command_source = (root / "commands/financial_period_command.py").read_text(encoding="utf-8")
    queries = ast.parse(query_source)
    commands = ast.parse(command_source)
    query_methods = {
        node.name for node in ast.walk(queries)
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    }
    command_methods = {
        node.name for node in ast.walk(commands)
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    }
    assert query_methods == {
        "list_periods", "get_period", "require_open_period_for_date",
        "require_open_period_for_integration",
    }
    assert command_methods == {"create_period", "update_period", "close_period", "lock_period"}
    assert "sqlalchemy" not in query_source
    assert "record_audit_entry" not in query_source
    assert "record_activity" not in query_source
