"""add portfolio project dependencies

Revision ID: f1e2d3c4b5a6
Revises: b7f9c2d4e6a1
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa


revision = "f1e2d3c4b5a6"
down_revision = "b7f9c2d4e6a1"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(index["name"] == index_name for index in _inspector().get_indexes(table_name))


def upgrade() -> None:
    if not _has_table("portfolio_project_dependencies"):
        op.create_table(
            "portfolio_project_dependencies",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("predecessor_project_id", sa.String(), nullable=False),
            sa.Column("successor_project_id", sa.String(), nullable=False),
            sa.Column("dependency_type", sa.String(length=8), nullable=False, server_default="FS"),
            sa.Column("summary", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["predecessor_project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["successor_project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "predecessor_project_id",
                "successor_project_id",
                name="ux_portfolio_project_dependencies_pair",
            ),
        )

    if not _has_index("portfolio_project_dependencies", "idx_portfolio_project_dependencies_predecessor"):
        op.create_index(
            "idx_portfolio_project_dependencies_predecessor",
            "portfolio_project_dependencies",
            ["predecessor_project_id"],
            unique=False,
        )

    if not _has_index("portfolio_project_dependencies", "idx_portfolio_project_dependencies_successor"):
        op.create_index(
            "idx_portfolio_project_dependencies_successor",
            "portfolio_project_dependencies",
            ["successor_project_id"],
            unique=False,
        )


def downgrade() -> None:
    if _has_index("portfolio_project_dependencies", "idx_portfolio_project_dependencies_successor"):
        op.drop_index(
            "idx_portfolio_project_dependencies_successor",
            table_name="portfolio_project_dependencies",
        )

    if _has_index("portfolio_project_dependencies", "idx_portfolio_project_dependencies_predecessor"):
        op.drop_index(
            "idx_portfolio_project_dependencies_predecessor",
            table_name="portfolio_project_dependencies",
        )

    if _has_table("portfolio_project_dependencies"):
        op.drop_table("portfolio_project_dependencies")
