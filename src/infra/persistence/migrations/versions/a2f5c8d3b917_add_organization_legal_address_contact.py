"""Add Organization legal identity, registered address, and contact fields.

Revision ID: a2f5c8d3b917
Revises: c5a9e7d1b342
Create Date: 2026-09-15

All new columns are non-nullable strings with a "" server default so
existing organization rows remain valid without fabricating placeholder
business data. No new indexes: these are free-text profile fields, not
lookup/filter keys.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a2f5c8d3b917"
down_revision: Union[str, Sequence[str], None] = "c5a9e7d1b342"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "organizations"
_COLUMNS = (
    ("legal_name", sa.String(length=256)),
    ("registration_number", sa.String(length=128)),
    ("tax_id", sa.String(length=64)),
    ("address_line_1", sa.String(length=256)),
    ("address_line_2", sa.String(length=256)),
    ("postal_code", sa.String(length=32)),
    ("city", sa.String(length=128)),
    ("state_region", sa.String(length=128)),
    ("country_code", sa.String(length=8)),
    ("email", sa.String(length=256)),
    ("phone", sa.String(length=64)),
    ("website", sa.String(length=256)),
)


def upgrade() -> None:
    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        for name, col_type in _COLUMNS:
            batch_op.add_column(
                sa.Column(name, col_type, nullable=False, server_default="")
            )


def downgrade() -> None:
    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        for name, _col_type in reversed(_COLUMNS):
            batch_op.drop_column(name)
