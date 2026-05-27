"""add shared time work allocation fields

Revision ID: 4e7f9a1c2d3b
Revises: 3c5d7e9f1a2b
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa


revision = "4e7f9a1c2d3b"
down_revision = "3c5d7e9f1a2b"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(column["name"] == column_name for column in _inspector().get_columns(table_name))


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(index["name"] == index_name for index in _inspector().get_indexes(table_name))


def upgrade() -> None:
    if not _has_table("time_entries"):
        return

    needs_work_allocation_id = not _has_column("time_entries", "work_allocation_id")
    needs_owner_label = not _has_column("time_entries", "owner_label")
    needs_scope_type = not _has_column("time_entries", "scope_type")
    needs_scope_id = not _has_column("time_entries", "scope_id")

    if needs_work_allocation_id or needs_owner_label or needs_scope_type or needs_scope_id:
        with op.batch_alter_table("time_entries") as batch:
            if needs_work_allocation_id:
                batch.add_column(sa.Column("work_allocation_id", sa.String(), nullable=True))
            if needs_owner_label:
                batch.add_column(sa.Column("owner_label", sa.String(length=256), nullable=True))
            if needs_scope_type:
                batch.add_column(sa.Column("scope_type", sa.String(length=64), nullable=True))
            if needs_scope_id:
                batch.add_column(sa.Column("scope_id", sa.String(), nullable=True))

    with op.batch_alter_table("time_entries") as batch:
        if _has_column("time_entries", "assignment_id"):
            batch.alter_column("assignment_id", existing_type=sa.String(), nullable=True)
        if _has_column("time_entries", "owner_type"):
            batch.alter_column(
                "owner_type",
                existing_type=sa.String(length=64),
                nullable=False,
                server_default="work_allocation",
            )

    bind = op.get_bind()
    if _has_column("time_entries", "work_allocation_id"):
        bind.execute(
            sa.text(
                "UPDATE time_entries "
                "SET work_allocation_id = assignment_id "
                "WHERE work_allocation_id IS NULL OR work_allocation_id = ''"
            )
        )
        bind.execute(
            sa.text(
                "UPDATE time_entries "
                "SET work_allocation_id = owner_id "
                "WHERE (work_allocation_id IS NULL OR work_allocation_id = '') "
                "AND owner_id IS NOT NULL AND owner_id <> ''"
            )
        )

    if _has_column("time_entries", "owner_type"):
        bind.execute(
            sa.text(
                "UPDATE time_entries "
                "SET owner_type = 'task_assignment' "
                "WHERE assignment_id IS NOT NULL "
                "AND assignment_id <> '' "
                "AND (owner_type IS NULL OR owner_type = '')"
            )
        )
        bind.execute(
            sa.text(
                "UPDATE time_entries "
                "SET owner_type = 'work_allocation' "
                "WHERE owner_type IS NULL OR owner_type = ''"
            )
        )

    if _has_column("time_entries", "work_allocation_id"):
        with op.batch_alter_table("time_entries") as batch:
            batch.alter_column("work_allocation_id", existing_type=sa.String(), nullable=False)

    if not _has_index("time_entries", "idx_time_entries_work_allocation"):
        op.create_index("idx_time_entries_work_allocation", "time_entries", ["work_allocation_id"], unique=False)
    if (
        _has_column("time_entries", "scope_type")
        and _has_column("time_entries", "scope_id")
        and not _has_index("time_entries", "idx_time_entries_scope")
    ):
        op.create_index("idx_time_entries_scope", "time_entries", ["scope_type", "scope_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table("time_entries") and _has_column("time_entries", "assignment_id") and _has_column("time_entries", "work_allocation_id"):
        bind.execute(
            sa.text(
                "UPDATE time_entries "
                "SET assignment_id = work_allocation_id "
                "WHERE (assignment_id IS NULL OR assignment_id = '') "
                "AND EXISTS ("
                "    SELECT 1 FROM task_assignments "
                "    WHERE task_assignments.id = time_entries.work_allocation_id"
                ")"
            )
        )

    if _has_index("time_entries", "idx_time_entries_scope"):
        op.drop_index("idx_time_entries_scope", table_name="time_entries")
    if _has_index("time_entries", "idx_time_entries_work_allocation"):
        op.drop_index("idx_time_entries_work_allocation", table_name="time_entries")

    if _has_table("time_entries"):
        has_work_allocation_id = _has_column("time_entries", "work_allocation_id")
        has_owner_label = _has_column("time_entries", "owner_label")
        has_scope_type = _has_column("time_entries", "scope_type")
        has_scope_id = _has_column("time_entries", "scope_id")
        with op.batch_alter_table("time_entries") as batch:
            if _has_column("time_entries", "owner_type"):
                batch.alter_column(
                    "owner_type",
                    existing_type=sa.String(length=64),
                    nullable=False,
                    server_default="task_assignment",
                )
            if has_scope_id:
                batch.drop_column("scope_id")
            if has_scope_type:
                batch.drop_column("scope_type")
            if has_owner_label:
                batch.drop_column("owner_label")
            if has_work_allocation_id:
                batch.drop_column("work_allocation_id")

        null_assignment_count = bind.execute(
            sa.text("SELECT COUNT(1) FROM time_entries WHERE assignment_id IS NULL OR assignment_id = ''")
        ).scalar_one()
        if null_assignment_count == 0 and _has_column("time_entries", "assignment_id"):
            with op.batch_alter_table("time_entries") as batch:
                batch.alter_column("assignment_id", existing_type=sa.String(), nullable=False)
