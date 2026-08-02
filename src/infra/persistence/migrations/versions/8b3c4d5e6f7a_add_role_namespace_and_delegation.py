"""Add tenant role namespaces and explicit delegation policies.

Revision ID: 8b3c4d5e6f7a
Revises: 7a2b3c4d5e6f
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "8b3c4d5e6f7a"
down_revision = "7a2b3c4d5e6f"
branch_labels = None
depends_on = None


_SQLITE_NAMING_CONVENTION = {
    "uq": "uq_%(table_name)s_%(column_0_name)s",
}


def _drop_global_role_name_constraint() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "roles",
            naming_convention=_SQLITE_NAMING_CONVENTION,
        ) as batch_op:
            batch_op.drop_constraint("uq_roles_name", type_="unique")
            batch_op.create_check_constraint(
                "ck_roles_ownership",
                "(is_system AND tenant_id IS NULL) OR "
                "(NOT is_system AND tenant_id IS NOT NULL)",
            )
            batch_op.create_check_constraint(
                "ck_roles_custom_scope",
                "is_system OR allowed_scope_type <> 'platform'",
            )
        return

    inspector = sa.inspect(bind)
    global_name_constraint = next(
        (
            constraint
            for constraint in inspector.get_unique_constraints("roles")
            if constraint.get("column_names") == ["name"]
        ),
        None,
    )
    if global_name_constraint is not None:
        constraint_name = global_name_constraint.get("name")
        if not constraint_name:
            raise RuntimeError(
                "The global roles.name constraint must be named before "
                "tenant role namespaces can be enabled."
            )
        op.drop_constraint(
            constraint_name,
            "roles",
            type_="unique",
        )
    op.create_check_constraint(
        "ck_roles_ownership",
        "roles",
        "(is_system AND tenant_id IS NULL) OR "
        "(NOT is_system AND tenant_id IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_roles_custom_scope",
        "roles",
        "is_system OR allowed_scope_type <> 'platform'",
    )


def _restore_global_role_name_constraint() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "roles",
            naming_convention=_SQLITE_NAMING_CONVENTION,
        ) as batch_op:
            batch_op.drop_constraint(
                "ck_roles_custom_scope",
                type_="check",
            )
            batch_op.drop_constraint(
                "ck_roles_ownership",
                type_="check",
            )
            batch_op.create_unique_constraint(
                "uq_roles_name",
                ["name"],
            )
        return

    op.drop_constraint(
        "ck_roles_custom_scope",
        "roles",
        type_="check",
    )
    op.drop_constraint(
        "ck_roles_ownership",
        "roles",
        type_="check",
    )
    op.create_unique_constraint(
        "uq_roles_name",
        "roles",
        ["name"],
    )


def upgrade() -> None:
    op.drop_index("idx_roles_name", table_name="roles")
    _drop_global_role_name_constraint()
    op.create_index(
        "ux_roles_system_name",
        "roles",
        ["name"],
        unique=True,
        sqlite_where=sa.text("tenant_id IS NULL"),
        postgresql_where=sa.text("tenant_id IS NULL"),
    )
    op.create_index(
        "ux_roles_tenant_name",
        "roles",
        ["tenant_id", "name"],
        unique=True,
        sqlite_where=sa.text("tenant_id IS NOT NULL"),
        postgresql_where=sa.text("tenant_id IS NOT NULL"),
    )

    op.create_table(
        "role_delegation_policies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("actor_role_id", sa.String(), nullable=False),
        sa.Column("assignable_role_id", sa.String(), nullable=False),
        sa.Column("target_scope_type", sa.String(length=64), nullable=False),
        sa.Column(
            "assignable_role_policy_version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "assignable_permission_set_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "assignable_role_policy_version >= 1",
            name="ck_role_delegation_policy_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_role_delegation_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_role_id"],
            ["roles.id"],
            name="fk_role_delegation_actor_role_id_roles",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assignable_role_id"],
            ["roles.id"],
            name="fk_role_delegation_assignable_role_id_roles",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_role_delegation_created_by_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_role_delegation_actor",
        "role_delegation_policies",
        ["actor_role_id"],
    )
    op.create_index(
        "idx_role_delegation_assignable",
        "role_delegation_policies",
        ["assignable_role_id"],
    )
    op.create_index(
        "idx_role_delegation_tenant",
        "role_delegation_policies",
        ["tenant_id"],
    )
    op.create_index(
        "ux_role_delegation_active_system",
        "role_delegation_policies",
        [
            "actor_role_id",
            "assignable_role_id",
            "target_scope_type",
        ],
        unique=True,
        sqlite_where=sa.text(
            "revoked_at IS NULL AND tenant_id IS NULL"
        ),
        postgresql_where=sa.text(
            "revoked_at IS NULL AND tenant_id IS NULL"
        ),
    )
    op.create_index(
        "ux_role_delegation_active_tenant",
        "role_delegation_policies",
        [
            "tenant_id",
            "actor_role_id",
            "assignable_role_id",
            "target_scope_type",
        ],
        unique=True,
        sqlite_where=sa.text(
            "revoked_at IS NULL AND tenant_id IS NOT NULL"
        ),
        postgresql_where=sa.text(
            "revoked_at IS NULL AND tenant_id IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "ux_role_delegation_active_tenant",
        table_name="role_delegation_policies",
    )
    op.drop_index(
        "ux_role_delegation_active_system",
        table_name="role_delegation_policies",
    )
    op.drop_index(
        "idx_role_delegation_tenant",
        table_name="role_delegation_policies",
    )
    op.drop_index(
        "idx_role_delegation_assignable",
        table_name="role_delegation_policies",
    )
    op.drop_index(
        "idx_role_delegation_actor",
        table_name="role_delegation_policies",
    )
    op.drop_table("role_delegation_policies")

    op.drop_index("ux_roles_tenant_name", table_name="roles")
    op.drop_index("ux_roles_system_name", table_name="roles")
    _restore_global_role_name_constraint()
    op.create_index(
        "idx_roles_name",
        "roles",
        ["name"],
        unique=True,
    )
