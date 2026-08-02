from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import Numeric

from src.infra.persistence.db.financial_numeric import (
    FinancialNumericKind,
    financial_numeric,
    financial_numeric_info,
    precision_for,
)
from src.infra.persistence.orm import Base
from src.infra.persistence.migrations.helpers import (
    build_tenant_organization_rls_disable_statements,
    build_tenant_organization_rls_enable_statements,
)


PROJECT_FINANCE_TABLE_PREFIX = "project_finance_"
PROJECT_FINANCE_RLS_SCOPE = "tenant_organization"
FINANCE_PRIMITIVES_ROOT = Path("src/core/platform/finance")
PROJECT_FINANCE_TRANSITION_MARKER = "PF-B1-CURRENCY-DUAL-WRITE"
PROJECT_FINANCE_TRANSITION_FILES = (
    Path(
        "src/core/modules/project_management/application/financials/"
        "configuration_service.py"
    ),
    Path(
        "src/core/modules/project_management/application/projects/commands/"
        "lifecycle.py"
    ),
)
PROJECT_FINANCE_PLAN = Path(
    "docs/pm_modernization/project_finance_existing_state_and_implementation_plan.md"
)


def _quote(identifier: str) -> str:
    return f'"{identifier}"'


def test_platform_finance_primitives_do_not_import_business_modules_or_sql_float() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in FINANCE_PRIMITIVES_ROOT.rglob("*.py")
    )

    assert "src.core.modules" not in source
    assert "sqlalchemy" not in source.lower()
    assert "Float(" not in source


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


@pytest.mark.parametrize("kind", list(FinancialNumericKind))
def test_financial_numeric_factory_is_decimal_and_matches_domain_precision(
    kind: FinancialNumericKind,
) -> None:
    sql_type = financial_numeric(kind)
    convention = precision_for(kind)

    assert isinstance(sql_type, Numeric)
    assert sql_type.asdecimal is True
    assert sql_type.precision == convention.precision
    assert sql_type.scale == convention.scale
    assert financial_numeric_info(kind) == {"financial_numeric": kind.value}


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
        for column in table.c:
            if not isinstance(column.type, Numeric):
                continue
            kind_value = column.info.get("financial_numeric")
            assert kind_value, (
                f"{table_name}.{column.name} must declare info['financial_numeric']"
            )
            convention = precision_for(kind_value)
            assert column.type.asdecimal is True
            assert column.type.precision == convention.precision
            assert column.type.scale == convention.scale


def test_phase_b1_currency_transition_is_marked_once_per_path_and_registered() -> None:
    source_occurrences = sum(
        path.read_text(encoding="utf-8").count(PROJECT_FINANCE_TRANSITION_MARKER)
        for path in PROJECT_FINANCE_TRANSITION_FILES
    )
    plan = PROJECT_FINANCE_PLAN.read_text(encoding="utf-8")

    assert source_occurrences == 2
    assert PROJECT_FINANCE_TRANSITION_MARKER in plan
    assert "Profile-to-Project and Project-to-profile currency synchronization" in plan
