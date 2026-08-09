"""add organization financial periods (Project Finance Phase C.1)

Revision ID: o2p3q4r5s6t7
Revises: n1o2p3q4r5s6
Create Date: 2026-08-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from src.infra.persistence.migrations.helpers.postgresql_rls import (
    disable_tenant_organization_rls,
    enable_tenant_organization_rls,
)


revision = "o2p3q4r5s6t7"
down_revision = "n1o2p3q4r5s6"
branch_labels = None
depends_on = None


_TABLE = "financial_periods"


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table(
        _TABLE,
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("period_number", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("closed_by", sa.String(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('open', 'closed', 'locked')",
            name="ck_financial_periods_status",
        ),
        sa.CheckConstraint(
            "length(code) >= 1 AND length(code) <= 32",
            name="ck_financial_periods_code_length",
        ),
        sa.CheckConstraint(
            "length(name) >= 1 AND length(name) <= 128",
            name="ck_financial_periods_name_length",
        ),
        sa.CheckConstraint(
            "(status = 'open' AND closed_by IS NULL AND closed_at IS NULL "
            "AND locked_by IS NULL AND locked_at IS NULL) OR "
            "(status = 'closed' AND closed_by IS NOT NULL AND closed_at IS NOT NULL "
            "AND locked_by IS NULL AND locked_at IS NULL) OR "
            "(status = 'locked' AND closed_by IS NOT NULL AND closed_at IS NOT NULL "
            "AND locked_by IS NOT NULL AND locked_at IS NOT NULL)",
            name="ck_financial_periods_lifecycle_metadata",
        ),
        sa.CheckConstraint(
            "end_date >= start_date",
            name="ck_financial_periods_date_range",
        ),
        sa.CheckConstraint(
            "fiscal_year >= 1 AND fiscal_year <= 9999",
            name="ck_financial_periods_fiscal_year",
        ),
        sa.CheckConstraint(
            "period_number >= 1 AND period_number <= 999",
            name="ck_financial_periods_period_number",
        ),
        sa.CheckConstraint("version >= 1", name="ck_financial_periods_version"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_financial_periods_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id"],
            ["organizations.tenant_id", "organizations.id"],
            name="fk_financial_periods_scoped_organization",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "organization_id",
            "id",
            name="uq_financial_periods_scoped_id",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "organization_id",
            "code",
            name="uq_financial_periods_scoped_code",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "organization_id",
            "fiscal_year",
            "period_number",
            name="uq_financial_periods_year_number",
        ),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index(
        "idx_financial_periods_scope",
        _TABLE,
        ["tenant_id", "organization_id"],
    )
    op.create_index(
        "idx_financial_periods_dates",
        _TABLE,
        ["tenant_id", "organization_id", "start_date", "end_date"],
    )
    op.create_index(
        "idx_financial_periods_status",
        _TABLE,
        ["tenant_id", "organization_id", "status"],
    )
    enable_tenant_organization_rls(op, bind, _TABLE)


def downgrade() -> None:
    bind = op.get_bind()
    disable_tenant_organization_rls(op, bind, _TABLE)
    op.drop_index("idx_financial_periods_status", table_name=_TABLE)
    op.drop_index("idx_financial_periods_dates", table_name=_TABLE)
    op.drop_index("idx_financial_periods_scope", table_name=_TABLE)
    op.drop_table(_TABLE)
