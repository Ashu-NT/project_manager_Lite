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


def _scoped_policy_statements(
    table_name: str,
    *,
    policy_scope: str,
    predicate: str,
    quote: Callable[[str], str],
) -> tuple[str, ...]:
    table = _validate_identifier(table_name, label="table name")
    prefix = _validate_identifier(f"{table}_{policy_scope}", label="policy name")
    quoted_table = quote(table)

    def policy(command: str) -> str:
        return quote(_validate_identifier(f"{prefix}_{command}", label="policy name"))

    return (
        f"ALTER TABLE {quoted_table} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {quoted_table} FORCE ROW LEVEL SECURITY",
        f"CREATE POLICY {policy('select')} ON {quoted_table} FOR SELECT USING ({predicate})",
        f"CREATE POLICY {policy('insert')} ON {quoted_table} FOR INSERT WITH CHECK ({predicate})",
        (
            f"CREATE POLICY {policy('update')} ON {quoted_table} FOR UPDATE "
            f"USING ({predicate}) WITH CHECK ({predicate})"
        ),
        f"CREATE POLICY {policy('delete')} ON {quoted_table} FOR DELETE USING ({predicate})",
    )


def _scoped_policy_teardown_statements(
    table_name: str,
    *,
    policy_scope: str,
    quote: Callable[[str], str],
) -> tuple[str, ...]:
    table = _validate_identifier(table_name, label="table name")
    prefix = _validate_identifier(f"{table}_{policy_scope}", label="policy name")
    quoted_table = quote(table)
    drops = tuple(
        f"DROP POLICY IF EXISTS {quote(_validate_identifier(f'{prefix}_{command}', label='policy name'))} "
        f"ON {quoted_table}"
        for command in ("delete", "update", "insert", "select")
    )
    return drops + (
        f"ALTER TABLE {quoted_table} NO FORCE ROW LEVEL SECURITY",
        f"ALTER TABLE {quoted_table} DISABLE ROW LEVEL SECURITY",
    )


def build_tenant_organization_rls_enable_statements(
    table_name: str,
    *,
    quote: Callable[[str], str],
) -> tuple[str, ...]:
    predicate = (
        "tenant_id = NULLIF(current_setting('app.tenant_id', true), '') "
        "AND organization_id = NULLIF(current_setting('app.organization_id', true), '')"
    )
    return _scoped_policy_statements(
        table_name,
        policy_scope="tenant_organization",
        predicate=predicate,
        quote=quote,
    )


def build_tenant_organization_rls_disable_statements(
    table_name: str,
    *,
    quote: Callable[[str], str],
) -> tuple[str, ...]:
    return _scoped_policy_teardown_statements(
        table_name,
        policy_scope="tenant_organization",
        quote=quote,
    )


def build_tenant_only_rls_enable_statements(
    table_name: str,
    *,
    quote: Callable[[str], str],
) -> tuple[str, ...]:
    predicate = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')"
    return _scoped_policy_statements(
        table_name,
        policy_scope="tenant",
        predicate=predicate,
        quote=quote,
    )


def build_tenant_only_rls_disable_statements(
    table_name: str,
    *,
    quote: Callable[[str], str],
) -> tuple[str, ...]:
    return _scoped_policy_teardown_statements(
        table_name,
        policy_scope="tenant",
        quote=quote,
    )


def build_nullable_tenant_audit_rls_enable_statements(
    table_name: str,
    *,
    quote: Callable[[str], str],
) -> tuple[str, ...]:
    table = _validate_identifier(table_name, label="table name")
    if table != "audit_entries":
        raise ValueError("The nullable-tenant audit policy is exclusive to audit_entries.")
    quoted_table = quote(table)
    policy = quote("audit_entries_tenant_isolation_or_platform")
    predicate = (
        "tenant_id = NULLIF(current_setting('app.tenant_id', true), '') "
        "OR tenant_id IS NULL"
    )
    return (
        f"ALTER TABLE {quoted_table} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {quoted_table} FORCE ROW LEVEL SECURITY",
        (
            f"CREATE POLICY {policy} ON {quoted_table} "
            f"USING ({predicate}) WITH CHECK ({predicate})"
        ),
    )


def build_nullable_tenant_audit_rls_disable_statements(
    table_name: str,
    *,
    quote: Callable[[str], str],
) -> tuple[str, ...]:
    table = _validate_identifier(table_name, label="table name")
    if table != "audit_entries":
        raise ValueError("The nullable-tenant audit policy is exclusive to audit_entries.")
    quoted_table = quote(table)
    policy = quote("audit_entries_tenant_isolation_or_platform")
    return (
        f"DROP POLICY IF EXISTS {policy} ON {quoted_table}",
        f"ALTER TABLE {quoted_table} NO FORCE ROW LEVEL SECURITY",
        f"ALTER TABLE {quoted_table} DISABLE ROW LEVEL SECURITY",
    )


def _execute_statements(operations: Any, bind: Any, statements: tuple[str, ...]) -> None:
    if bind.dialect.name != "postgresql":
        return
    for statement in statements:
        operations.execute(sa.text(statement))


def enable_tenant_organization_rls(operations: Any, bind: Any, table_name: str) -> None:
    quote = bind.dialect.identifier_preparer.quote
    _execute_statements(
        operations,
        bind,
        build_tenant_organization_rls_enable_statements(table_name, quote=quote),
    )


def disable_tenant_organization_rls(operations: Any, bind: Any, table_name: str) -> None:
    quote = bind.dialect.identifier_preparer.quote
    _execute_statements(
        operations,
        bind,
        build_tenant_organization_rls_disable_statements(table_name, quote=quote),
    )


def enable_tenant_only_rls(operations: Any, bind: Any, table_name: str) -> None:
    quote = bind.dialect.identifier_preparer.quote
    _execute_statements(
        operations,
        bind,
        build_tenant_only_rls_enable_statements(table_name, quote=quote),
    )


def disable_tenant_only_rls(operations: Any, bind: Any, table_name: str) -> None:
    quote = bind.dialect.identifier_preparer.quote
    _execute_statements(
        operations,
        bind,
        build_tenant_only_rls_disable_statements(table_name, quote=quote),
    )


def enable_nullable_tenant_audit_rls(operations: Any, bind: Any, table_name: str) -> None:
    quote = bind.dialect.identifier_preparer.quote
    _execute_statements(
        operations,
        bind,
        build_nullable_tenant_audit_rls_enable_statements(table_name, quote=quote),
    )


def disable_nullable_tenant_audit_rls(operations: Any, bind: Any, table_name: str) -> None:
    quote = bind.dialect.identifier_preparer.quote
    _execute_statements(
        operations,
        bind,
        build_nullable_tenant_audit_rls_disable_statements(table_name, quote=quote),
    )


__all__ = [
    "build_nullable_tenant_audit_rls_disable_statements",
    "build_nullable_tenant_audit_rls_enable_statements",
    "build_tenant_only_rls_disable_statements",
    "build_tenant_only_rls_enable_statements",
    "build_tenant_organization_rls_disable_statements",
    "build_tenant_organization_rls_enable_statements",
    "disable_nullable_tenant_audit_rls",
    "disable_tenant_only_rls",
    "disable_tenant_organization_rls",
    "enable_nullable_tenant_audit_rls",
    "enable_tenant_only_rls",
    "enable_tenant_organization_rls",
]
