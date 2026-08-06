"""add project finance budgets (Phase B item 5)

Revision ID: m1n2o3p4q5r6
Revises: l0m1n2o3p4q5
Create Date: 2026-08-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from src.infra.persistence.migrations.helpers.postgresql_rls import (
    disable_tenant_organization_rls,
    enable_tenant_organization_rls,
)


revision = "m1n2o3p4q5r6"
down_revision = "l0m1n2o3p4q5"
branch_labels = None
depends_on = None


_TABLES = (
    "project_finance_budget_lines",
    "project_finance_budgets",
)


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "project_finance_budgets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="draft"
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("submitted_by", sa.String(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by", sa.String(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_by", sa.String(), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.String(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.String(), nullable=False, server_default=""),
        sa.Column("submission_notes", sa.String(), nullable=False, server_default=""),
        sa.Column("approval_notes", sa.String(), nullable=False, server_default=""),
        sa.Column("rejection_notes", sa.String(), nullable=False, server_default=""),
        sa.Column("closure_notes", sa.String(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'submitted', 'approved', 'rejected', "
            "'superseded', 'closed')",
            name="ck_pf_budgets_status",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_pf_budgets_revision"),
        sa.CheckConstraint("version >= 1", name="ck_pf_budgets_version"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_pf_budgets_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id"],
            ["organizations.tenant_id", "organizations.id"],
            name="fk_pf_budgets_scoped_organization",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_budgets_scoped_project",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "organization_id",
            "id",
            name="uq_pf_budgets_scoped_id",
        ),
        # Enables the line's four-column composite FK — the real, DB-level
        # guarantee that BudgetLine.project_id == ProjectBudget.project_id.
        sa.UniqueConstraint(
            "tenant_id",
            "organization_id",
            "project_id",
            "id",
            name="uq_pf_budget_scope_project_id",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "organization_id",
            "project_id",
            "revision",
            name="uq_pf_budget_project_revision",
        ),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index(
        "idx_pf_budgets_scope",
        "project_finance_budgets",
        ["tenant_id", "organization_id"],
    )
    op.create_index(
        "idx_pf_budgets_project",
        "project_finance_budgets",
        ["project_id"],
    )
    op.create_index(
        "uq_pf_budgets_one_approved_per_project",
        "project_finance_budgets",
        ["tenant_id", "organization_id", "project_id"],
        unique=True,
        postgresql_where=sa.text("status = 'approved'"),
        sqlite_where=sa.text("status = 'approved'"),
    )
    op.create_index(
        "uq_pf_budgets_one_open_per_project",
        "project_finance_budgets",
        ["tenant_id", "organization_id", "project_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('draft', 'submitted')"),
        sqlite_where=sa.text("status IN ('draft', 'submitted')"),
    )

    op.create_table(
        "project_finance_budget_lines",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("budget_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("cost_code_id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=False, server_default=""),
        sa.Column("amount", sa.Numeric(19, 4, asdecimal=True), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount >= 0", name="ck_pf_budget_lines_amount"),
        sa.CheckConstraint("version >= 1", name="ck_pf_budget_lines_version"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_pf_budget_lines_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "budget_id"],
            [
                "project_finance_budgets.tenant_id",
                "project_finance_budgets.organization_id",
                "project_finance_budgets.project_id",
                "project_finance_budgets.id",
            ],
            name="fk_pf_budget_lines_scoped_budget",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_budget_lines_scoped_project",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "cost_code_id"],
            [
                "project_finance_cost_codes.tenant_id",
                "project_finance_cost_codes.organization_id",
                "project_finance_cost_codes.id",
            ],
            name="fk_pf_budget_lines_scoped_cost_code",
            ondelete="RESTRICT",
        ),
        # RESTRICT, not SET NULL: a task referenced by any budget line must
        # not be silently detached by deleting the task — that would mutate
        # an approved, supposedly-immutable line with no BudgetService call,
        # no row_version bump, and no audit trail.
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name="fk_pf_budget_lines_task",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index(
        "idx_pf_budget_lines_scope",
        "project_finance_budget_lines",
        ["tenant_id", "organization_id"],
    )
    op.create_index(
        "idx_pf_budget_lines_budget",
        "project_finance_budget_lines",
        ["budget_id"],
    )
    op.create_index(
        "idx_pf_budget_lines_cost_code",
        "project_finance_budget_lines",
        ["cost_code_id"],
    )
    op.create_index(
        "idx_pf_budget_lines_task",
        "project_finance_budget_lines",
        ["task_id"],
    )

    for table_name in _TABLES:
        enable_tenant_organization_rls(op, bind, table_name)


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in reversed(_TABLES):
        disable_tenant_organization_rls(op, bind, table_name)

    op.drop_index("idx_pf_budget_lines_task", table_name="project_finance_budget_lines")
    op.drop_index(
        "idx_pf_budget_lines_cost_code", table_name="project_finance_budget_lines"
    )
    op.drop_index("idx_pf_budget_lines_budget", table_name="project_finance_budget_lines")
    op.drop_index("idx_pf_budget_lines_scope", table_name="project_finance_budget_lines")
    op.drop_table("project_finance_budget_lines")

    op.drop_index(
        "uq_pf_budgets_one_open_per_project", table_name="project_finance_budgets"
    )
    op.drop_index(
        "uq_pf_budgets_one_approved_per_project", table_name="project_finance_budgets"
    )
    op.drop_index("idx_pf_budgets_project", table_name="project_finance_budgets")
    op.drop_index("idx_pf_budgets_scope", table_name="project_finance_budgets")
    op.drop_table("project_finance_budgets")


__all__ = ["downgrade", "upgrade"]
