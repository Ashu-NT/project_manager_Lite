"""add employee and time entry shared master references

Revision ID: b3c4d5e6f7a8
Revises: ae4c7b1d9f20
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa


revision = "b3c4d5e6f7a8"
down_revision = "ae4c7b1d9f20"
branch_labels = None
depends_on = None

_EMPLOYEES_DEPARTMENT_FK = "fk_employees_department_id_departments"
_EMPLOYEES_SITE_FK = "fk_employees_site_id_sites"
_TIME_ENTRIES_DEPARTMENT_FK = "fk_time_entries_department_id_departments"
_TIME_ENTRIES_SITE_FK = "fk_time_entries_site_id_sites"


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
    if _has_table("employees"):
        with op.batch_alter_table("employees") as batch:
            if not _has_column("employees", "department_id"):
                batch.add_column(sa.Column("department_id", sa.String(), nullable=True))
            if not _has_column("employees", "site_id"):
                batch.add_column(sa.Column("site_id", sa.String(), nullable=True))
        if not _has_fk("employees", _EMPLOYEES_DEPARTMENT_FK):
            with op.batch_alter_table("employees") as batch:
                batch.create_foreign_key(
                    _EMPLOYEES_DEPARTMENT_FK,
                    "departments",
                    ["department_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
        if not _has_fk("employees", _EMPLOYEES_SITE_FK):
            with op.batch_alter_table("employees") as batch:
                batch.create_foreign_key(
                    _EMPLOYEES_SITE_FK,
                    "sites",
                    ["site_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
        if not _has_index("employees", "idx_employees_department"):
            op.create_index("idx_employees_department", "employees", ["department_id"], unique=False)
        if not _has_index("employees", "idx_employees_site"):
            op.create_index("idx_employees_site", "employees", ["site_id"], unique=False)

    if _has_table("time_entries"):
        with op.batch_alter_table("time_entries") as batch:
            if not _has_column("time_entries", "department_id"):
                batch.add_column(sa.Column("department_id", sa.String(), nullable=True))
            if not _has_column("time_entries", "site_id"):
                batch.add_column(sa.Column("site_id", sa.String(), nullable=True))
        if not _has_fk("time_entries", _TIME_ENTRIES_DEPARTMENT_FK):
            with op.batch_alter_table("time_entries") as batch:
                batch.create_foreign_key(
                    _TIME_ENTRIES_DEPARTMENT_FK,
                    "departments",
                    ["department_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
        if not _has_fk("time_entries", _TIME_ENTRIES_SITE_FK):
            with op.batch_alter_table("time_entries") as batch:
                batch.create_foreign_key(
                    _TIME_ENTRIES_SITE_FK,
                    "sites",
                    ["site_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
        if not _has_index("time_entries", "idx_time_entries_department"):
            op.create_index("idx_time_entries_department", "time_entries", ["department_id"], unique=False)
        if not _has_index("time_entries", "idx_time_entries_site"):
            op.create_index("idx_time_entries_site", "time_entries", ["site_id"], unique=False)


def downgrade() -> None:
    if _has_index("time_entries", "idx_time_entries_site"):
        op.drop_index("idx_time_entries_site", table_name="time_entries")
    if _has_index("time_entries", "idx_time_entries_department"):
        op.drop_index("idx_time_entries_department", table_name="time_entries")
    if _has_table("time_entries"):
        with op.batch_alter_table("time_entries") as batch:
            if _has_fk("time_entries", _TIME_ENTRIES_SITE_FK):
                batch.drop_constraint(_TIME_ENTRIES_SITE_FK, type_="foreignkey")
            if _has_fk("time_entries", _TIME_ENTRIES_DEPARTMENT_FK):
                batch.drop_constraint(_TIME_ENTRIES_DEPARTMENT_FK, type_="foreignkey")
            if _has_column("time_entries", "site_id"):
                batch.drop_column("site_id")
            if _has_column("time_entries", "department_id"):
                batch.drop_column("department_id")

    if _has_index("employees", "idx_employees_site"):
        op.drop_index("idx_employees_site", table_name="employees")
    if _has_index("employees", "idx_employees_department"):
        op.drop_index("idx_employees_department", table_name="employees")
    if _has_table("employees"):
        with op.batch_alter_table("employees") as batch:
            if _has_fk("employees", _EMPLOYEES_SITE_FK):
                batch.drop_constraint(_EMPLOYEES_SITE_FK, type_="foreignkey")
            if _has_fk("employees", _EMPLOYEES_DEPARTMENT_FK):
                batch.drop_constraint(_EMPLOYEES_DEPARTMENT_FK, type_="foreignkey")
            if _has_column("employees", "site_id"):
                batch.drop_column("site_id")
            if _has_column("employees", "department_id"):
                batch.drop_column("department_id")
