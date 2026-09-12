"""harden Procurement receipt source identity

Revision ID: b7d2e4f9a6c1
Revises: f4b7c9d2e6a1
Create Date: 2026-09-11

The current neutral Procurement contract publishes immutable posted receipt
facts but no correction/reversal lineage. One semantic receipt line therefore
maps to one Finance Actual until an explicit correction contract is introduced.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7d2e4f9a6c1"
down_revision: Union[str, Sequence[str], None] = "f4b7c9d2e6a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_INDEX = "uq_project_cost_entries_procurement_receipt_source"
_TABLE = "project_cost_entries"
_COLUMNS = (
    "tenant_id",
    "organization_id",
    "source_module",
    "source_type",
    "source_id",
    "source_line_id",
    "posting_purpose",
)
_WHERE = (
    "source_module = 'inventory_procurement' "
    "AND source_type = 'receipt_line' "
    "AND posting_purpose = 'receipt_accrual'"
)


def upgrade() -> None:
    op.create_index(
        _INDEX,
        _TABLE,
        list(_COLUMNS),
        unique=True,
        postgresql_where=sa.text(_WHERE),
        sqlite_where=sa.text(_WHERE),
    )


def downgrade() -> None:
    op.drop_index(_INDEX, table_name=_TABLE)
