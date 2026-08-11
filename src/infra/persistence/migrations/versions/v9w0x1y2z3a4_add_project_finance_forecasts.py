"""add canonical project forecast versions and lines

Revision ID: v9w0x1y2z3a4
Revises: u8v9w0x1y2z3
Create Date: 2026-08-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from src.infra.persistence.migrations.helpers.postgresql_rls import (
    disable_tenant_organization_rls,
    enable_tenant_organization_rls,
)


revision = "v9w0x1y2z3a4"
down_revision = "u8v9w0x1y2z3"
branch_labels = None
depends_on = None

_TABLES = (
    "project_finance_forecasts",
    "project_finance_forecast_lines",
)


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table(
        "project_finance_forecasts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("generation_mode", sa.String(length=16), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
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
        sa.Column("notes", sa.String(), nullable=False, server_default=""),
        sa.Column("submission_notes", sa.String(), nullable=False, server_default=""),
        sa.Column("approval_notes", sa.String(), nullable=False, server_default=""),
        sa.Column("rejection_notes", sa.String(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'submitted', 'approved', 'rejected', 'superseded')",
            name="ck_pf_forecasts_status",
        ),
        sa.CheckConstraint(
            "generation_mode IN ('automatic', 'manual', 'hybrid')",
            name="ck_pf_forecasts_generation_mode",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_pf_forecasts_revision"),
        sa.CheckConstraint("version >= 1", name="ck_pf_forecasts_version"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"],
            name="fk_pf_forecasts_tenant", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id"],
            ["organizations.tenant_id", "organizations.id"],
            name="fk_pf_forecasts_scoped_organization", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_forecasts_scoped_project", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "organization_id", "id",
            name="uq_pf_forecasts_scoped_id",
        ),
        sa.UniqueConstraint(
            "tenant_id", "organization_id", "project_id", "id",
            name="uq_pf_forecast_scope_project_id",
        ),
        sa.UniqueConstraint(
            "tenant_id", "organization_id", "project_id", "revision",
            name="uq_pf_forecast_project_revision",
        ),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index(
        "idx_pf_forecasts_scope", "project_finance_forecasts",
        ["tenant_id", "organization_id"],
    )
    op.create_index(
        "idx_pf_forecasts_project", "project_finance_forecasts", ["project_id"]
    )
    op.create_index(
        "uq_pf_forecasts_one_approved_per_project",
        "project_finance_forecasts",
        ["tenant_id", "organization_id", "project_id"],
        unique=True,
        postgresql_where=sa.text("status = 'approved'"),
        sqlite_where=sa.text("status = 'approved'"),
    )
    op.create_index(
        "uq_pf_forecasts_one_open_per_project",
        "project_finance_forecasts",
        ["tenant_id", "organization_id", "project_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('draft', 'submitted')"),
        sqlite_where=sa.text("status IN ('draft', 'submitted')"),
    )

    op.create_table(
        "project_finance_forecast_lines",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("forecast_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("cost_code_id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=False, server_default=""),
        sa.Column("amount", sa.Numeric(19, 4, asdecimal=True), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("source_kind", sa.String(length=16), nullable=False),
        sa.Column("source_type", sa.String(length=24), nullable=False),
        sa.Column("source_reference_type", sa.String(length=64), nullable=True),
        sa.Column("source_reference_id", sa.String(), nullable=True),
        sa.Column("source_snapshot_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount >= 0", name="ck_pf_forecast_lines_amount"),
        sa.CheckConstraint("version >= 1", name="ck_pf_forecast_lines_version"),
        sa.CheckConstraint(
            "source_kind IN ('automatic', 'manual')",
            name="ck_pf_forecast_lines_source_kind",
        ),
        sa.CheckConstraint(
            "source_type IN ('remaining_plan', 'open_commitment', 'risk', 'manual_estimate')",
            name="ck_pf_forecast_lines_source_type",
        ),
        sa.CheckConstraint(
            "(period_start IS NULL AND period_end IS NULL) OR "
            "(period_start IS NOT NULL AND period_end IS NOT NULL AND period_end >= period_start)",
            name="ck_pf_forecast_lines_period",
        ),
        sa.CheckConstraint(
            "(source_kind = 'manual' AND source_type = 'manual_estimate') OR "
            "(source_kind = 'automatic' AND source_type <> 'manual_estimate' "
            "AND source_reference_type IS NOT NULL AND source_reference_id IS NOT NULL "
            "AND source_snapshot_at IS NOT NULL)",
            name="ck_pf_forecast_lines_source_metadata",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"],
            name="fk_pf_forecast_lines_tenant", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "forecast_id"],
            [
                "project_finance_forecasts.tenant_id",
                "project_finance_forecasts.organization_id",
                "project_finance_forecasts.project_id",
                "project_finance_forecasts.id",
            ],
            name="fk_pf_forecast_lines_scoped_forecast", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_forecast_lines_scoped_project", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "cost_code_id"],
            [
                "project_finance_cost_codes.tenant_id",
                "project_finance_cost_codes.organization_id",
                "project_finance_cost_codes.id",
            ],
            name="fk_pf_forecast_lines_scoped_cost_code", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["tasks.id"],
            name="fk_pf_forecast_lines_task", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index(
        "idx_pf_forecast_lines_scope", "project_finance_forecast_lines",
        ["tenant_id", "organization_id"],
    )
    op.create_index(
        "idx_pf_forecast_lines_forecast", "project_finance_forecast_lines", ["forecast_id"]
    )
    op.create_index(
        "idx_pf_forecast_lines_cost_code", "project_finance_forecast_lines", ["cost_code_id"]
    )
    op.create_index(
        "idx_pf_forecast_lines_task", "project_finance_forecast_lines", ["task_id"]
    )
    op.create_index(
        "idx_pf_forecast_lines_source", "project_finance_forecast_lines",
        ["source_reference_type", "source_reference_id"],
    )
    for table_name in _TABLES:
        enable_tenant_organization_rls(op, bind, table_name)


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in reversed(_TABLES):
        disable_tenant_organization_rls(op, bind, table_name)
    op.drop_table("project_finance_forecast_lines")
    op.drop_table("project_finance_forecasts")
