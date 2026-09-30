"""Enforce comment scope and same-task replies; redact stored mention previews."""

import sqlalchemy as sa
from alembic import op

from src.infra.persistence.migrations.helpers.postgresql_rls import (
    disable_parent_scoped_rls,
    enable_parent_scoped_rls,
)
from src.infra.persistence.migrations.helpers.rls_classification import PARENT_SCOPED_RLS_PREDICATES

revision = "a7b19c32d405"
down_revision = "d1e8c4a3f976"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    # Fresh baselines install manifest policies too; recreate deterministically.
    disable_parent_scoped_rls(op, bind, "task_comments")
    naming = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}
    fks = sa.inspect(bind).get_foreign_keys("task_comments")
    parent_fk = next(fk for fk in fks if fk["constrained_columns"] == ["parent_comment_id"])
    with op.batch_alter_table("task_comments", naming_convention=naming) as batch:
        batch.drop_constraint(parent_fk["name"] or "fk_task_comments_parent_comment_id_task_comments", type_="foreignkey")
        batch.create_unique_constraint("uq_task_comments_id_task", ["id", "task_id"])
        batch.create_foreign_key(
            "fk_task_comments_parent_task", "task_comments",
            ["parent_comment_id", "task_id"], ["id", "task_id"], ondelete="RESTRICT",
        )
    # Existing persisted previews cannot remain an alternate deleted-body reader.
    op.execute(sa.text(
        "UPDATE notifications SET body = 'Open the task discussion to view this mention if you still have access.' "
        "WHERE category = 'pm.comment.mentioned.v1'"
    ))
    enable_parent_scoped_rls(op, bind, "task_comments", predicate=PARENT_SCOPED_RLS_PREDICATES["task_comments"])


def downgrade():
    bind = op.get_bind()
    disable_parent_scoped_rls(op, bind, "task_comments")
    with op.batch_alter_table("task_comments") as batch:
        batch.drop_constraint("fk_task_comments_parent_task", type_="foreignkey")
        batch.drop_constraint("uq_task_comments_id_task", type_="unique")
        batch.create_foreign_key(
            "fk_task_comments_parent_comment_id_task_comments", "task_comments",
            ["parent_comment_id"], ["id"], ondelete="SET NULL",
        )
    # Redacted notification content is intentionally not reconstructed on downgrade.
