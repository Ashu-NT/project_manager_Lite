"""harden module entitlement tenant scope

Revision ID: f4g5h6i7j8k9
Revises: e3f4g5h6i7j8
Create Date: 2026-08-02
"""

from alembic import op
import sqlalchemy as sa


revision = "f4g5h6i7j8k9"
down_revision = "e3f4g5h6i7j8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "organization_module_entitlements" not in inspector.get_table_names():
        return
    columns = {
        column["name"]: column
        for column in inspector.get_columns("organization_module_entitlements")
    }
    if "tenant_id" not in columns:
        with op.batch_alter_table("organization_module_entitlements") as batch:
            batch.add_column(sa.Column("tenant_id", sa.String(), nullable=True))

    op.execute(
        sa.text(
            "UPDATE organization_module_entitlements "
            "SET tenant_id = ("
            "SELECT organizations.tenant_id FROM organizations "
            "WHERE organizations.id = organization_module_entitlements.organization_id"
            ") WHERE tenant_id IS NULL OR tenant_id = ''"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM organization_module_entitlements "
            "WHERE tenant_id IS NULL OR tenant_id = ''"
        )
    )
    with op.batch_alter_table("organization_module_entitlements") as batch:
        batch.alter_column("tenant_id", existing_type=sa.String(), nullable=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "organization_module_entitlements" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("organization_module_entitlements")}
    if "tenant_id" in columns:
        with op.batch_alter_table("organization_module_entitlements") as batch:
            batch.alter_column("tenant_id", existing_type=sa.String(), nullable=True)
