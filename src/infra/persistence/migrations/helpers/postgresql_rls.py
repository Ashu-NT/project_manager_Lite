from __future__ import annotations

import re
from typing import Any, Callable

import sqlalchemy as sa


_SQL_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(value: str, *, label: str) -> str:
    normalized = str(value or "").strip()
    if not _SQL_IDENTIFIER.fullmatch(normalized):
        raise ValueError(f"Invalid PostgreSQL {label}: {value!r}")
    return normalized


def build_tenant_organization_rls_enable_statements(
    table_name: str,
    *,
    quote: Callable[[str], str],
) -> tuple[str, str, str]:
    """Build a forced, default-deny policy for directly scoped business data."""
    table = _validate_identifier(table_name, label="table name")
    policy_name = _validate_identifier(
        f"{table}_tenant_organization_isolation",
        label="policy name",
    )
    quoted_table = quote(table)
    quoted_policy = quote(policy_name)
    predicate = (
        "tenant_id = NULLIF(current_setting('app.tenant_id', true), '') "
        "AND organization_id = NULLIF(current_setting('app.organization_id', true), '')"
    )
    return (
        f"ALTER TABLE {quoted_table} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {quoted_table} FORCE ROW LEVEL SECURITY",
        (
            f"CREATE POLICY {quoted_policy} ON {quoted_table} "
            f"USING ({predicate}) WITH CHECK ({predicate})"
        ),
    )


def build_tenant_organization_rls_disable_statements(
    table_name: str,
    *,
    quote: Callable[[str], str],
) -> tuple[str, str, str]:
    table = _validate_identifier(table_name, label="table name")
    policy_name = _validate_identifier(
        f"{table}_tenant_organization_isolation",
        label="policy name",
    )
    quoted_table = quote(table)
    quoted_policy = quote(policy_name)
    return (
        f"DROP POLICY IF EXISTS {quoted_policy} ON {quoted_table}",
        f"ALTER TABLE {quoted_table} NO FORCE ROW LEVEL SECURITY",
        f"ALTER TABLE {quoted_table} DISABLE ROW LEVEL SECURITY",
    )


def enable_tenant_organization_rls(
    operations: Any,
    bind: Any,
    table_name: str,
) -> None:
    if bind.dialect.name != "postgresql":
        return
    quote = bind.dialect.identifier_preparer.quote
    for statement in build_tenant_organization_rls_enable_statements(
        table_name,
        quote=quote,
    ):
        operations.execute(sa.text(statement))


def disable_tenant_organization_rls(
    operations: Any,
    bind: Any,
    table_name: str,
) -> None:
    if bind.dialect.name != "postgresql":
        return
    quote = bind.dialect.identifier_preparer.quote
    for statement in build_tenant_organization_rls_disable_statements(
        table_name,
        quote=quote,
    ):
        operations.execute(sa.text(statement))


__all__ = [
    "build_tenant_organization_rls_disable_statements",
    "build_tenant_organization_rls_enable_statements",
    "disable_tenant_organization_rls",
    "enable_tenant_organization_rls",
]
