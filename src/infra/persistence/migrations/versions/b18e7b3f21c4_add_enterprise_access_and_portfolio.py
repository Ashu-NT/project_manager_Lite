"""add enterprise access and portfolio tables

Revision ID: b18e7b3f21c4
Revises: 8b0f6c4e3d29
Create Date: 2026-03-13
"""

from alembic import op
import sqlalchemy as sa


revision = "b18e7b3f21c4"
down_revision = "8b0f6c4e3d29"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column(
                "failed_login_attempts",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch.add_column(sa.Column("locked_until", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("last_login_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("session_expires_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("password_changed_at", sa.DateTime(), nullable=True))
        batch.add_column(
            sa.Column(
                "must_change_password",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )

    op.create_table(
        "project_memberships",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("scope_role", sa.String(length=64), nullable=False, server_default="viewer"),
        sa.Column("permission_codes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="ux_project_memberships_project_user"),
    )
    op.create_index("idx_project_memberships_project", "project_memberships", ["project_id"])
    op.create_index("idx_project_memberships_user", "project_memberships", ["user_id"])

    op.create_table(
        "portfolio_intake_items",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("sponsor_name", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("requested_budget", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column(
            "requested_capacity_percent",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.0"),
        ),
        sa.Column("target_start_date", sa.Date(), nullable=True),
        sa.Column("strategic_score", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("value_score", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("urgency_score", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("risk_score", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PROPOSED"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_portfolio_intake_status", "portfolio_intake_items", ["status"])
    op.create_index("idx_portfolio_intake_updated", "portfolio_intake_items", ["updated_at"])

    op.create_table(
        "portfolio_scenarios",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("budget_limit", sa.Float(), nullable=True),
        sa.Column("capacity_limit_percent", sa.Float(), nullable=True),
        sa.Column("project_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("intake_item_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_portfolio_scenarios_updated", "portfolio_scenarios", ["updated_at"])


def downgrade() -> None:
    op.drop_index("idx_portfolio_scenarios_updated", table_name="portfolio_scenarios")
    op.drop_table("portfolio_scenarios")

    op.drop_index("idx_portfolio_intake_updated", table_name="portfolio_intake_items")
    op.drop_index("idx_portfolio_intake_status", table_name="portfolio_intake_items")
    op.drop_table("portfolio_intake_items")

    op.drop_index("idx_project_memberships_user", table_name="project_memberships")
    op.drop_index("idx_project_memberships_project", table_name="project_memberships")
    op.drop_table("project_memberships")

    with op.batch_alter_table("users") as batch:
        batch.drop_column("must_change_password")
        batch.drop_column("password_changed_at")
        batch.drop_column("session_expires_at")
        batch.drop_column("last_login_at")
        batch.drop_column("locked_until")
        batch.drop_column("failed_login_attempts")
