"""Add tenant_id to organizations; create default tenant and backfill.

Revision ID: z0a1b2c3d4e5
Revises: y9z0a1b2c3d4
Create Date: 2026-06-12
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op


revision = "z0a1b2c3d4e5"
down_revision = "y9z0a1b2c3d4"
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


def _ensure_default_tenant(connection: sa.Connection, inspector: sa.Inspector) -> str | None:
    """Return existing default tenant id or create one from the first active organization."""
    if not _table_exists(inspector, "tenants"):
        return None

    # Already have a tenant?
    existing = _first_scalar(connection, "SELECT id FROM tenants ORDER BY tenant_code LIMIT 1")
    if existing:
        return existing

    # Derive name from first active organization
    orgs_columns = _column_names(inspector, "organizations")
    if not _table_exists(inspector, "organizations") or "id" not in orgs_columns:
        tenant_code = "DEFAULT"
        display_name = "Default Tenant"
    else:
        order_col = "created_at" if "created_at" in orgs_columns else "id"
        org_row = connection.execute(
            sa.text(f"SELECT organization_code, display_name FROM organizations ORDER BY {order_col} LIMIT 1")
        ).first()
        if org_row:
            tenant_code = str(org_row[0] or "DEFAULT").strip().upper()
            display_name = str(org_row[1] or "Default Tenant").strip()
        else:
            tenant_code = "DEFAULT"
            display_name = "Default Tenant"

    tenant_id = str(uuid.uuid4())
    connection.execute(
        sa.text(
            "INSERT INTO tenants (id, tenant_code, display_name, is_active, version) "
            "VALUES (:id, :code, :name, 1, 1)"
        ),
        {"id": tenant_id, "code": tenant_code, "name": display_name},
    )
    return tenant_id


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if not _table_exists(inspector, "organizations"):
        return

    # Add tenant_id column
    columns = _column_names(inspector, "organizations")
    if "tenant_id" not in columns:
        op.add_column(
            "organizations",
            sa.Column(
                "tenant_id",
                sa.String(),
                sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
                nullable=True,
            ),
        )
        inspector = sa.inspect(connection)

    # Create index
    if "idx_organizations_tenant" not in _index_names(inspector, "organizations"):
        op.create_index("idx_organizations_tenant", "organizations", ["tenant_id"])

    # Ensure a default tenant exists and backfill all orgs
    inspector = sa.inspect(connection)
    default_tenant_id = _ensure_default_tenant(connection, inspector)
    if default_tenant_id:
        connection.execute(
            sa.text(
                "UPDATE organizations SET tenant_id = :tid "
                "WHERE tenant_id IS NULL OR tenant_id = ''"
            ),
            {"tid": default_tenant_id},
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if not _table_exists(inspector, "organizations"):
        return
    if "idx_organizations_tenant" in _index_names(inspector, "organizations"):
        op.drop_index("idx_organizations_tenant", table_name="organizations")
    inspector = sa.inspect(connection)
    if "tenant_id" in _column_names(inspector, "organizations"):
        with op.batch_alter_table("organizations") as batch_op:
            batch_op.drop_column("tenant_id")
    # Note: does NOT remove the default tenant row — downgrade only reverses the column.
