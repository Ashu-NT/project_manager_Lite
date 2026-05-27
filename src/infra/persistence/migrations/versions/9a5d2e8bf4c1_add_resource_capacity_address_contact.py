"""add resource capacity, address, and contact

Revision ID: 9a5d2e8bf4c1
Revises: 2c7fb73e21aa
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa


revision = "9a5d2e8bf4c1"
down_revision = "2c7fb73e21aa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("resources") as batch:
        batch.add_column(
            sa.Column(
                "capacity_percent",
                sa.Float(),
                nullable=False,
                server_default=sa.text("100.0"),
            )
        )
        batch.add_column(sa.Column("address", sa.String(), nullable=True))
        batch.add_column(sa.Column("contact", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("resources") as batch:
        batch.drop_column("contact")
        batch.drop_column("address")
        batch.drop_column("capacity_percent")
