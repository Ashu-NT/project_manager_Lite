"""Key ephemeral task presence by User identity and enforce parent-scoped RLS."""

import sqlalchemy as sa
from alembic import op

from src.infra.persistence.migrations.helpers.postgresql_rls import (
    disable_parent_scoped_rls,
    enable_parent_scoped_rls,
)
from src.infra.persistence.migrations.helpers.rls_classification import (
    PARENT_SCOPED_RLS_PREDICATES,
    PARENT_SCOPED_RLS_WRITE_PREDICATES,
)

revision = "d3e7a91c4b52"
down_revision = "b1d7c2f4a96e"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    disable_parent_scoped_rls(op, bind, "task_presence")
    # Presence is ephemeral; old username-keyed rows cannot be authoritative.
    op.execute(sa.text("DELETE FROM task_presence"))
    with op.batch_alter_table("task_presence") as batch:
        batch.drop_constraint("ux_task_presence_task_username", type_="unique")
        batch.alter_column("user_id", existing_type=sa.String(), nullable=False)
        batch.create_foreign_key(
            "fk_task_presence_user_id_users", "users", ["user_id"], ["id"],
            ondelete="CASCADE",
        )
        batch.create_unique_constraint("ux_task_presence_task_user", ["task_id", "user_id"])
    enable_parent_scoped_rls(
        op, bind, "task_presence",
        predicate=PARENT_SCOPED_RLS_PREDICATES["task_presence"],
        write_predicate=PARENT_SCOPED_RLS_WRITE_PREDICATES["task_presence"],
    )


def downgrade():
    bind = op.get_bind()
    disable_parent_scoped_rls(op, bind, "task_presence")
    with op.batch_alter_table("task_presence") as batch:
        batch.drop_constraint("ux_task_presence_task_user", type_="unique")
        batch.drop_constraint("fk_task_presence_user_id_users", type_="foreignkey")
        batch.alter_column("user_id", existing_type=sa.String(), nullable=True)
        batch.create_unique_constraint("ux_task_presence_task_username", ["task_id", "username"])
