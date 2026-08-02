"""Drop superseded legacy RBAC authority tables.

Revision ID: c1e2a3n4u5p6
Revises: b1n2o3t4i5f6

All resource/organization scopes now route authority exclusively through
canonical `role_bindings`. This drops the legacy tables no production code
reads or writes anymore: `user_roles`, `scoped_access_grants`,
`project_memberships` (superseded authority), and
`authorization_migration_batches` / `legacy_role_binding_migration_records`
(bookkeeping for a staged legacy-to-canonical backfill this program bypassed
via direct cutover instead).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c1e2a3n4u5p6"
down_revision = "b1n2o3t4i5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(
        "idx_legacy_role_binding_migration_reason",
        table_name="legacy_role_binding_migration_records",
    )
    op.drop_index(
        "idx_legacy_role_binding_migration_batch_status",
        table_name="legacy_role_binding_migration_records",
    )
    op.drop_table("legacy_role_binding_migration_records")

    op.drop_index(
        "idx_authorization_migration_batches_status",
        table_name="authorization_migration_batches",
    )
    op.drop_table("authorization_migration_batches")

    op.drop_index("idx_user_roles_organization", table_name="user_roles")
    op.drop_index("idx_user_roles_role", table_name="user_roles")
    op.drop_index("idx_user_roles_user", table_name="user_roles")
    op.drop_table("user_roles")

    op.drop_index("idx_scoped_access_tenant", table_name="scoped_access_grants")
    op.drop_index("idx_scoped_access_scope", table_name="scoped_access_grants")
    op.drop_index("idx_scoped_access_user", table_name="scoped_access_grants")
    op.drop_table("scoped_access_grants")

    op.drop_index("idx_project_memberships_org", table_name="project_memberships")
    op.drop_index("idx_project_memberships_project", table_name="project_memberships")
    op.drop_index("idx_project_memberships_user", table_name="project_memberships")
    op.drop_table("project_memberships")


def downgrade() -> None:
    op.create_table(
        "project_memberships",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "project_id",
            sa.String(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scope_role", sa.String(64), nullable=False, server_default="viewer"),
        sa.Column("permission_codes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id", "user_id", name="ux_project_memberships_project_user"
        ),
    )
    op.create_index(
        "idx_project_memberships_user", "project_memberships", ["user_id"]
    )
    op.create_index(
        "idx_project_memberships_project", "project_memberships", ["project_id"]
    )
    op.create_index(
        "idx_project_memberships_org", "project_memberships", ["organization_id"]
    )

    op.create_table(
        "scoped_access_grants",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("scope_type", sa.String(64), nullable=False),
        sa.Column("scope_id", sa.String(), nullable=False),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scope_role", sa.String(64), nullable=False, server_default="viewer"),
        sa.Column("permission_codes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "scope_type",
            "scope_id",
            "user_id",
            name="ux_scoped_access_tenant_scope_user",
        ),
    )
    op.create_index(
        "idx_scoped_access_user", "scoped_access_grants", ["user_id"]
    )
    op.create_index(
        "idx_scoped_access_scope", "scoped_access_grants", ["scope_type", "scope_id"]
    )
    op.create_index(
        "idx_scoped_access_tenant", "scoped_access_grants", ["tenant_id"]
    )

    op.create_table(
        "user_roles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            sa.String(),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey(
                "organizations.id",
                ondelete="CASCADE",
                name="fk_user_roles_organization_id",
            ),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "role_id", "organization_id", name="ux_user_roles_user_role_org"
        ),
    )
    op.create_index("idx_user_roles_user", "user_roles", ["user_id"])
    op.create_index("idx_user_roles_role", "user_roles", ["role_id"])
    op.create_index("idx_user_roles_organization", "user_roles", ["organization_id"])

    op.create_table(
        "authorization_migration_batches",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_inventory_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_record_count", sa.Integer(), nullable=False),
        sa.Column("reviewed_plan_sha256", sa.String(length=64), nullable=False),
        sa.Column("reviewer_id", sa.String(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint(
            "status IN ('prepared', 'applied', 'rolled_back')",
            name="ck_authorization_migration_batches_status",
        ),
        sa.CheckConstraint(
            "source_record_count >= 0",
            name="ck_authorization_migration_batches_record_count",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_authorization_migration_batches_version",
        ),
        sa.CheckConstraint(
            "length(source_inventory_sha256) = 64",
            name="ck_authorization_migration_batches_hash_length",
        ),
        sa.CheckConstraint(
            "length(reviewed_plan_sha256) = 64",
            name="ck_authorization_migration_batches_plan_hash_length",
        ),
        sa.CheckConstraint(
            "("
            "status = 'prepared' AND applied_at IS NULL "
            "AND rolled_back_at IS NULL"
            ") OR ("
            "status = 'applied' AND applied_at IS NOT NULL "
            "AND rolled_back_at IS NULL"
            ") OR ("
            "status = 'rolled_back' AND applied_at IS NOT NULL "
            "AND rolled_back_at IS NOT NULL"
            ")",
            name="ck_authorization_migration_batches_lifecycle",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_inventory_sha256",
            name="ux_authorization_migration_batches_inventory",
        ),
    )
    op.create_index(
        "idx_authorization_migration_batches_status",
        "authorization_migration_batches",
        ["status"],
    )

    op.create_table(
        "legacy_role_binding_migration_records",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("batch_id", sa.String(), nullable=False),
        sa.Column("legacy_binding_id", sa.String(), nullable=False),
        sa.Column("source_user_id", sa.String(), nullable=False),
        sa.Column("source_role_id", sa.String(), nullable=False),
        sa.Column("source_organization_id", sa.String(), nullable=True),
        sa.Column("source_snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("quarantine_reason_code", sa.String(length=128), nullable=True),
        sa.Column("resolved_tenant_id", sa.String(), nullable=True),
        sa.Column("resolved_scope_type", sa.String(length=64), nullable=True),
        sa.Column("resolved_scope_id", sa.String(), nullable=True),
        sa.Column("canonical_binding_id", sa.String(), nullable=True),
        sa.Column("reviewed_by", sa.String(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint(
            "status IN ('ready', 'quarantined', 'applied', 'rolled_back')",
            name="ck_legacy_role_binding_migration_status",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_legacy_role_binding_migration_version",
        ),
        sa.CheckConstraint(
            "length(source_snapshot_sha256) = 64",
            name="ck_legacy_role_binding_migration_hash_length",
        ),
        sa.CheckConstraint(
            "("
            "status = 'quarantined' AND quarantine_reason_code IS NOT NULL "
            "AND canonical_binding_id IS NULL "
            "AND resolved_tenant_id IS NULL "
            "AND resolved_scope_type IS NULL "
            "AND resolved_scope_id IS NULL"
            ") OR ("
            "status <> 'quarantined' AND quarantine_reason_code IS NULL "
            "AND resolved_scope_type IS NOT NULL "
            "AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL"
            ")",
            name="ck_legacy_role_binding_migration_resolution",
        ),
        sa.CheckConstraint(
            "("
            "status IN ('ready', 'quarantined') "
            "AND canonical_binding_id IS NULL"
            ") OR ("
            "status IN ('applied', 'rolled_back') "
            "AND canonical_binding_id IS NOT NULL"
            ")",
            name="ck_legacy_role_binding_migration_canonical_state",
        ),
        sa.CheckConstraint(
            "(reviewed_by IS NULL AND reviewed_at IS NULL) OR "
            "(reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="ck_legacy_role_binding_migration_review",
        ),
        sa.CheckConstraint(
            "status = 'quarantined' OR ("
            "resolved_scope_type = 'platform' "
            "AND resolved_tenant_id IS NULL "
            "AND resolved_scope_id IS NULL"
            ") OR ("
            "resolved_scope_type = 'tenant' "
            "AND resolved_tenant_id IS NOT NULL "
            "AND resolved_scope_id IS NULL"
            ") OR ("
            "resolved_scope_type NOT IN ('platform', 'tenant') "
            "AND resolved_tenant_id IS NOT NULL "
            "AND resolved_scope_id IS NOT NULL"
            ")",
            name="ck_legacy_role_binding_migration_scope_shape",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["authorization_migration_batches.id"],
            name="fk_legacy_role_binding_migration_batch",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "batch_id",
            "legacy_binding_id",
            name="ux_legacy_role_binding_migration_batch_source",
        ),
    )
    op.create_index(
        "idx_legacy_role_binding_migration_batch_status",
        "legacy_role_binding_migration_records",
        ["batch_id", "status"],
    )
    op.create_index(
        "idx_legacy_role_binding_migration_reason",
        "legacy_role_binding_migration_records",
        ["quarantine_reason_code"],
    )
