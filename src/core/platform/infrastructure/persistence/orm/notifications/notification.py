from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class NotificationORM(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "organization_id IS NULL OR tenant_id IS NOT NULL",
            name="ck_notifications_org_requires_tenant",
        ),
        CheckConstraint(
            "source_event_id IS NULL OR tenant_id IS NOT NULL",
            name="ck_notifications_source_requires_tenant",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    recipient_user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=True,
    )
    organization_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True,
    )
    source_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}", server_default="{}")


Index("idx_notifications_recipient_created", NotificationORM.recipient_user_id, NotificationORM.created_at)
Index("idx_notifications_recipient_unread", NotificationORM.recipient_user_id, NotificationORM.read_at)
Index(
    "uq_notifications_source_recipient_kind",
    NotificationORM.tenant_id,
    NotificationORM.source_event_id,
    NotificationORM.category,
    NotificationORM.recipient_user_id,
    unique=True,
    postgresql_where=text("source_event_id IS NOT NULL"),
    sqlite_where=text("source_event_id IS NOT NULL"),
)


__all__ = ["NotificationORM"]
