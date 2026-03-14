"""add portfolio scoring templates

Revision ID: b7f9c2d4e6a1
Revises: ea7b2d91c4f3
Create Date: 2026-03-14
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "b7f9c2d4e6a1"
down_revision = "ea7b2d91c4f3"
branch_labels = None
depends_on = None

DEFAULT_TEMPLATE_ID = "portfolio-template-balanced-pmo"


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(column["name"] == column_name for column in _inspector().get_columns(table_name))


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(index["name"] == index_name for index in _inspector().get_indexes(table_name))


def upgrade() -> None:
    if not _has_table("portfolio_scoring_templates"):
        op.create_table(
            "portfolio_scoring_templates",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False, server_default=""),
            sa.Column("strategic_weight", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("value_weight", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("urgency_weight", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("risk_weight", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_index("portfolio_scoring_templates", "idx_portfolio_scoring_active"):
        op.create_index(
            "idx_portfolio_scoring_active",
            "portfolio_scoring_templates",
            ["is_active"],
            unique=False,
        )
    if not _has_index("portfolio_scoring_templates", "idx_portfolio_scoring_updated"):
        op.create_index(
            "idx_portfolio_scoring_updated",
            "portfolio_scoring_templates",
            ["updated_at"],
            unique=False,
        )

    timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
    bind = op.get_bind()
    existing_template = bind.execute(
        sa.text("SELECT id FROM portfolio_scoring_templates WHERE id = :template_id"),
        {"template_id": DEFAULT_TEMPLATE_ID},
    ).scalar()
    if not existing_template:
        bind.execute(
            sa.text(
                """
                INSERT INTO portfolio_scoring_templates (
                    id,
                    name,
                    summary,
                    strategic_weight,
                    value_weight,
                    urgency_weight,
                    risk_weight,
                    is_active,
                    created_at,
                    updated_at
                )
                VALUES (
                    :id,
                    :name,
                    :summary,
                    :strategic_weight,
                    :value_weight,
                    :urgency_weight,
                    :risk_weight,
                    :is_active,
                    :created_at,
                    :updated_at
                )
                """
            ),
            {
                "id": DEFAULT_TEMPLATE_ID,
                "name": "Balanced PMO",
                "summary": "Balanced template for strategic fit, value, urgency, and delivery risk.",
                "strategic_weight": 3,
                "value_weight": 2,
                "urgency_weight": 2,
                "risk_weight": 1,
                "is_active": True,
                "created_at": timestamp,
                "updated_at": timestamp,
            },
        )

    with op.batch_alter_table("portfolio_intake_items") as batch:
        if not _has_column("portfolio_intake_items", "scoring_template_id"):
            batch.add_column(
                sa.Column(
                    "scoring_template_id",
                    sa.String(length=64),
                    nullable=False,
                    server_default="",
                )
            )
        if not _has_column("portfolio_intake_items", "scoring_template_name"):
            batch.add_column(
                sa.Column(
                    "scoring_template_name",
                    sa.String(length=256),
                    nullable=False,
                    server_default="Balanced PMO",
                )
            )
        if not _has_column("portfolio_intake_items", "strategic_weight"):
            batch.add_column(
                sa.Column("strategic_weight", sa.Integer(), nullable=False, server_default="3")
            )
        if not _has_column("portfolio_intake_items", "value_weight"):
            batch.add_column(
                sa.Column("value_weight", sa.Integer(), nullable=False, server_default="2")
            )
        if not _has_column("portfolio_intake_items", "urgency_weight"):
            batch.add_column(
                sa.Column("urgency_weight", sa.Integer(), nullable=False, server_default="2")
            )
        if not _has_column("portfolio_intake_items", "risk_weight"):
            batch.add_column(
                sa.Column("risk_weight", sa.Integer(), nullable=False, server_default="1")
            )

    if not _has_index("portfolio_intake_items", "idx_portfolio_intake_template"):
        op.create_index(
            "idx_portfolio_intake_template",
            "portfolio_intake_items",
            ["scoring_template_id"],
            unique=False,
        )

    bind.execute(
        sa.text(
            """
            UPDATE portfolio_intake_items
            SET scoring_template_id = :template_id
            WHERE scoring_template_id IS NULL OR scoring_template_id = ''
            """
        ),
        {"template_id": DEFAULT_TEMPLATE_ID},
    )


def downgrade() -> None:
    if _has_index("portfolio_intake_items", "idx_portfolio_intake_template"):
        op.drop_index("idx_portfolio_intake_template", table_name="portfolio_intake_items")

    if _has_table("portfolio_intake_items"):
        with op.batch_alter_table("portfolio_intake_items") as batch:
            if _has_column("portfolio_intake_items", "risk_weight"):
                batch.drop_column("risk_weight")
            if _has_column("portfolio_intake_items", "urgency_weight"):
                batch.drop_column("urgency_weight")
            if _has_column("portfolio_intake_items", "value_weight"):
                batch.drop_column("value_weight")
            if _has_column("portfolio_intake_items", "strategic_weight"):
                batch.drop_column("strategic_weight")
            if _has_column("portfolio_intake_items", "scoring_template_name"):
                batch.drop_column("scoring_template_name")
            if _has_column("portfolio_intake_items", "scoring_template_id"):
                batch.drop_column("scoring_template_id")

    if _has_index("portfolio_scoring_templates", "idx_portfolio_scoring_updated"):
        op.drop_index("idx_portfolio_scoring_updated", table_name="portfolio_scoring_templates")
    if _has_index("portfolio_scoring_templates", "idx_portfolio_scoring_active"):
        op.drop_index("idx_portfolio_scoring_active", table_name="portfolio_scoring_templates")
    if _has_table("portfolio_scoring_templates"):
        op.drop_table("portfolio_scoring_templates")
