"""add employee directory and resource employee links

Revision ID: 9f1a2c6b4e11
Revises: d4c9e2a17f6b
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa


revision = "9f1a2c6b4e11"
down_revision = "d4c9e2a17f6b"
branch_labels = None
depends_on = None

_EMPLOYMENT_TYPE = sa.Enum("FULL_TIME", "PART_TIME", "TEMPORARY", name="employmenttype")
_WORKER_TYPE = sa.Enum("EMPLOYEE", "EXTERNAL", name="workertype")
_RESOURCES_EMPLOYEE_FK = "fk_resources_employee_id_employees"


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
    if not _has_table("employees"):
        op.create_table(
            "employees",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("employee_code", sa.String(length=64), nullable=False),
            sa.Column("full_name", sa.String(length=256), nullable=False),
            sa.Column("department", sa.String(length=256), nullable=True),
            sa.Column("title", sa.String(length=256), nullable=True),
            sa.Column(
                "employment_type",
                _EMPLOYMENT_TYPE,
                nullable=False,
                server_default="FULL_TIME",
            ),
            sa.Column("email", sa.String(length=256), nullable=True),
            sa.Column("phone", sa.String(length=64), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("employee_code"),
        )

    if not _has_index("employees", "idx_employees_code"):
        op.create_index("idx_employees_code", "employees", ["employee_code"], unique=True)
    if not _has_index("employees", "idx_employees_active"):
        op.create_index("idx_employees_active", "employees", ["is_active"], unique=False)

    needs_worker_type = not _has_column("resources", "worker_type")
    needs_employee_id = not _has_column("resources", "employee_id")
    if needs_worker_type or needs_employee_id:
        with op.batch_alter_table("resources") as batch:
            if needs_worker_type:
                batch.add_column(
                    sa.Column(
                        "worker_type",
                        _WORKER_TYPE,
                        nullable=False,
                        server_default="EXTERNAL",
                    )
                )
            if needs_employee_id:
                batch.add_column(
                    sa.Column(
                        "employee_id",
                        sa.String(),
                        nullable=True,
                    )
                )

    if not _has_fk("resources", _RESOURCES_EMPLOYEE_FK):
        with op.batch_alter_table("resources") as batch:
            batch.create_foreign_key(
                _RESOURCES_EMPLOYEE_FK,
                "employees",
                ["employee_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if not _has_index("resources", "idx_resources_employee"):
        op.create_index("idx_resources_employee", "resources", ["employee_id"], unique=False)


def downgrade() -> None:
    if _has_index("resources", "idx_resources_employee"):
        op.drop_index("idx_resources_employee", table_name="resources")

    if _has_table("resources"):
        has_employee_id = _has_column("resources", "employee_id")
        has_worker_type = _has_column("resources", "worker_type")
        has_fk = _has_fk("resources", _RESOURCES_EMPLOYEE_FK)
        if has_employee_id or has_worker_type or has_fk:
            with op.batch_alter_table("resources") as batch:
                if has_fk:
                    batch.drop_constraint(_RESOURCES_EMPLOYEE_FK, type_="foreignkey")
                if has_employee_id:
                    batch.drop_column("employee_id")
                if has_worker_type:
                    batch.drop_column("worker_type")

    if _has_index("employees", "idx_employees_active"):
        op.drop_index("idx_employees_active", table_name="employees")
    if _has_index("employees", "idx_employees_code"):
        op.drop_index("idx_employees_code", table_name="employees")
    if _has_table("employees"):
        op.drop_table("employees")
