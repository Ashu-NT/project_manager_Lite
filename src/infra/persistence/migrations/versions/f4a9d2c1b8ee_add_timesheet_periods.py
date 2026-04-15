"""add timesheet periods

Revision ID: f4a9d2c1b8ee
Revises: c2b7f1ab61de
Create Date: 2026-03-11
"""

from alembic import op
import sqlalchemy as sa


revision = "f4a9d2c1b8ee"
down_revision = "c2b7f1ab61de"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "timesheet_periods",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("resource_id", sa.String(), sa.ForeignKey("resources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN"),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("submitted_by_user_id", sa.String(), nullable=True),
        sa.Column("submitted_by_username", sa.String(length=128), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("decided_by_user_id", sa.String(), nullable=True),
        sa.Column("decided_by_username", sa.String(length=128), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_timesheet_periods_resource", "timesheet_periods", ["resource_id"])
    op.create_index(
        "ux_timesheet_periods_resource_start",
        "timesheet_periods",
        ["resource_id", "period_start"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_timesheet_periods_resource_start", table_name="timesheet_periods")
    op.drop_index("idx_timesheet_periods_resource", table_name="timesheet_periods")
    op.drop_table("timesheet_periods")
