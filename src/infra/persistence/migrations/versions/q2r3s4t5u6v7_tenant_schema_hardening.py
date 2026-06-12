"""Tenant schema hardening: re-key module entitlements, add tenant_id to scoped access,
add organization_id to project memberships, add last_active_tenant/org to auth_sessions,
and add composite tenant+org indexes on high-volume tables.

Revision ID: q2r3s4t5u6v7
Revises: p1q2r3s4t5u6
Create Date: 2026-06-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "q2r3s4t5u6v7"
down_revision = "p1q2r3s4t5u6"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _table_exists(inspector, table_name):
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _table_exists(inspector, table_name):
        return set()
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def _first_scalar(connection: sa.Connection, sql: str) -> str | None:
    row = connection.execute(sa.text(sql)).first()
    if row is None:
        return None
    value = row[0]
    return str(value) if value else None


def _default_tenant_id(connection: sa.Connection, inspector: sa.Inspector) -> str | None:
    if not _table_exists(inspector, "tenants"):
        return None
    return _first_scalar(connection, "SELECT id FROM tenants WHERE is_active = 1 ORDER BY tenant_code LIMIT 1")


# ---------------------------------------------------------------------------
# Step 11: Re-key organization_module_entitlements to (tenant_id, module_code)
# ---------------------------------------------------------------------------

def _rekey_module_entitlements(connection: sa.Connection, inspector: sa.Inspector, default_tenant_id: str | None) -> None:
    table = "organization_module_entitlements"
    if not _table_exists(inspector, table):
        return

    columns = _column_names(inspector, table)

    if "tenant_id" not in columns:
        op.add_column(table, sa.Column("tenant_id", sa.String(), nullable=True))
        inspector = sa.inspect(connection)

    # Backfill tenant_id from organization_id → organizations.tenant_id
    if "organization_id" in _column_names(inspector, table):
        connection.execute(
            sa.text(
                f"""
                UPDATE {table}
                   SET tenant_id = (
                       SELECT o.tenant_id FROM organizations o
                        WHERE o.id = {table}.organization_id AND o.tenant_id IS NOT NULL
                        LIMIT 1
                   )
                 WHERE tenant_id IS NULL OR tenant_id = ''
                """
            )
        )

    if default_tenant_id:
        connection.execute(
            sa.text(f"UPDATE {table} SET tenant_id = :tid WHERE tenant_id IS NULL OR tenant_id = ''"),
            {"tid": default_tenant_id},
        )

    inspector = sa.inspect(connection)
    if "idx_org_module_entitlements_tenant" not in _index_names(inspector, table):
        op.create_index("idx_org_module_entitlements_tenant", table, ["tenant_id"])


# ---------------------------------------------------------------------------
# Step 12: Add tenant_id to scoped_access_grants
# ---------------------------------------------------------------------------

def _add_tenant_to_scoped_access(connection: sa.Connection, inspector: sa.Inspector, default_tenant_id: str | None) -> None:
    table = "scoped_access_grants"
    if not _table_exists(inspector, table):
        return

    columns = _column_names(inspector, table)
    if "tenant_id" not in columns:
        op.add_column(table, sa.Column("tenant_id", sa.String(), nullable=True))
        inspector = sa.inspect(connection)

    # For scope_type='organization', look up that org's tenant
    connection.execute(
        sa.text(
            f"""
            UPDATE {table}
               SET tenant_id = (
                   SELECT o.tenant_id FROM organizations o
                    WHERE o.id = {table}.scope_id AND o.tenant_id IS NOT NULL
                    LIMIT 1
               )
             WHERE (tenant_id IS NULL OR tenant_id = '')
               AND scope_type = 'organization'
            """
        )
    )

    if default_tenant_id:
        connection.execute(
            sa.text(f"UPDATE {table} SET tenant_id = :tid WHERE tenant_id IS NULL OR tenant_id = ''"),
            {"tid": default_tenant_id},
        )

    inspector = sa.inspect(connection)
    if "idx_scoped_access_tenant" not in _index_names(inspector, table):
        op.create_index("idx_scoped_access_tenant", table, ["tenant_id"])

    # Recreate unique constraint including tenant_id (SQLite batch mode)
    try:
        with op.batch_alter_table(table, recreate="always") as batch_op:
            try:
                batch_op.drop_constraint("ux_scoped_access_scope_user", type_="unique")
            except Exception:
                pass
            batch_op.create_unique_constraint(
                "ux_scoped_access_tenant_scope_user",
                ["tenant_id", "scope_type", "scope_id", "user_id"],
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Step 13: Add organization_id to project_memberships
# ---------------------------------------------------------------------------

def _add_org_to_project_memberships(connection: sa.Connection, inspector: sa.Inspector) -> None:
    table = "project_memberships"
    if not _table_exists(inspector, table):
        return

    columns = _column_names(inspector, table)
    if "organization_id" not in columns:
        op.add_column(table, sa.Column("organization_id", sa.String(), nullable=True))
        inspector = sa.inspect(connection)

    if (
        _table_exists(inspector, "projects")
        and "organization_id" in _column_names(inspector, "projects")
    ):
        connection.execute(
            sa.text(
                f"""
                UPDATE {table}
                   SET organization_id = (
                       SELECT p.organization_id FROM projects p
                        WHERE p.id = {table}.project_id AND p.organization_id IS NOT NULL
                        LIMIT 1
                   )
                 WHERE organization_id IS NULL OR organization_id = ''
                """
            )
        )

    inspector = sa.inspect(connection)
    if "idx_project_memberships_org" not in _index_names(inspector, table):
        op.create_index("idx_project_memberships_org", table, ["organization_id"])


# ---------------------------------------------------------------------------
# Step 14: Add last_active_tenant_id + last_active_organization_id to auth_sessions
# ---------------------------------------------------------------------------

def _add_session_context_columns(connection: sa.Connection, inspector: sa.Inspector) -> None:
    table = "auth_sessions"
    if not _table_exists(inspector, table):
        return

    columns = _column_names(inspector, table)
    if "last_active_tenant_id" not in columns:
        op.add_column(table, sa.Column("last_active_tenant_id", sa.String(), nullable=True))
    if "last_active_organization_id" not in columns:
        op.add_column(table, sa.Column("last_active_organization_id", sa.String(), nullable=True))


# ---------------------------------------------------------------------------
# Step 15: Composite indexes on high-volume tables
# ---------------------------------------------------------------------------

_COMPOSITE_INDEXES = [
    ("projects", "idx_projects_tenant_org", ["tenant_id", "organization_id"]),
    ("resources", "idx_resources_tenant_org", ["tenant_id", "organization_id"]),
    ("time_entries", "idx_time_entries_tenant_org", ["tenant_id", "organization_id"]),
    ("timesheet_periods", "idx_timesheet_periods_tenant_org", ["tenant_id", "organization_id"]),
    ("audit_logs", "idx_audit_logs_tenant_org", ["tenant_id", "organization_id"]),
    ("approval_requests", "idx_approval_requests_tenant_org", ["tenant_id", "organization_id"]),
    ("employees", "idx_employees_tenant_org", ["tenant_id", "organization_id"]),
]


def _add_composite_indexes(connection: sa.Connection, inspector: sa.Inspector) -> None:
    for table, idx_name, columns in _COMPOSITE_INDEXES:
        if not _table_exists(inspector, table):
            continue
        tbl_columns = _column_names(inspector, table)
        if not all(c in tbl_columns for c in columns):
            continue
        inspector = sa.inspect(connection)
        if idx_name not in _index_names(inspector, table):
            op.create_index(idx_name, table, columns)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    default_tenant_id = _default_tenant_id(connection, inspector)

    _rekey_module_entitlements(connection, inspector, default_tenant_id)
    inspector = sa.inspect(connection)
    _add_tenant_to_scoped_access(connection, inspector, default_tenant_id)
    inspector = sa.inspect(connection)
    _add_org_to_project_memberships(connection, inspector)
    inspector = sa.inspect(connection)
    _add_session_context_columns(connection, inspector)
    inspector = sa.inspect(connection)
    _add_composite_indexes(connection, inspector)


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    for table, idx_name, _ in _COMPOSITE_INDEXES:
        if _table_exists(inspector, table) and idx_name in _index_names(inspector, table):
            op.drop_index(idx_name, table_name=table)
        inspector = sa.inspect(connection)

    for col in ("last_active_tenant_id", "last_active_organization_id"):
        if _table_exists(inspector, "auth_sessions") and col in _column_names(inspector, "auth_sessions"):
            with op.batch_alter_table("auth_sessions") as batch_op:
                batch_op.drop_column(col)
        inspector = sa.inspect(connection)

    if _table_exists(inspector, "project_memberships"):
        if "idx_project_memberships_org" in _index_names(inspector, "project_memberships"):
            op.drop_index("idx_project_memberships_org", table_name="project_memberships")
        inspector = sa.inspect(connection)
        if "organization_id" in _column_names(inspector, "project_memberships"):
            with op.batch_alter_table("project_memberships") as batch_op:
                batch_op.drop_column("organization_id")
        inspector = sa.inspect(connection)

    if _table_exists(inspector, "scoped_access_grants"):
        if "idx_scoped_access_tenant" in _index_names(inspector, "scoped_access_grants"):
            op.drop_index("idx_scoped_access_tenant", table_name="scoped_access_grants")
        inspector = sa.inspect(connection)
        if "tenant_id" in _column_names(inspector, "scoped_access_grants"):
            with op.batch_alter_table("scoped_access_grants") as batch_op:
                batch_op.drop_column("tenant_id")
        inspector = sa.inspect(connection)

    if _table_exists(inspector, "organization_module_entitlements"):
        if "idx_org_module_entitlements_tenant" in _index_names(inspector, "organization_module_entitlements"):
            op.drop_index("idx_org_module_entitlements_tenant", table_name="organization_module_entitlements")
        inspector = sa.inspect(connection)
        if "tenant_id" in _column_names(inspector, "organization_module_entitlements"):
            with op.batch_alter_table("organization_module_entitlements") as batch_op:
                batch_op.drop_column("tenant_id")
