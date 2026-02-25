"""add auth tables and optimistic locking version columns

Revision ID: 1f0d9a6a3f21
Revises: 7d3fd7fd42bd
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1f0d9a6a3f21"
down_revision = "7d3fd7fd42bd"
branch_labels = None
depends_on = None


def _add_version_column(table_name: str) -> None:
    with op.batch_alter_table(table_name) as batch:
        batch.add_column(
            sa.Column(
                "version",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("1"),
            )
        )


def _drop_version_column(table_name: str) -> None:
    with op.batch_alter_table(table_name) as batch:
        batch.drop_column("version")


def upgrade() -> None:
    _add_version_column("projects")
    _add_version_column("tasks")
    _add_version_column("resources")
    _add_version_column("cost_items")

    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("username", sa.String(length=128), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=True),
        sa.Column("email", sa.String(length=256), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False, unique=True),
        sa.Column("description", sa.String(), nullable=False, server_default=sa.text("''")),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "permissions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False, unique=True),
        sa.Column("description", sa.String(), nullable=False, server_default=sa.text("''")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "user_roles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role_id", name="ux_user_roles_user_role"),
    )
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("role_id", sa.String(), nullable=False),
        sa.Column("permission_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "permission_id", name="ux_role_permissions_role_perm"),
    )

    op.create_index("idx_users_username", "users", ["username"], unique=True)
    op.create_index("idx_roles_name", "roles", ["name"], unique=True)
    op.create_index("idx_permissions_code", "permissions", ["code"], unique=True)
    op.create_index("idx_user_roles_user", "user_roles", ["user_id"], unique=False)
    op.create_index("idx_user_roles_role", "user_roles", ["role_id"], unique=False)
    op.create_index("idx_role_permissions_role", "role_permissions", ["role_id"], unique=False)
    op.create_index("idx_role_permissions_permission", "role_permissions", ["permission_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_role_permissions_permission", table_name="role_permissions")
    op.drop_index("idx_role_permissions_role", table_name="role_permissions")
    op.drop_index("idx_user_roles_role", table_name="user_roles")
    op.drop_index("idx_user_roles_user", table_name="user_roles")
    op.drop_index("idx_permissions_code", table_name="permissions")
    op.drop_index("idx_roles_name", table_name="roles")
    op.drop_index("idx_users_username", table_name="users")

    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")

    _drop_version_column("cost_items")
    _drop_version_column("resources")
    _drop_version_column("tasks")
    _drop_version_column("projects")
