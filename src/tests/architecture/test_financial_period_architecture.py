from __future__ import annotations

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
    root = Path("src/core/platform/finance/periods")
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.py"))

    assert "src.core.modules" not in source
    assert "time_management" not in source
    assert "sqlalchemy" not in source.lower()


def test_financial_period_foundation_contains_no_reopen_transition_code() -> None:
    roots = (
        Path("src/core/platform/finance/periods"),
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
