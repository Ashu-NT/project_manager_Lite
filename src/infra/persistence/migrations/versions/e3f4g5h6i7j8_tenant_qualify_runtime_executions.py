"""tenant qualify runtime executions

Revision ID: e3f4g5h6i7j8
Revises: d2e3f4g5h6i7
Create Date: 2026-08-02
"""

from alembic import op
import sqlalchemy as sa


revision = "e3f4g5h6i7j8"
down_revision = "d2e3f4g5h6i7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "runtime_executions" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("runtime_executions")}
    with op.batch_alter_table("runtime_executions") as batch:
        if "tenant_id" not in columns:
            batch.add_column(sa.Column("tenant_id", sa.String(), nullable=True))
        if "organization_id" not in columns:
            batch.add_column(sa.Column("organization_id", sa.String(), nullable=True))
        if "authorization_context_id" not in columns:
            batch.add_column(
                sa.Column("authorization_context_id", sa.String(), nullable=True)
            )

    # Runtime history is operational metadata. Ownership cannot be inferred safely.
    op.execute(sa.text("DELETE FROM runtime_executions"))
    with op.batch_alter_table("runtime_executions") as batch:
        batch.alter_column("tenant_id", existing_type=sa.String(), nullable=False)
        batch.alter_column("organization_id", existing_type=sa.String(), nullable=False)
        batch.create_foreign_key(
            "fk_runtime_executions_tenant_id",
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch.create_foreign_key(
            "fk_runtime_executions_organization_id",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch.create_index(
            "idx_runtime_executions_tenant_org_started",
            ["tenant_id", "organization_id", "started_at"],
            unique=False,
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "runtime_executions" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("runtime_executions")}
    with op.batch_alter_table("runtime_executions") as batch:
        batch.drop_index("idx_runtime_executions_tenant_org_started")
        batch.drop_constraint(
            "fk_runtime_executions_organization_id",
            type_="foreignkey",
        )
        batch.drop_constraint("fk_runtime_executions_tenant_id", type_="foreignkey")
        for column_name in (
            "authorization_context_id",
            "organization_id",
            "tenant_id",
        ):
            if column_name in columns:
                batch.drop_column(column_name)
