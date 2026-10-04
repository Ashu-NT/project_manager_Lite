"""Record notification provenance and enforce one row per event/kind/recipient."""

import sqlalchemy as sa
from alembic import op

from src.infra.persistence.migrations.helpers.postgresql_rls import (
    disable_parent_scoped_rls,
    enable_parent_scoped_rls,
)
from src.infra.persistence.migrations.helpers.rls_classification import (
    PARENT_SCOPED_RLS_PREDICATES,
)

revision = "c9a73e6d41b2"
down_revision = "a7b19c32d405"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("notifications") as batch:
        batch.add_column(sa.Column("organization_id", sa.String(), nullable=True))
        batch.add_column(sa.Column("source_event_id", sa.String(length=128), nullable=True))
        batch.create_foreign_key(
            "fk_notifications_organization_id_organizations",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_check_constraint(
            "ck_notifications_org_requires_tenant",
            "organization_id IS NULL OR tenant_id IS NOT NULL",
        )
        batch.create_check_constraint(
            "ck_notifications_source_requires_tenant",
            "source_event_id IS NULL OR tenant_id IS NOT NULL",
        )
    op.create_index(
        "uq_notifications_source_recipient_kind",
        "notifications",
        ["tenant_id", "source_event_id", "category", "recipient_user_id"],
        unique=True,
        postgresql_where=sa.text("source_event_id IS NOT NULL"),
        sqlite_where=sa.text("source_event_id IS NOT NULL"),
    )
    op.create_table(
        "notification_work",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("organization_id", sa.String(), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("source_event_id", sa.String(length=128), nullable=False),
        sa.Column("recipient_user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.CheckConstraint("attempt_count >= 0 AND attempt_count <= 8", name="ck_notification_work_attempts"),
        sa.CheckConstraint("organization_id IS NULL OR tenant_id IS NOT NULL", name="ck_notification_work_org_requires_tenant"),
    )
    op.create_index(
        "uq_notification_work_source_recipient_kind", "notification_work",
        ["tenant_id", "source_event_id", "category", "recipient_user_id"], unique=True,
    )
    op.create_index(
        "idx_notification_work_pending", "notification_work",
        ["tenant_id", "organization_id", "status", "available_at"],
    )
    enable_parent_scoped_rls(
        op, op.get_bind(), "notification_work",
        predicate=PARENT_SCOPED_RLS_PREDICATES["notification_work"],
    )
    enable_parent_scoped_rls(
        op, op.get_bind(), "notifications",
        predicate=PARENT_SCOPED_RLS_PREDICATES["notifications"],
    )


def downgrade():
    disable_parent_scoped_rls(op, op.get_bind(), "notifications")
    disable_parent_scoped_rls(op, op.get_bind(), "notification_work")
    op.drop_index("idx_notification_work_pending", table_name="notification_work")
    op.drop_index("uq_notification_work_source_recipient_kind", table_name="notification_work")
    op.drop_table("notification_work")
    op.drop_index("uq_notifications_source_recipient_kind", table_name="notifications")
    with op.batch_alter_table("notifications") as batch:
        batch.drop_constraint("ck_notifications_source_requires_tenant", type_="check")
        batch.drop_constraint("ck_notifications_org_requires_tenant", type_="check")
        batch.drop_constraint(
            "fk_notifications_organization_id_organizations", type_="foreignkey"
        )
        batch.drop_column("source_event_id")
        batch.drop_column("organization_id")
