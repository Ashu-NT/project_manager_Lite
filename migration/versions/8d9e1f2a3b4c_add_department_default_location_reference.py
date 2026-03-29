"""add department default location reference

Revision ID: 8d9e1f2a3b4c
Revises: 7c8d9e1f2a3b
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa


revision = "8d9e1f2a3b4c"
down_revision = "7c8d9e1f2a3b"
branch_labels = None
depends_on = None


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
    if _has_table("departments") and not _has_column("departments", "default_location_id"):
        with op.batch_alter_table("departments") as batch:
            batch.add_column(
                sa.Column(
                    "default_location_id",
                    sa.String(),
                    sa.ForeignKey("maintenance_locations.id", ondelete="SET NULL"),
                    nullable=True,
                )
            )

    if _has_table("departments") and not _has_index("departments", "idx_departments_default_location"):
        op.create_index(
            "idx_departments_default_location",
            "departments",
            ["default_location_id"],
            unique=False,
        )


def downgrade() -> None:
    if _has_table("departments") and _has_index("departments", "idx_departments_default_location"):
        op.drop_index("idx_departments_default_location", table_name="departments")

    if _has_table("departments") and _has_column("departments", "default_location_id"):
        with op.batch_alter_table("departments") as batch:
            batch.drop_column("default_location_id")
