"""harden approved-time labor posting provenance and references

Revision ID: f4b7c9d2e6a1
Revises: e9f2a5b8c4d1
Create Date: 2026-09-10

Historical rows remain explicitly incomplete. Their prior monetary facts are
never revalued or decorated with provenance that was not captured at posting.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4b7c9d2e6a1"
down_revision: Union[str, Sequence[str], None] = "e9f2a5b8c4d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ENVELOPE_COLUMNS = (
    "id",
    "tenant_id",
    "organization_id",
    "event_id",
    "event_type",
    "aggregate_type",
    "aggregate_id",
    "aggregate_version",
    "occurred_at",
    "envelope_json",
    "envelope_hash",
    "created_at",
)


def _restore_sqlite_labor_guards() -> None:
    if op.get_bind().dialect.name != "sqlite":
        return
    table = "project_approved_time_labor_postings"
    for operation in ("UPDATE", "DELETE"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable_{operation.lower()} "
            f"BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, "
            f"'{table} rows are immutable'); END"
        )


def _restore_sqlite_finance_inbox_guard() -> None:
    if op.get_bind().dialect.name != "sqlite":
        return
    table = "project_finance_inbox_receipts"
    comparisons = " OR ".join(
        f"OLD.{column} IS NOT NEW.{column}" for column in _ENVELOPE_COLUMNS
    )
    op.execute(
        f"CREATE TRIGGER trg_{table}_envelope_immutable BEFORE UPDATE ON {table} "
        f"WHEN {comparisons} BEGIN SELECT RAISE(ABORT, "
        f"'{table} envelope columns are immutable'); END"
    )


def upgrade() -> None:
    with op.batch_alter_table("service_principals", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_service_principals_scoped_id",
            ["tenant_id", "organization_id", "id"],
        )

    with op.batch_alter_table(
        "project_approved_time_labor_postings", schema=None
    ) as batch_op:
        batch_op.add_column(
            sa.Column("rate_base_amount", sa.Numeric(precision=19, scale=8), nullable=True)
        )
        batch_op.add_column(sa.Column("rate_origin", sa.String(length=32), nullable=True))
        batch_op.add_column(
            sa.Column(
                "rate_provenance_complete",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column("worker_service_principal_id", sa.String(), nullable=True)
        )
        batch_op.add_column(sa.Column("source_event_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("correlation_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("causation_id", sa.String(), nullable=True))
        batch_op.create_check_constraint(
            "ck_labor_rate_base_amount",
            "rate_base_amount IS NULL OR rate_base_amount >= 0",
        )
        batch_op.create_check_constraint(
            "ck_labor_complete_provenance",
            "rate_provenance_complete = false OR "
            "(rate_line_version IS NOT NULL AND rate_base_amount IS NOT NULL "
            "AND rate_origin IS NOT NULL AND worker_service_principal_id IS NOT NULL "
            "AND source_event_id IS NOT NULL)",
        )
        batch_op.create_foreign_key(
            "fk_labor_postings_scoped_resource",
            "resources",
            ["tenant_id", "organization_id", "resource_id"],
            ["tenant_id", "organization_id", "id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_labor_postings_project_task",
            "tasks",
            ["project_id", "task_id"],
            ["project_id", "id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_labor_postings_scoped_worker_principal",
            "service_principals",
            ["tenant_id", "organization_id", "worker_service_principal_id"],
            ["tenant_id", "organization_id", "id"],
            ondelete="RESTRICT",
        )
    _restore_sqlite_labor_guards()

    with op.batch_alter_table("project_finance_inbox_receipts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("source_project_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("source_resource_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("source_work_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("source_revision", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_pm_fin_inbox_scoped_source_project",
            "projects",
            ["tenant_id", "organization_id", "source_project_id"],
            ["tenant_id", "organization_id", "id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_pm_fin_inbox_scoped_source_resource",
            "resources",
            ["tenant_id", "organization_id", "source_resource_id"],
            ["tenant_id", "organization_id", "id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(
            "idx_pm_fin_inbox_approved_time_failures",
            [
                "tenant_id",
                "organization_id",
                "source_project_id",
                "event_type",
                "status",
                "updated_at",
            ],
            unique=False,
        )
    _restore_sqlite_finance_inbox_guard()


def downgrade() -> None:
    with op.batch_alter_table("project_finance_inbox_receipts", schema=None) as batch_op:
        batch_op.drop_index("idx_pm_fin_inbox_approved_time_failures")
        batch_op.drop_constraint(
            "fk_pm_fin_inbox_scoped_source_resource", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_pm_fin_inbox_scoped_source_project", type_="foreignkey"
        )
        batch_op.drop_column("source_revision")
        batch_op.drop_column("source_work_date")
        batch_op.drop_column("source_resource_id")
        batch_op.drop_column("source_project_id")
    _restore_sqlite_finance_inbox_guard()

    with op.batch_alter_table(
        "project_approved_time_labor_postings", schema=None
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_labor_postings_scoped_worker_principal", type_="foreignkey"
        )
        batch_op.drop_constraint("fk_labor_postings_project_task", type_="foreignkey")
        batch_op.drop_constraint(
            "fk_labor_postings_scoped_resource", type_="foreignkey"
        )
        batch_op.drop_constraint("ck_labor_complete_provenance", type_="check")
        batch_op.drop_constraint("ck_labor_rate_base_amount", type_="check")
        batch_op.drop_column("causation_id")
        batch_op.drop_column("correlation_id")
        batch_op.drop_column("source_event_id")
        batch_op.drop_column("worker_service_principal_id")
        batch_op.drop_column("rate_provenance_complete")
        batch_op.drop_column("rate_origin")
        batch_op.drop_column("rate_base_amount")
    _restore_sqlite_labor_guards()

    with op.batch_alter_table("service_principals", schema=None) as batch_op:
        batch_op.drop_constraint("uq_service_principals_scoped_id", type_="unique")
