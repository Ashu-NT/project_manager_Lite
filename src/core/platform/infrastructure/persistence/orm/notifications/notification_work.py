"""Committed local notification work; not a second business-event authority."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class NotificationWorkORM(Base):
    __tablename__ = "notification_work"
    __table_args__ = (
        CheckConstraint("attempt_count >= 0 AND attempt_count <= 8", name="ck_notification_work_attempts"),
        CheckConstraint(
            "organization_id IS NULL OR tenant_id IS NOT NULL",
            name="ck_notification_work_org_requires_tenant",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False,
    )
    organization_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True,
    )
    source_event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    recipient_user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}", server_default="{}")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", server_default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    available_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)


Index(
    "uq_notification_work_source_recipient_kind",
    NotificationWorkORM.tenant_id,
    NotificationWorkORM.source_event_id,
    NotificationWorkORM.category,
    NotificationWorkORM.recipient_user_id,
    unique=True,
)
Index(
    "idx_notification_work_pending",
    NotificationWorkORM.tenant_id,
    NotificationWorkORM.organization_id,
    NotificationWorkORM.status,
    NotificationWorkORM.available_at,
)
