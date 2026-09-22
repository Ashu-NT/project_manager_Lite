"""Drop Site.is_active -- status is the ONE lifecycle source of truth.

Revision ID: c7f2a5d91b48
Revises: b54546fc740c
Create Date: 2026-09-22 22:10:00.000000

Site.status already exists and is already the value every current write path
populates (create_site/update_site/activate_site/deactivate_site/
archive_site). is_active becomes a computed domain property (status ==
"active"), never a second persisted source of truth -- pre-release, no dual
status/is_active source of truth is retained (see 5555a14faf88, which did the
same for Organization.is_enabled -> status).

Any row where status is somehow still NULL/empty is backfilled from
is_active before the column is dropped, so no row silently loses its
lifecycle state.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7f2a5d91b48'
down_revision: Union[str, Sequence[str], None] = 'b54546fc740c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "sites"


def upgrade() -> None:
    sites = sa.table(
        _TABLE,
        sa.column("is_active", sa.Boolean()),
        sa.column("status", sa.String()),
    )
    op.execute(
        sites.update()
        .where(sa.or_(sites.c.status.is_(None), sites.c.status == ""))
        .where(sites.c.is_active.is_(True))
        .values(status="active")
    )
    op.execute(
        sites.update()
        .where(sa.or_(sites.c.status.is_(None), sites.c.status == ""))
        .where(sites.c.is_active.is_(False))
        .values(status="inactive")
    )

    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        batch_op.drop_index("idx_sites_active")
        batch_op.drop_column("is_active")
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=64),
            nullable=False,
            server_default="active",
        )
        batch_op.create_index("idx_sites_status", ["organization_id", "status"])


def downgrade() -> None:
    # status pre-dates this migration (it is not created here) -- only
    # is_active is restored; status is left exactly as it is.
    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1")
        )

    sites = sa.table(
        _TABLE,
        sa.column("status", sa.String()),
        sa.column("is_active", sa.Boolean()),
    )
    op.execute(sites.update().where(sites.c.status == "active").values(is_active=True))
    op.execute(sites.update().where(sites.c.status != "active").values(is_active=False))

    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=64),
            nullable=True,
            server_default=None,
        )
        batch_op.drop_index("idx_sites_status")
        batch_op.create_index("idx_sites_active", ["organization_id", "is_active"])
