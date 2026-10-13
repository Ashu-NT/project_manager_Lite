"""Employee lifecycle becomes a `status` string column ("active"/
"inactive") -- the sole source of truth -- replacing the `is_active`
boolean. Never both at once: this migration backfills `status` from the
existing `is_active` value, then drops `is_active` outright in the same
pass (no dual-write period at the schema level; the application layer was
updated in the same change so there is no window where both must be kept
in sync).

Revision ID: d1e8c4a3f976
Revises: c9a5f2d8b647
Create Date: 2026-09-30 00:00:03.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd1e8c4a3f976'
down_revision: str | Sequence[str] | None = 'c9a5f2d8b647'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "employees"


def upgrade() -> None:
    connection = op.get_bind()

    op.add_column(_TABLE, sa.Column("status", sa.String(length=16), nullable=True))
    connection.execute(
        sa.text(
            "UPDATE employees SET status = CASE WHEN is_active THEN 'active' ELSE 'inactive' END"
        )
    )

    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=16),
            nullable=False,
            server_default="active",
        )
        batch_op.drop_index("idx_employees_active")
        batch_op.drop_column("is_active")

    op.create_index("idx_employees_status", _TABLE, ["status"], unique=False)


def downgrade() -> None:
    connection = op.get_bind()

    op.add_column(
        _TABLE,
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="1"),
    )
    connection.execute(
        sa.text("UPDATE employees SET is_active = CASE WHEN status = 'active' THEN 1 ELSE 0 END")
    )

    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        batch_op.alter_column(
            "is_active",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default="1",
        )
        batch_op.drop_index("idx_employees_status")
        batch_op.drop_column("status")

    op.create_index("idx_employees_active", _TABLE, ["is_active"], unique=False)
