"""add canonical forecast generation source decisions

Revision ID: w0x1y2z3a4b5
Revises: v9w0x1y2z3a4
Create Date: 2026-08-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from src.infra.persistence.migrations.helpers.postgresql_rls import (
    disable_tenant_organization_rls,
    enable_tenant_organization_rls,
)


revision = "w0x1y2z3a4b5"
down_revision = "v9w0x1y2z3a4"
branch_labels = None
depends_on = None

_DECISION_TABLE = "project_finance_forecast_source_decisions"
_LINE_TABLE = "project_finance_forecast_lines"

_ORIGINAL_LINE_SOURCE_METADATA = (
    "(source_kind = 'manual' AND source_type = 'manual_estimate') OR "
    "(source_kind = 'automatic' AND source_type <> 'manual_estimate' "
    "AND source_reference_type IS NOT NULL AND source_reference_id IS NOT NULL "
    "AND source_snapshot_at IS NOT NULL)"
)
_GENERATED_LINE_SOURCE_METADATA = (
    "(source_kind = 'manual' AND source_type = 'manual_estimate') OR "
    "(source_kind = 'manual' AND source_type = 'risk' "
    "AND source_reference_type IS NOT NULL AND source_reference_id IS NOT NULL "
    "AND source_snapshot_at IS NOT NULL) OR "
    "(source_kind = 'automatic' AND source_type <> 'manual_estimate' "
    "AND source_reference_type IS NOT NULL AND source_reference_id IS NOT NULL "
    "AND source_snapshot_at IS NOT NULL)"
)


def _replace_line_source_constraint(expression: str) -> None:
    with op.batch_alter_table(_LINE_TABLE) as batch_op:
        batch_op.drop_constraint(
            "ck_pf_forecast_lines_source_metadata", type_="check"
        )
        batch_op.create_check_constraint(
            "ck_pf_forecast_lines_source_metadata", expression
        )


def upgrade() -> None:
    bind = op.get_bind()
    _replace_line_source_constraint(_GENERATED_LINE_SOURCE_METADATA)
    op.create_table(
        _DECISION_TABLE,
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("forecast_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("cost_code_id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("source_type", sa.String(length=24), nullable=False),
        sa.Column("source_reference_type", sa.String(length=64), nullable=False),
        sa.Column("source_reference_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("source_amount", sa.Numeric(19, 4, asdecimal=True), nullable=False),
        sa.Column("included_amount", sa.Numeric(19, 4, asdecimal=True), nullable=False),
        sa.Column("excluded_amount", sa.Numeric(19, 4, asdecimal=True), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("source_snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "action IN ('included', 'offset', 'excluded')",
            name="ck_pf_forecast_decisions_action",
        ),
        sa.CheckConstraint(
            "reason IN ('remaining_plan', 'open_commitment', 'posted_actual_offset', "
            "'actual_credit', 'reversed_actual', 'manual_override', "
            "'risk_contingency', 'no_remaining_amount', 'closed_or_cancelled', "
            "'after_as_of')",
            name="ck_pf_forecast_decisions_reason",
        ),
        sa.CheckConstraint(
            "source_type IN ('remaining_plan', 'open_commitment', 'risk', "
            "'manual_estimate', 'posted_actual')",
            name="ck_pf_forecast_decisions_source_type",
        ),
        sa.CheckConstraint(
            "source_amount >= 0 AND included_amount >= 0 AND excluded_amount >= 0",
            name="ck_pf_forecast_decisions_amounts",
        ),
        sa.CheckConstraint(
            "included_amount + excluded_amount = source_amount",
            name="ck_pf_forecast_decisions_reconciled",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"],
            name="fk_pf_forecast_decisions_tenant", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "forecast_id"],
            [
                "project_finance_forecasts.tenant_id",
                "project_finance_forecasts.organization_id",
                "project_finance_forecasts.project_id",
                "project_finance_forecasts.id",
            ],
            name="fk_pf_forecast_decisions_scoped_forecast", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "cost_code_id"],
            [
                "project_finance_cost_codes.tenant_id",
                "project_finance_cost_codes.organization_id",
                "project_finance_cost_codes.id",
            ],
            name="fk_pf_forecast_decisions_scoped_cost_code", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["tasks.id"],
            name="fk_pf_forecast_decisions_task", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index(
        "idx_pf_forecast_decisions_scope", _DECISION_TABLE,
        ["tenant_id", "organization_id"],
    )
    op.create_index(
        "idx_pf_forecast_decisions_forecast", _DECISION_TABLE, ["forecast_id"]
    )
    op.create_index(
        "idx_pf_forecast_decisions_source", _DECISION_TABLE,
        ["source_reference_type", "source_reference_id"],
    )
    enable_tenant_organization_rls(op, bind, _DECISION_TABLE)


def downgrade() -> None:
    bind = op.get_bind()
    disable_tenant_organization_rls(op, bind, _DECISION_TABLE)
    op.drop_table(_DECISION_TABLE)
    _replace_line_source_constraint(_ORIGINAL_LINE_SOURCE_METADATA)
