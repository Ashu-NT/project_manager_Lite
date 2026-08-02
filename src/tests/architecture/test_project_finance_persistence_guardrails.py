from __future__ import annotations

import pytest

from src.infra.persistence.orm import Base
from src.infra.persistence.migrations.helpers import (
    build_tenant_organization_rls_disable_statements,
    build_tenant_organization_rls_enable_statements,
)


PROJECT_FINANCE_TABLE_PREFIX = "project_finance_"
PROJECT_FINANCE_RLS_SCOPE = "tenant_organization"


def _quote(identifier: str) -> str:
    return f'"{identifier}"'


def test_project_finance_rls_template_is_forced_and_default_deny() -> None:
    statements = build_tenant_organization_rls_enable_statements(
        "project_finance_cost_entries",
        quote=_quote,
    )
    sql = " ".join(statements)

    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "FORCE ROW LEVEL SECURITY" in sql
    assert sql.count("current_setting('app.tenant_id', true)") == 2
    assert sql.count("current_setting('app.organization_id', true)") == 2
    assert "USING" in sql and "WITH CHECK" in sql


def test_project_finance_rls_template_has_reversible_policy_teardown() -> None:
    statements = build_tenant_organization_rls_disable_statements(
        "project_finance_cost_entries",
        quote=_quote,
    )

    assert statements[0].startswith("DROP POLICY IF EXISTS")
    assert "NO FORCE ROW LEVEL SECURITY" in statements[1]
    assert "DISABLE ROW LEVEL SECURITY" in statements[2]


def test_project_finance_rls_template_rejects_unsafe_identifiers() -> None:
    with pytest.raises(ValueError, match="Invalid PostgreSQL table name"):
        build_tenant_organization_rls_enable_statements(
            "cost_entries; DROP TABLE projects",
            quote=_quote,
        )


def test_every_project_finance_table_has_direct_scope_and_rls_marker() -> None:
    finance_tables = {
        name: table
        for name, table in Base.metadata.tables.items()
        if name.startswith(PROJECT_FINANCE_TABLE_PREFIX)
    }

    for table_name, table in finance_tables.items():
        assert "tenant_id" in table.c, f"{table_name} must own tenant_id directly"
        assert "organization_id" in table.c, (
            f"{table_name} must own organization_id directly"
        )
        assert not table.c.tenant_id.nullable, f"{table_name}.tenant_id must be non-null"
        assert not table.c.organization_id.nullable, (
            f"{table_name}.organization_id must be non-null"
        )
        assert table.info.get("rls_scope") == PROJECT_FINANCE_RLS_SCOPE, (
            f"{table_name} must declare info['rls_scope']='tenant_organization'"
        )
