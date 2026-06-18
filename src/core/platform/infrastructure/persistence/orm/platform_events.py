from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class PlatformEventORM(Base):
    __tablename__ = "platform_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tenant_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String, nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False, default="success", server_default="success")
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="low", server_default="low")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}", server_default="{}")


Index("idx_platform_events_tenant", PlatformEventORM.tenant_id, PlatformEventORM.created_at)
Index("idx_platform_events_actor", PlatformEventORM.actor_user_id, PlatformEventORM.created_at)
Index("idx_platform_events_resource", PlatformEventORM.tenant_id, PlatformEventORM.resource_type, PlatformEventORM.resource_id)
Index("idx_platform_events_operation", PlatformEventORM.operation, PlatformEventORM.created_at)
Index("idx_platform_events_created_at", PlatformEventORM.created_at)


__all__ = ["PlatformEventORM"]
