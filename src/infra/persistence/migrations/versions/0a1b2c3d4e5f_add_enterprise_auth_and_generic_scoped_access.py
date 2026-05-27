"""add enterprise auth fields and generic scoped access grants

Revision ID: 0a1b2c3d4e5f
Revises: a8b9c0d1e2f3
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa


revision = "0a1b2c3d4e5f"
down_revision = "a8b9c0d1e2f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("identity_provider", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("federated_subject", sa.String(length=256), nullable=True))
        batch.add_column(sa.Column("mfa_secret", sa.String(length=128), nullable=True))
        batch.add_column(
            sa.Column(
                "mfa_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch.add_column(sa.Column("session_timeout_minutes_override", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column(
                "session_revision",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("1"),
            )
        )
        batch.add_column(sa.Column("last_login_auth_method", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("last_login_device_label", sa.String(length=256), nullable=True))
        batch.create_unique_constraint(
            "ux_users_federated_identity",
            ["identity_provider", "federated_subject"],
        )

    op.create_table(
        "scoped_access_grants",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("scope_type", sa.String(length=64), nullable=False),
        sa.Column("scope_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("scope_role", sa.String(length=64), nullable=False, server_default="viewer"),
        sa.Column("permission_codes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope_type", "scope_id", "user_id", name="ux_scoped_access_scope_user"),
    )
    op.create_index("idx_scoped_access_scope", "scoped_access_grants", ["scope_type", "scope_id"])
    op.create_index("idx_scoped_access_user", "scoped_access_grants", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_scoped_access_user", table_name="scoped_access_grants")
    op.drop_index("idx_scoped_access_scope", table_name="scoped_access_grants")
    op.drop_table("scoped_access_grants")

    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("ux_users_federated_identity", type_="unique")
        batch.drop_column("last_login_device_label")
        batch.drop_column("last_login_auth_method")
        batch.drop_column("session_revision")
        batch.drop_column("session_timeout_minutes_override")
        batch.drop_column("mfa_enabled")
        batch.drop_column("mfa_secret")
        batch.drop_column("federated_subject")
        batch.drop_column("identity_provider")
