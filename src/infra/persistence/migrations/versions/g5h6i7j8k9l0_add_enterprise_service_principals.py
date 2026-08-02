"""add enterprise service principals

Revision ID: g5h6i7j8k9l0
Revises: f4g5h6i7j8k9
Create Date: 2026-08-02
"""

from alembic import op
import sqlalchemy as sa


revision = "g5h6i7j8k9l0"
down_revision = "f4g5h6i7j8k9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "users" in tables:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "account_type" not in user_columns:
            with op.batch_alter_table("users") as batch:
                batch.add_column(
                    sa.Column(
                        "account_type",
                        sa.String(length=32),
                        nullable=False,
                        server_default="human",
                    )
                )
                batch.create_check_constraint(
                    "ck_users_account_type",
                    "account_type IN ('human', 'service')",
                )

    if "service_principals" not in tables:
        op.create_table(
            "service_principals",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("tenant_id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
            sa.Column("created_by_user_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["created_by_user_id"],
                ["users.id"],
                ondelete="SET NULL",
            ),
            sa.UniqueConstraint("user_id", name="ux_service_principals_user"),
            sa.UniqueConstraint(
                "tenant_id",
                "name",
                name="ux_service_principals_tenant_name",
            ),
        )
        op.create_index(
            "idx_service_principals_tenant",
            "service_principals",
            ["tenant_id"],
        )
        op.create_index(
            "idx_service_principals_org",
            "service_principals",
            ["organization_id"],
        )

    if "service_principal_api_keys" not in tables:
        op.create_table(
            "service_principal_api_keys",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("tenant_id", sa.String(), nullable=False),
            sa.Column("service_principal_id", sa.String(), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("key_prefix", sa.String(length=32), nullable=False),
            sa.Column("secret_hash", sa.String(length=64), nullable=False),
            sa.Column("permission_scopes_json", sa.Text(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("created_by_user_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["service_principal_id"],
                ["service_principals.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["created_by_user_id"],
                ["users.id"],
                ondelete="SET NULL",
            ),
            sa.UniqueConstraint("key_prefix", name="ux_service_api_keys_prefix"),
        )
        op.create_index(
            "idx_service_api_keys_tenant",
            "service_principal_api_keys",
            ["tenant_id"],
        )
        op.create_index(
            "idx_service_api_keys_principal",
            "service_principal_api_keys",
            ["service_principal_id"],
        )
        op.create_index(
            "idx_service_api_keys_expiry",
            "service_principal_api_keys",
            ["expires_at"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "service_principal_api_keys" in tables:
        op.drop_table("service_principal_api_keys")
    if "service_principals" in tables:
        op.drop_table("service_principals")
    if "users" in tables:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "account_type" in user_columns:
            with op.batch_alter_table("users") as batch:
                batch.drop_constraint("ck_users_account_type", type_="check")
                batch.drop_column("account_type")
