"""add inventory hardening fields and runtime tracking tables

Revision ID: 2d4e6f8a9b0c
Revises: 1b2c3d4e5f6a
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa


revision = "2d4e6f8a9b0c"
down_revision = "1b2c3d4e5f6a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "session_revision",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("auth_method", sa.String(length=64), nullable=False),
        sa.Column("device_label", sa.String(length=256), nullable=True),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("last_validated_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_auth_sessions_user", "auth_sessions", ["user_id"])
    op.create_index("idx_auth_sessions_expires", "auth_sessions", ["expires_at"])
    op.create_index("idx_auth_sessions_revoked", "auth_sessions", ["revoked_at"])

    op.create_table(
        "runtime_executions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("operation_type", sa.String(length=32), nullable=False),
        sa.Column("operation_key", sa.String(length=128), nullable=False),
        sa.Column("module_code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="RUNNING"),
        sa.Column("requested_by_user_id", sa.String(), nullable=True),
        sa.Column("requested_by_username", sa.String(length=128), nullable=True),
        sa.Column("input_path", sa.Text(), nullable=True),
        sa.Column("output_path", sa.Text(), nullable=True),
        sa.Column("created_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_runtime_executions_started", "runtime_executions", ["started_at"])
    op.create_index(
        "idx_runtime_executions_module_status",
        "runtime_executions",
        ["module_code", "status"],
    )

    with op.batch_alter_table("inventory_storerooms") as batch:
        batch.add_column(
            sa.Column(
                "requires_reservation_for_issue",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch.add_column(
            sa.Column(
                "requires_supplier_reference_for_receipt",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )

    with op.batch_alter_table("inventory_receipt_lines") as batch:
        batch.add_column(sa.Column("lot_number", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("serial_number", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("expiry_date", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("inventory_receipt_lines") as batch:
        batch.drop_column("expiry_date")
        batch.drop_column("serial_number")
        batch.drop_column("lot_number")

    with op.batch_alter_table("inventory_storerooms") as batch:
        batch.drop_column("requires_supplier_reference_for_receipt")
        batch.drop_column("requires_reservation_for_issue")

    op.drop_index("idx_runtime_executions_module_status", table_name="runtime_executions")
    op.drop_index("idx_runtime_executions_started", table_name="runtime_executions")
    op.drop_table("runtime_executions")

    op.drop_index("idx_auth_sessions_revoked", table_name="auth_sessions")
    op.drop_index("idx_auth_sessions_expires", table_name="auth_sessions")
    op.drop_index("idx_auth_sessions_user", table_name="auth_sessions")
    op.drop_table("auth_sessions")
