"""add register entries

Revision ID: 8b0f6c4e3d29
Revises: f4a9d2c1b8ee
Create Date: 2026-03-11
"""

from alembic import op
import sqlalchemy as sa


revision = "8b0f6c4e3d29"
down_revision = "f4a9d2c1b8ee"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "register_entries",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entry_type", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="OPEN"),
        sa.Column("owner_name", sa.String(length=256), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("impact_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("response_plan", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("idx_register_entries_project", "register_entries", ["project_id"])
    op.create_index("idx_register_entries_type", "register_entries", ["entry_type"])
    op.create_index("idx_register_entries_status", "register_entries", ["status"])
    op.create_index("idx_register_entries_due", "register_entries", ["due_date"])


def downgrade() -> None:
    op.drop_index("idx_register_entries_due", table_name="register_entries")
    op.drop_index("idx_register_entries_status", table_name="register_entries")
    op.drop_index("idx_register_entries_type", table_name="register_entries")
    op.drop_index("idx_register_entries_project", table_name="register_entries")
    op.drop_table("register_entries")
