"""Replace Organization.is_enabled with an explicit ACTIVE/INACTIVE/ARCHIVED
lifecycle status.

Revision ID: 5555a14faf88
Revises: e7b2a9c4f613
Create Date: 2026-09-22 06:31:48.139473

is_enabled=true -> 'active', is_enabled=false -> 'inactive'. No organization
row could previously represent 'archived', so none are backfilled into it.
is_enabled and its index are dropped outright -- pre-release, no dual
enabled/status source of truth is retained.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5555a14faf88'
down_revision: Union[str, Sequence[str], None] = 'e7b2a9c4f613'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "organizations"


def upgrade() -> None:
    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("status", sa.String(length=16), nullable=False, server_default="active")
        )

    organizations = sa.table(
        _TABLE,
        sa.column("is_enabled", sa.Boolean()),
        sa.column("status", sa.String()),
    )
    op.execute(organizations.update().where(organizations.c.is_enabled.is_(True)).values(status="active"))
    op.execute(organizations.update().where(organizations.c.is_enabled.is_(False)).values(status="inactive"))

    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        batch_op.drop_index("idx_organizations_enabled")
        batch_op.drop_column("is_enabled")
        batch_op.create_index("idx_organizations_status", ["status"])


def downgrade() -> None:
    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="1")
        )

    organizations = sa.table(
        _TABLE,
        sa.column("status", sa.String()),
        sa.column("is_enabled", sa.Boolean()),
    )
    op.execute(organizations.update().where(organizations.c.status != "active").values(is_enabled=False))

    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        batch_op.drop_index("idx_organizations_status")
        batch_op.drop_column("status")
        batch_op.create_index("idx_organizations_enabled", ["is_enabled"])
