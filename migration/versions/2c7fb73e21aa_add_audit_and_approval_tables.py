"""add audit and approval tables

Revision ID: 2c7fb73e21aa
Revises: 1f0d9a6a3f21
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa


revision = "2c7fb73e21aa"
down_revision = "1f0d9a6a3f21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("actor_user_id", sa.String(), nullable=True),
        sa.Column("actor_username", sa.String(length=128), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("request_type", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("requested_by_user_id", sa.String(), nullable=True),
        sa.Column("requested_by_username", sa.String(length=128), nullable=True),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("decided_by_user_id", sa.String(), nullable=True),
        sa.Column("decided_by_username", sa.String(length=128), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_logs_occurred_at", "audit_logs", ["occurred_at"], unique=False)
    op.create_index("idx_audit_logs_project", "audit_logs", ["project_id"], unique=False)
    op.create_index(
        "idx_audit_logs_entity",
        "audit_logs",
        ["entity_type", "entity_id"],
        unique=False,
    )
    op.create_index("idx_approval_status", "approval_requests", ["status"], unique=False)
    op.create_index("idx_approval_project", "approval_requests", ["project_id"], unique=False)
    op.create_index("idx_approval_type", "approval_requests", ["request_type"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_approval_type", table_name="approval_requests")
    op.drop_index("idx_approval_project", table_name="approval_requests")
    op.drop_index("idx_approval_status", table_name="approval_requests")
    op.drop_index("idx_audit_logs_entity", table_name="audit_logs")
    op.drop_index("idx_audit_logs_project", table_name="audit_logs")
    op.drop_index("idx_audit_logs_occurred_at", table_name="audit_logs")
    op.drop_table("approval_requests")
    op.drop_table("audit_logs")

