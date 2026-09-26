"""Enforce reservation line ownership within its scoped preparation.

Revision ID: e7b2a9c4f613
Revises: d4f8b3e6a917
"""

from alembic import op

revision = "e7b2a9c4f613"
down_revision = "d4f8b3e6a917"
branch_labels = None
depends_on = None

_LINES = "project_billing_preparation_lines"
_LOCKS = "project_billing_source_locks"
_SCOPE = ["tenant_id", "organization_id", "project_id", "preparation_id"]


def upgrade() -> None:
    with op.batch_alter_table(_LINES) as batch:
        batch.create_unique_constraint("uq_billing_lines_scoped_preparation_id", [*_SCOPE, "id"])
    with op.batch_alter_table(_LOCKS) as batch:
        batch.drop_constraint("fk_billing_locks_line", type_="foreignkey")
        batch.create_foreign_key(
            "fk_billing_locks_scoped_line", _LINES,
            [*_SCOPE, "preparation_line_id"], [*_SCOPE, "id"], ondelete="CASCADE",
        )


def downgrade() -> None:
    with op.batch_alter_table(_LOCKS) as batch:
        batch.drop_constraint("fk_billing_locks_scoped_line", type_="foreignkey")
        batch.create_foreign_key(
            "fk_billing_locks_line", _LINES, ["preparation_line_id"], ["id"], ondelete="CASCADE",
        )
    with op.batch_alter_table(_LINES) as batch:
        batch.drop_constraint("uq_billing_lines_scoped_preparation_id", type_="unique")
