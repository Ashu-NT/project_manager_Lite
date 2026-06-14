from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class ActivityEntryORM(Base):
    __tablename__ = "activity_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    actor_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    actor_role: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    module: Mapped[str] = mapped_column(String(64), nullable=False, default="platform", server_default="platform")
    workspace_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=True,
    )
    organization_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False, default="info", server_default="info")
    human_message: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}", server_default="{}")
    context_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}", server_default="{}")
    parent_entity_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, default="workspace", server_default="workspace")


Index("idx_activity_tenant_timestamp", ActivityEntryORM.tenant_id, ActivityEntryORM.timestamp)
Index("idx_activity_org_timestamp", ActivityEntryORM.organization_id, ActivityEntryORM.timestamp)
Index("idx_activity_entity", ActivityEntryORM.entity_type, ActivityEntryORM.entity_id)
Index("idx_activity_workspace", ActivityEntryORM.workspace_id, ActivityEntryORM.timestamp)
Index("idx_activity_module_entity", ActivityEntryORM.module, ActivityEntryORM.entity_type, ActivityEntryORM.entity_id)
Index("idx_activity_actor", ActivityEntryORM.actor_id, ActivityEntryORM.timestamp)


__all__ = ["ActivityEntryORM"]
