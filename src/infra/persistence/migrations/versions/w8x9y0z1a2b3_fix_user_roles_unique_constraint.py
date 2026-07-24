"""Fix user_roles unique constraint to include organization_id for org-scoped roles.

Revision ID: w8x9y0z1a2b3
Revises: v7w8x9y0z1a2
Create Date: 2026-06-17

The old constraint (user_id, role_id) prevents a user from holding the same role
at both global scope and org scope simultaneously.  The new constraint
(user_id, role_id, organization_id) allows that by treating NULL organization_id
as a distinct value via the partial-index workaround below — SQLite and most
engines treat two NULLs as distinct in a unique index.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "w8x9y0z1a2b3"
down_revision = "v7w8x9y0z1a2"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _constraint_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _table_exists(inspector, table_name):
        return set()
    return {uc["name"] for uc in inspector.get_unique_constraints(table_name)}


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if not _table_exists(inspector, "user_roles"):
        return

    existing = _constraint_names(inspector, "user_roles")

    with op.batch_alter_table("user_roles", recreate="always") as batch_op:
        if "ux_user_roles_user_role" in existing:
            batch_op.drop_constraint("ux_user_roles_user_role", type_="unique")
        if "ux_user_roles_user_role_org" not in existing:
            batch_op.create_unique_constraint(
                "ux_user_roles_user_role_org",
                ["user_id", "role_id", "organization_id"],
            )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if not _table_exists(inspector, "user_roles"):
        return

    existing = _constraint_names(inspector, "user_roles")

    with op.batch_alter_table("user_roles", recreate="always") as batch_op:
        if "ux_user_roles_user_role_org" in existing:
            batch_op.drop_constraint("ux_user_roles_user_role_org", type_="unique")
        if "ux_user_roles_user_role" not in existing:
            batch_op.create_unique_constraint(
                "ux_user_roles_user_role",
                ["user_id", "role_id"],
            )
