"""add runtime execution async controls

Revision ID: 6b7c8d9e1f2a
Revises: 5a6b7c8d9e1f
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa


revision = "6b7c8d9e1f2a"
down_revision = "5a6b7c8d9e1f"
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
    if not _has_table("runtime_executions"):
        return

    needed_columns = [
        ("output_file_name", sa.String(length=255), True, None),
        ("output_media_type", sa.String(length=255), True, None),
        ("output_metadata_json", sa.Text(), False, "{}"),
        ("cancellation_requested_at", sa.DateTime(), True, None),
        ("cancellation_requested_by_user_id", sa.String(), True, None),
        ("cancellation_requested_by_username", sa.String(length=128), True, None),
        ("retry_of_execution_id", sa.String(), True, None),
        ("attempt_number", sa.Integer(), False, "1"),
    ]

    missing = [name for name, _type, _nullable, _default in needed_columns if not _has_column("runtime_executions", name)]
    if missing:
        with op.batch_alter_table("runtime_executions") as batch:
            for name, column_type, nullable, default in needed_columns:
                if name not in missing:
                    continue
                kwargs = {"nullable": nullable}
                if default is not None:
                    kwargs["server_default"] = default
                batch.add_column(sa.Column(name, column_type, **kwargs))

    if _has_column("runtime_executions", "output_metadata_json"):
        op.execute(
            sa.text(
                "UPDATE runtime_executions "
                "SET output_metadata_json = '{}' "
                "WHERE output_metadata_json IS NULL OR output_metadata_json = ''"
            )
        )
    if _has_column("runtime_executions", "attempt_number"):
        op.execute(
            sa.text(
                "UPDATE runtime_executions "
                "SET attempt_number = 1 "
                "WHERE attempt_number IS NULL OR attempt_number < 1"
            )
        )

    if _has_column("runtime_executions", "retry_of_execution_id") and not _has_index(
        "runtime_executions",
        "idx_runtime_executions_retry_of",
    ):
        op.create_index(
            "idx_runtime_executions_retry_of",
            "runtime_executions",
            ["retry_of_execution_id"],
            unique=False,
        )


def downgrade() -> None:
    if not _has_table("runtime_executions"):
        return

    if _has_index("runtime_executions", "idx_runtime_executions_retry_of"):
        op.drop_index("idx_runtime_executions_retry_of", table_name="runtime_executions")

    removable = [
        "attempt_number",
        "retry_of_execution_id",
        "cancellation_requested_by_username",
        "cancellation_requested_by_user_id",
        "cancellation_requested_at",
        "output_metadata_json",
        "output_media_type",
        "output_file_name",
    ]
    existing = [name for name in removable if _has_column("runtime_executions", name)]
    if existing:
        with op.batch_alter_table("runtime_executions") as batch:
            for name in existing:
                batch.drop_column(name)
