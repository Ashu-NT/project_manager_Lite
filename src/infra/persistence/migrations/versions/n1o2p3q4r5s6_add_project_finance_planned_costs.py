"""add project finance planned-cost snapshots (Phase B item 6)

Revision ID: n1o2p3q4r5s6
Revises: m1n2o3p4q5r6
Create Date: 2026-08-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from src.infra.persistence.migrations.helpers.postgresql_rls import (
    disable_tenant_organization_rls,
    enable_tenant_organization_rls,
)


revision = "n1o2p3q4r5s6"
down_revision = "m1n2o3p4q5r6"
branch_labels = None
depends_on = None


_TABLES = (
    "project_finance_planned_cost_lines",
    "project_finance_planned_cost_versions",
)


def upgrade() -> None:
    bind = op.get_bind()

    # Tactical WBS distribution of a resource's ProjectResource.planned_hours
    # envelope, and its own optimistic-concurrency token — see
    # domain/tasks/task.py's TaskAssignment.allocated_planned_hours docstring
    # and domain/financials/planned_cost.py's module docstring.
    op.add_column(
        "task_assignments",
        sa.Column(
            "allocated_planned_hours",
            sa.Numeric(19, 6, asdecimal=True),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "task_assignments",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )

    # Envelope-side optimistic-concurrency token, touched (with no other
    # field change) whenever a planned-hours reconciliation transaction
    # needs to make a concurrent envelope shrink and a concurrent
    # allocation increase detectable against each other.
    op.add_column(
        "project_resources",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "project_finance_planned_cost_versions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="current"
        ),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("calculated_by", sa.String(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "rates_complete", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "allocations_complete",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "cost_codes_complete",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "unresolved_rate_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "partially_allocated_resource_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "unclassified_line_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("superseded_by", sa.String(), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('current', 'superseded')",
            name="ck_pf_planned_cost_versions_status",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_pf_planned_cost_versions_revision"),
        sa.CheckConstraint("version >= 1", name="ck_pf_planned_cost_versions_version"),
        sa.CheckConstraint(
            "unresolved_rate_count >= 0",
            name="ck_pf_planned_cost_versions_unresolved_rate_count",
        ),
        sa.CheckConstraint(
            "partially_allocated_resource_count >= 0",
            name="ck_pf_planned_cost_versions_partial_alloc_count",
        ),
        sa.CheckConstraint(
            "unclassified_line_count >= 0",
            name="ck_pf_planned_cost_versions_unclassified_count",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_pf_planned_cost_versions_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id"],
            ["organizations.tenant_id", "organizations.id"],
            name="fk_pf_planned_cost_versions_scoped_organization",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_planned_cost_versions_scoped_project",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "organization_id",
            "id",
            name="uq_pf_planned_cost_versions_scoped_id",
        ),
        # Enables the line's four-column composite FK — the real, DB-level
        # guarantee that ProjectPlannedCostLine.project_id ==
        # ProjectPlannedCostVersion.project_id.
        sa.UniqueConstraint(
            "tenant_id",
            "organization_id",
            "project_id",
            "id",
            name="uq_pf_planned_cost_versions_scope_project_id",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "organization_id",
            "project_id",
            "revision",
            name="uq_pf_planned_cost_versions_project_revision",
        ),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index(
        "idx_pf_planned_cost_versions_scope",
        "project_finance_planned_cost_versions",
        ["tenant_id", "organization_id"],
    )
    op.create_index(
        "idx_pf_planned_cost_versions_project",
        "project_finance_planned_cost_versions",
        ["project_id"],
    )
    op.create_index(
        "uq_pf_planned_cost_versions_one_current_per_project",
        "project_finance_planned_cost_versions",
        ["tenant_id", "organization_id", "project_id"],
        unique=True,
        postgresql_where=sa.text("status = 'current'"),
        sqlite_where=sa.text("status = 'current'"),
    )

    op.create_table(
        "project_finance_planned_cost_lines",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("version_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=False),
        sa.Column("project_resource_id", sa.String(), nullable=False),
        sa.Column("cost_code_id", sa.String(), nullable=False),
        # Plain, immutable, snapshotted identifier — deliberately NOT a live
        # foreign key. The line's hours/rate/amount/currency/dimensions are
        # already fully self-contained, so deleting the operational
        # TaskAssignment later (a routine scheduling action) must not be
        # blocked, and must not erase which record produced this line's
        # numbers.
        sa.Column("source_assignment_id", sa.String(), nullable=False),
        sa.Column("planned_hours", sa.Numeric(19, 6, asdecimal=True), nullable=False),
        sa.Column("rate_amount", sa.Numeric(19, 8, asdecimal=True), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4, asdecimal=True), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("rate_card_id", sa.String(), nullable=False),
        sa.Column("rate_line_id", sa.String(), nullable=False),
        sa.Column("rate_card_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("planned_hours >= 0", name="ck_pf_planned_cost_lines_hours"),
        sa.CheckConstraint(
            "rate_amount >= 0", name="ck_pf_planned_cost_lines_rate_amount"
        ),
        sa.CheckConstraint("amount >= 0", name="ck_pf_planned_cost_lines_amount"),
        sa.CheckConstraint(
            "rate_card_version >= 1", name="ck_pf_planned_cost_lines_rate_card_version"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_pf_planned_cost_lines_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "version_id"],
            [
                "project_finance_planned_cost_versions.tenant_id",
                "project_finance_planned_cost_versions.organization_id",
                "project_finance_planned_cost_versions.project_id",
                "project_finance_planned_cost_versions.id",
            ],
            name="fk_pf_planned_cost_lines_scoped_version",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_planned_cost_lines_scoped_project",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "cost_code_id"],
            [
                "project_finance_cost_codes.tenant_id",
                "project_finance_cost_codes.organization_id",
                "project_finance_cost_codes.id",
            ],
            name="fk_pf_planned_cost_lines_scoped_cost_code",
            ondelete="RESTRICT",
        ),
        # RESTRICT: task/resource/project_resource are structural dimensions
        # of a persisted snapshot line (current or superseded) — deleting
        # any of them must not silently corrupt financial history.
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name="fk_pf_planned_cost_lines_task",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"],
            ["resources.id"],
            name="fk_pf_planned_cost_lines_resource",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_resource_id"],
            ["project_resources.id"],
            name="fk_pf_planned_cost_lines_project_resource",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index(
        "idx_pf_planned_cost_lines_scope",
        "project_finance_planned_cost_lines",
        ["tenant_id", "organization_id"],
    )
    op.create_index(
        "idx_pf_planned_cost_lines_version",
        "project_finance_planned_cost_lines",
        ["version_id"],
    )
    op.create_index(
        "idx_pf_planned_cost_lines_task",
        "project_finance_planned_cost_lines",
        ["task_id"],
    )
    op.create_index(
        "idx_pf_planned_cost_lines_cost_code",
        "project_finance_planned_cost_lines",
        ["cost_code_id"],
    )

    for table_name in _TABLES:
        enable_tenant_organization_rls(op, bind, table_name)


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in reversed(_TABLES):
        disable_tenant_organization_rls(op, bind, table_name)

    op.drop_index(
        "idx_pf_planned_cost_lines_cost_code",
        table_name="project_finance_planned_cost_lines",
    )
    op.drop_index(
        "idx_pf_planned_cost_lines_task",
        table_name="project_finance_planned_cost_lines",
    )
    op.drop_index(
        "idx_pf_planned_cost_lines_version",
        table_name="project_finance_planned_cost_lines",
    )
    op.drop_index(
        "idx_pf_planned_cost_lines_scope",
        table_name="project_finance_planned_cost_lines",
    )
    op.drop_table("project_finance_planned_cost_lines")

    op.drop_index(
        "uq_pf_planned_cost_versions_one_current_per_project",
        table_name="project_finance_planned_cost_versions",
    )
    op.drop_index(
        "idx_pf_planned_cost_versions_project",
        table_name="project_finance_planned_cost_versions",
    )
    op.drop_index(
        "idx_pf_planned_cost_versions_scope",
        table_name="project_finance_planned_cost_versions",
    )
    op.drop_table("project_finance_planned_cost_versions")

    op.drop_column("project_resources", "version")
    op.drop_column("task_assignments", "version")
    op.drop_column("task_assignments", "allocated_planned_hours")


__all__ = ["downgrade", "upgrade"]
