"""Add canonical tenant-aware role metadata and role bindings.

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "b5c6d7e8f9a0"
down_revision = "a4b5c6d7e8f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("roles") as batch_op:
        batch_op.add_column(sa.Column("tenant_id", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column("display_name", sa.String(length=256), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column(
                "allowed_scope_type",
                sa.String(length=64),
                nullable=False,
                server_default="tenant",
            )
        )
        batch_op.add_column(
            sa.Column(
                "is_assignable",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default="active",
            )
        )
        batch_op.add_column(
            sa.Column(
                "policy_version",
                sa.Integer(),
                nullable=False,
                server_default="1",
            )
        )
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )
        batch_op.create_foreign_key(
            "fk_roles_tenant_id_tenants",
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="CASCADE",
        )

    op.execute("UPDATE roles SET display_name = replace(name, '_', ' ')")
    op.execute(
        "UPDATE roles SET allowed_scope_type = 'platform', is_assignable = false "
        "WHERE name IN ('admin', 'support_admin')"
    )
    op.execute(
        "UPDATE roles SET allowed_scope_type = 'organization' "
        "WHERE name = 'org_admin'"
    )
    op.create_index("idx_roles_tenant", "roles", ["tenant_id"])

    op.create_table(
        "role_bindings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("principal_type", sa.String(length=32), nullable=False),
        sa.Column("principal_id", sa.String(), nullable=False),
        sa.Column("role_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("actual_scope_type", sa.String(length=64), nullable=False),
        sa.Column("actual_scope_id", sa.String(), nullable=True),
        sa.Column("assigned_by", sa.String(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint(
            "principal_type = 'user'",
            name="ck_role_bindings_principal_type",
        ),
        sa.CheckConstraint(
            "("
            "actual_scope_type = 'platform' AND tenant_id IS NULL "
            "AND actual_scope_id IS NULL"
            ") OR ("
            "actual_scope_type = 'tenant' AND tenant_id IS NOT NULL "
            "AND actual_scope_id IS NULL"
            ") OR ("
            "actual_scope_type NOT IN ('platform', 'tenant') "
            "AND tenant_id IS NOT NULL AND actual_scope_id IS NOT NULL"
            ")",
            name="ck_role_bindings_scope_shape",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_role_bindings_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by"],
            ["users.id"],
            name="fk_role_bindings_assigned_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["principal_id"],
            ["users.id"],
            name="fk_role_bindings_principal_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name="fk_role_bindings_role_id_roles",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_role_bindings_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_role_bindings_principal",
        "role_bindings",
        ["principal_type", "principal_id"],
    )
    op.create_index("idx_role_bindings_role", "role_bindings", ["role_id"])
    op.create_index("idx_role_bindings_tenant", "role_bindings", ["tenant_id"])
    op.create_index(
        "ux_role_bindings_active_platform",
        "role_bindings",
        ["principal_type", "principal_id", "role_id"],
        unique=True,
        sqlite_where=sa.text(
            "revoked_at IS NULL AND actual_scope_type = 'platform'"
        ),
        postgresql_where=sa.text(
            "revoked_at IS NULL AND actual_scope_type = 'platform'"
        ),
    )
    op.create_index(
        "ux_role_bindings_active_tenant",
        "role_bindings",
        ["principal_type", "principal_id", "role_id", "tenant_id"],
        unique=True,
        sqlite_where=sa.text(
            "revoked_at IS NULL AND actual_scope_type = 'tenant'"
        ),
        postgresql_where=sa.text(
            "revoked_at IS NULL AND actual_scope_type = 'tenant'"
        ),
    )
    op.create_index(
        "ux_role_bindings_active_resource",
        "role_bindings",
        [
            "principal_type",
            "principal_id",
            "role_id",
            "tenant_id",
            "actual_scope_type",
            "actual_scope_id",
        ],
        unique=True,
        sqlite_where=sa.text(
            "revoked_at IS NULL "
            "AND actual_scope_type NOT IN ('platform', 'tenant')"
        ),
        postgresql_where=sa.text(
            "revoked_at IS NULL "
            "AND actual_scope_type NOT IN ('platform', 'tenant')"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "ux_role_bindings_active_resource",
        table_name="role_bindings",
    )
    op.drop_index(
        "ux_role_bindings_active_tenant",
        table_name="role_bindings",
    )
    op.drop_index(
        "ux_role_bindings_active_platform",
        table_name="role_bindings",
    )
    op.drop_index("idx_role_bindings_tenant", table_name="role_bindings")
    op.drop_index("idx_role_bindings_role", table_name="role_bindings")
    op.drop_index("idx_role_bindings_principal", table_name="role_bindings")
    op.drop_table("role_bindings")

    op.drop_index("idx_roles_tenant", table_name="roles")
    with op.batch_alter_table("roles") as batch_op:
        batch_op.drop_constraint(
            "fk_roles_tenant_id_tenants",
            type_="foreignkey",
        )
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("policy_version")
        batch_op.drop_column("status")
        batch_op.drop_column("is_assignable")
        batch_op.drop_column("allowed_scope_type")
        batch_op.drop_column("display_name")
        batch_op.drop_column("tenant_id")
