"""Allow released Billing source locks to retain history without blocking reuse.

Revision ID: c5a9e7d1b342
Revises: b7d2e4f9a6c1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c5a9e7d1b342"
down_revision: str | Sequence[str] | None = "b7d2e4f9a6c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "project_billing_source_locks"
_COLUMNS = ("tenant_id", "organization_id", "source_type", "source_id")
_ACTIVE = sa.text("status != 'released'")


def upgrade() -> None:
    with op.batch_alter_table(_TABLE) as batch_op:
        batch_op.drop_constraint("uq_billing_locks_source", type_="unique")
    op.create_index(
        "uq_billing_locks_active_source",
        _TABLE,
        _COLUMNS,
        unique=True,
        postgresql_where=_ACTIVE,
        sqlite_where=_ACTIVE,
    )
    correction_active = sa.text(
        "correction_of_preparation_id IS NOT NULL "
        "AND status NOT IN ('rejected', 'cancelled')"
    )
    op.create_index(
        "uq_billing_preparations_active_correction",
        "project_billing_preparations",
        ("tenant_id", "organization_id", "project_id", "correction_of_preparation_id"),
        unique=True,
        postgresql_where=correction_active,
        sqlite_where=correction_active,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_billing_preparations_active_correction",
        table_name="project_billing_preparations",
    )
    op.drop_index("uq_billing_locks_active_source", table_name=_TABLE)
    with op.batch_alter_table(_TABLE) as batch_op:
        batch_op.create_unique_constraint("uq_billing_locks_source", _COLUMNS)
