"""R10A: correct Organization's persisted availability field.

`organizations.is_active` carried legacy single-organization mutual-exclusion
designation semantics (application code enforced "at most one organization
is_active=True per tenant"). The corrected domain model (P10A) treats
availability as an independent per-organization flag with no such invariant --
multiple organizations in the same tenant may be enabled simultaneously.
Renaming the column to `is_enabled` makes the persisted vocabulary match the
corrected meaning; existing values are preserved unchanged (a previously
`is_active=True` row becomes `is_enabled=True`, and vice versa -- P10A does
not reinterpret any row's stored value, only what the column is understood to
mean going forward).
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a1c7e93b4d02"
down_revision: str | Sequence[str] | None = "9f4c2d7b1a30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.drop_index("idx_organizations_active")
        batch_op.alter_column(
            "is_active",
            new_column_name="is_enabled",
            existing_type=sa.Boolean(),
            existing_server_default="1",
            existing_nullable=False,
        )
    # Separate batch: SQLite batch-mode rebuilds the table for the rename above, and gathering a
    # brand-new index against the renamed column in the SAME batch fails (the new_table reflection
    # used to gather indexes does not yet see the rename) -- creating it once the rename has been
    # flushed avoids that.
    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.create_index("idx_organizations_enabled", ["is_enabled"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.drop_index("idx_organizations_enabled")
        batch_op.alter_column(
            "is_enabled",
            new_column_name="is_active",
            existing_type=sa.Boolean(),
            existing_server_default="1",
            existing_nullable=False,
        )
    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.create_index("idx_organizations_active", ["is_active"], unique=False)
