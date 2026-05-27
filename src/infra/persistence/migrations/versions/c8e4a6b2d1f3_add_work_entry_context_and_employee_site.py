"""add work entry context and employee site name

Revision ID: c8e4a6b2d1f3
Revises: a1d3f5c7e9b2
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa


revision = "c8e4a6b2d1f3"
down_revision = "a1d3f5c7e9b2"
branch_labels = None
depends_on = None

_TIME_ENTRIES_EMPLOYEE_FK = "fk_time_entries_employee_id_employees"


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


def _has_fk(table_name: str, constraint_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(fk.get("name") == constraint_name for fk in _inspector().get_foreign_keys(table_name))


def upgrade() -> None:
    if _has_table("employees") and not _has_column("employees", "site_name"):
        with op.batch_alter_table("employees") as batch:
            batch.add_column(sa.Column("site_name", sa.String(length=256), nullable=True))

    if not _has_table("time_entries"):
        return

    needs_owner_type = not _has_column("time_entries", "owner_type")
    needs_owner_id = not _has_column("time_entries", "owner_id")
    needs_employee_id = not _has_column("time_entries", "employee_id")
    needs_department_name = not _has_column("time_entries", "department_name")
    needs_site_name = not _has_column("time_entries", "site_name")
    if needs_owner_type or needs_owner_id or needs_employee_id or needs_department_name or needs_site_name:
        with op.batch_alter_table("time_entries") as batch:
            if needs_owner_type:
                batch.add_column(
                    sa.Column(
                        "owner_type",
                        sa.String(length=64),
                        nullable=False,
                        server_default="task_assignment",
                    )
                )
            if needs_owner_id:
                batch.add_column(sa.Column("owner_id", sa.String(), nullable=True))
            if needs_employee_id:
                batch.add_column(sa.Column("employee_id", sa.String(), nullable=True))
            if needs_department_name:
                batch.add_column(sa.Column("department_name", sa.String(length=256), nullable=True))
            if needs_site_name:
                batch.add_column(sa.Column("site_name", sa.String(length=256), nullable=True))

    bind = op.get_bind()
    if _has_column("time_entries", "owner_type"):
        bind.execute(
            sa.text(
                "UPDATE time_entries "
                "SET owner_type = 'task_assignment' "
                "WHERE owner_type IS NULL OR owner_type = ''"
            )
        )
    if _has_column("time_entries", "owner_id"):
        bind.execute(
            sa.text(
                "UPDATE time_entries "
                "SET owner_id = assignment_id "
                "WHERE owner_id IS NULL OR owner_id = ''"
            )
        )

    if _has_table("employees") and _has_column("time_entries", "employee_id") and not _has_fk("time_entries", _TIME_ENTRIES_EMPLOYEE_FK):
        with op.batch_alter_table("time_entries") as batch:
            batch.create_foreign_key(
                _TIME_ENTRIES_EMPLOYEE_FK,
                "employees",
                ["employee_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if _has_column("time_entries", "owner_type") and _has_column("time_entries", "owner_id") and not _has_index("time_entries", "idx_time_entries_owner"):
        op.create_index("idx_time_entries_owner", "time_entries", ["owner_type", "owner_id"], unique=False)
    if _has_column("time_entries", "employee_id") and not _has_index("time_entries", "idx_time_entries_employee"):
        op.create_index("idx_time_entries_employee", "time_entries", ["employee_id"], unique=False)


def downgrade() -> None:
    if _has_index("time_entries", "idx_time_entries_employee"):
        op.drop_index("idx_time_entries_employee", table_name="time_entries")
    if _has_index("time_entries", "idx_time_entries_owner"):
        op.drop_index("idx_time_entries_owner", table_name="time_entries")

    if _has_table("time_entries"):
        has_owner_type = _has_column("time_entries", "owner_type")
        has_owner_id = _has_column("time_entries", "owner_id")
        has_employee_id = _has_column("time_entries", "employee_id")
        has_department_name = _has_column("time_entries", "department_name")
        has_site_name = _has_column("time_entries", "site_name")
        has_fk = _has_fk("time_entries", _TIME_ENTRIES_EMPLOYEE_FK)
        if has_owner_type or has_owner_id or has_employee_id or has_department_name or has_site_name or has_fk:
            with op.batch_alter_table("time_entries") as batch:
                if has_fk:
                    batch.drop_constraint(_TIME_ENTRIES_EMPLOYEE_FK, type_="foreignkey")
                if has_site_name:
                    batch.drop_column("site_name")
                if has_department_name:
                    batch.drop_column("department_name")
                if has_employee_id:
                    batch.drop_column("employee_id")
                if has_owner_id:
                    batch.drop_column("owner_id")
                if has_owner_type:
                    batch.drop_column("owner_type")

    if _has_table("employees") and _has_column("employees", "site_name"):
        with op.batch_alter_table("employees") as batch:
            batch.drop_column("site_name")
