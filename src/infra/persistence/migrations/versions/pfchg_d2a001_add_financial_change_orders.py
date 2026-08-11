"""Add governed project financial change orders.

Revision ID: pfchg_d2a001
Revises: w0x1y2z3a4b5
Create Date: 2026-08-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from src.infra.persistence.migrations.helpers.postgresql_rls import (
    disable_tenant_organization_rls,
    enable_tenant_organization_rls,
)


revision = "pfchg_d2a001"
down_revision = "w0x1y2z3a4b5"
branch_labels = None
depends_on = None

_TABLES = (
    "project_finance_change_requests",
    "project_finance_change_impacts",
)

_D1_LINE_TYPES = (
    "source_type IN ('remaining_plan', 'open_commitment', 'risk', 'manual_estimate')"
)
_D2_LINE_TYPES = (
    "source_type IN ('remaining_plan', 'open_commitment', 'risk', 'manual_estimate', "
    "'base_forecast', 'financial_change')"
)
_D1_LINE_METADATA = (
    "(source_kind = 'manual' AND source_type = 'manual_estimate') OR "
    "(source_kind = 'manual' AND source_type = 'risk' "
    "AND source_reference_type IS NOT NULL AND source_reference_id IS NOT NULL "
    "AND source_snapshot_at IS NOT NULL) OR "
    "(source_kind = 'automatic' AND source_type <> 'manual_estimate' "
    "AND source_reference_type IS NOT NULL AND source_reference_id IS NOT NULL "
    "AND source_snapshot_at IS NOT NULL)"
)
_D2_LINE_METADATA = (
    "(source_kind = 'manual' AND source_type = 'manual_estimate') OR "
    "(source_kind = 'manual' AND source_type IN ('risk', 'financial_change') "
    "AND source_reference_type IS NOT NULL AND source_reference_id IS NOT NULL "
    "AND source_snapshot_at IS NOT NULL) OR "
    "(source_kind = 'automatic' AND source_type <> 'manual_estimate' "
    "AND source_reference_type IS NOT NULL AND source_reference_id IS NOT NULL "
    "AND source_snapshot_at IS NOT NULL)"
)
_D1_DECISION_REASONS = (
    "reason IN ('remaining_plan', 'open_commitment', 'posted_actual_offset', "
    "'actual_credit', 'reversed_actual', 'manual_override', 'risk_contingency', "
    "'no_remaining_amount', 'closed_or_cancelled', 'after_as_of')"
)
_D2_DECISION_REASONS = (
    "reason IN ('remaining_plan', 'open_commitment', 'posted_actual_offset', "
    "'actual_credit', 'reversed_actual', 'manual_override', 'risk_contingency', "
    "'no_remaining_amount', 'closed_or_cancelled', 'after_as_of', "
    "'base_forecast', 'financial_change')"
)
_D1_DECISION_TYPES = (
    "source_type IN ('remaining_plan', 'open_commitment', 'risk', 'manual_estimate', "
    "'posted_actual')"
)
_D2_DECISION_TYPES = (
    "source_type IN ('remaining_plan', 'open_commitment', 'risk', 'manual_estimate', "
    "'posted_actual', 'base_forecast', 'financial_change')"
)


def _replace_forecast_constraints(
    *,
    line_types: str,
    line_metadata: str,
    decision_reasons: str,
    decision_types: str,
) -> None:
    with op.batch_alter_table("project_finance_forecast_lines") as batch_op:
        batch_op.drop_constraint("ck_pf_forecast_lines_source_type", type_="check")
        batch_op.drop_constraint("ck_pf_forecast_lines_source_metadata", type_="check")
        batch_op.create_check_constraint("ck_pf_forecast_lines_source_type", line_types)
        batch_op.create_check_constraint(
            "ck_pf_forecast_lines_source_metadata", line_metadata
        )
    with op.batch_alter_table(
        "project_finance_forecast_source_decisions"
    ) as batch_op:
        batch_op.drop_constraint("ck_pf_forecast_decisions_reason", type_="check")
        batch_op.drop_constraint("ck_pf_forecast_decisions_source_type", type_="check")
        batch_op.create_check_constraint(
            "ck_pf_forecast_decisions_reason", decision_reasons
        )
        batch_op.create_check_constraint(
            "ck_pf_forecast_decisions_source_type", decision_types
        )


def upgrade() -> None:
    bind = op.get_bind()
    _replace_forecast_constraints(
        line_types=_D2_LINE_TYPES,
        line_metadata=_D2_LINE_METADATA,
        decision_reasons=_D2_DECISION_REASONS,
        decision_types=_D2_DECISION_TYPES,
    )
    op.create_table(
        "project_finance_change_requests",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False, server_default=""),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("base_budget_id", sa.String(), nullable=True),
        sa.Column("base_budget_revision", sa.Integer(), nullable=True),
        sa.Column("base_forecast_id", sa.String(), nullable=True),
        sa.Column("base_forecast_revision", sa.Integer(), nullable=True),
        sa.Column("approval_request_id", sa.String(), nullable=True),
        sa.Column("applied_budget_id", sa.String(), nullable=True),
        sa.Column("applied_forecast_id", sa.String(), nullable=True),
        sa.Column("applied_schedule_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("submitted_by", sa.String(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_by", sa.String(), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by", sa.String(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_notes", sa.String(), nullable=False, server_default=""),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'pending_approval', 'applied', 'rejected')",
            name="ck_pf_changes_status",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_pf_changes_revision"),
        sa.CheckConstraint("version >= 1", name="ck_pf_changes_version"),
        sa.CheckConstraint(
            "applied_schedule_count >= 0", name="ck_pf_changes_schedule_count"
        ),
        sa.CheckConstraint(
            "(base_budget_id IS NULL AND base_budget_revision IS NULL) OR "
            "(base_budget_id IS NOT NULL AND base_budget_revision >= 1)",
            name="ck_pf_changes_base_budget_pair",
        ),
        sa.CheckConstraint(
            "(base_forecast_id IS NULL AND base_forecast_revision IS NULL) OR "
            "(base_forecast_id IS NOT NULL AND base_forecast_revision >= 1)",
            name="ck_pf_changes_base_forecast_pair",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"],
            name="fk_pf_changes_tenant", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id"],
            ["organizations.tenant_id", "organizations.id"],
            name="fk_pf_changes_scoped_organization", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_changes_scoped_project", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "base_budget_id"],
            ["project_finance_budgets.tenant_id", "project_finance_budgets.organization_id", "project_finance_budgets.project_id", "project_finance_budgets.id"],
            name="fk_pf_changes_scoped_base_budget", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "base_forecast_id"],
            ["project_finance_forecasts.tenant_id", "project_finance_forecasts.organization_id", "project_finance_forecasts.project_id", "project_finance_forecasts.id"],
            name="fk_pf_changes_scoped_base_forecast", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "applied_budget_id"],
            ["project_finance_budgets.tenant_id", "project_finance_budgets.organization_id", "project_finance_budgets.project_id", "project_finance_budgets.id"],
            name="fk_pf_changes_scoped_applied_budget", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "applied_forecast_id"],
            ["project_finance_forecasts.tenant_id", "project_finance_forecasts.organization_id", "project_finance_forecasts.project_id", "project_finance_forecasts.id"],
            name="fk_pf_changes_scoped_applied_forecast", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["approval_request_id"], ["approval_requests.id"],
            name="fk_pf_changes_approval_request", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "organization_id", "project_id", "id",
            name="uq_pf_change_scope_project_id",
        ),
        sa.UniqueConstraint(
            "tenant_id", "organization_id", "project_id", "revision",
            name="uq_pf_change_project_revision",
        ),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index(
        "idx_pf_changes_scope", "project_finance_change_requests",
        ["tenant_id", "organization_id"],
    )
    op.create_index(
        "idx_pf_changes_project", "project_finance_change_requests", ["project_id"]
    )
    op.create_index(
        "idx_pf_changes_status", "project_finance_change_requests", ["status"]
    )
    op.create_index(
        "idx_pf_changes_approval", "project_finance_change_requests", ["approval_request_id"]
    )

    op.create_table(
        "project_finance_change_impacts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("change_request_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("impact_type", sa.String(length=16), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4, asdecimal=True), nullable=False, server_default="0"),
        sa.Column("currency_code", sa.String(length=8), nullable=True),
        sa.Column("cost_code_id", sa.String(), nullable=True),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("target_line_id", sa.String(), nullable=True),
        sa.Column("target_task_version", sa.Integer(), nullable=True),
        sa.Column("schedule_start", sa.Date(), nullable=True),
        sa.Column("schedule_finish", sa.Date(), nullable=True),
        sa.Column("applied_reference_type", sa.String(length=32), nullable=True),
        sa.Column("applied_reference_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "impact_type IN ('budget', 'forecast', 'schedule')",
            name="ck_pf_change_impacts_type",
        ),
        sa.CheckConstraint(
            "impact_type NOT IN ('budget', 'forecast') OR "
            "(amount <> 0 AND currency_code IS NOT NULL AND cost_code_id IS NOT NULL)",
            name="ck_pf_change_impacts_monetary_shape",
        ),
        sa.CheckConstraint(
            "impact_type <> 'schedule' OR "
            "(task_id IS NOT NULL AND target_task_version >= 1 AND "
            "(schedule_start IS NOT NULL OR schedule_finish IS NOT NULL) AND amount = 0 AND "
            "currency_code IS NULL AND cost_code_id IS NULL AND target_line_id IS NULL)",
            name="ck_pf_change_impacts_schedule_shape",
        ),
        sa.CheckConstraint(
            "impact_type = 'schedule' OR target_task_version IS NULL",
            name="ck_pf_change_impacts_task_version",
        ),
        sa.CheckConstraint(
            "schedule_start IS NULL OR schedule_finish IS NULL OR schedule_finish >= schedule_start",
            name="ck_pf_change_impacts_schedule_period",
        ),
        sa.CheckConstraint(
            "amount >= 0 OR target_line_id IS NOT NULL OR impact_type NOT IN ('budget', 'forecast')",
            name="ck_pf_change_impacts_negative_target",
        ),
        sa.CheckConstraint(
            "(applied_reference_type IS NULL AND applied_reference_id IS NULL) OR "
            "(applied_reference_type IS NOT NULL AND applied_reference_id IS NOT NULL)",
            name="ck_pf_change_impacts_applied_pair",
        ),
        sa.CheckConstraint(
            "applied_reference_type IS NULL OR "
            "(impact_type = 'budget' AND applied_reference_type = 'budget_line') OR "
            "(impact_type = 'forecast' AND applied_reference_type = 'forecast_line') OR "
            "(impact_type = 'schedule' AND applied_reference_type = 'task')",
            name="ck_pf_change_impacts_applied_type",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"],
            name="fk_pf_change_impacts_tenant", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "change_request_id"],
            ["project_finance_change_requests.tenant_id", "project_finance_change_requests.organization_id", "project_finance_change_requests.project_id", "project_finance_change_requests.id"],
            name="fk_pf_change_impacts_scoped_request", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "cost_code_id"],
            ["project_finance_cost_codes.tenant_id", "project_finance_cost_codes.organization_id", "project_finance_cost_codes.id"],
            name="fk_pf_change_impacts_scoped_cost_code", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["tasks.id"],
            name="fk_pf_change_impacts_task", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index(
        "idx_pf_change_impacts_scope", "project_finance_change_impacts",
        ["tenant_id", "organization_id"],
    )
    op.create_index(
        "idx_pf_change_impacts_request", "project_finance_change_impacts",
        ["change_request_id"],
    )
    op.create_index(
        "idx_pf_change_impacts_target", "project_finance_change_impacts", ["target_line_id"]
    )
    op.create_index(
        "idx_pf_change_impacts_task", "project_finance_change_impacts", ["task_id"]
    )
    for table_name in _TABLES:
        enable_tenant_organization_rls(op, bind, table_name)


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in reversed(_TABLES):
        disable_tenant_organization_rls(op, bind, table_name)
        op.drop_table(table_name)
    _replace_forecast_constraints(
        line_types=_D1_LINE_TYPES,
        line_metadata=_D1_LINE_METADATA,
        decision_reasons=_D1_DECISION_REASONS,
        decision_types=_D1_DECISION_TYPES,
    )
