from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class AuditEntryORM(Base):
    __tablename__ = "audit_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    actor_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False, default="user", server_default="user")
    actor_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    actor_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    actor_user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    entity_parent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    field: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    module: Mapped[str] = mapped_column(String(64), nullable=False, default="platform", server_default="platform")
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
    workspace_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="api", server_default="api")
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="low", server_default="low")
    compliance_tag: Mapped[str] = mapped_column(String(32), nullable=False, default="none", server_default="none")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}", server_default="{}")


Index("idx_audit_entries_tenant_ts", AuditEntryORM.tenant_id, AuditEntryORM.timestamp)
Index("idx_audit_entries_org_ts", AuditEntryORM.organization_id, AuditEntryORM.timestamp)
Index("idx_audit_entries_entity", AuditEntryORM.entity_type, AuditEntryORM.entity_id)
Index("idx_audit_entries_actor", AuditEntryORM.actor_id, AuditEntryORM.timestamp)
Index("idx_audit_entries_operation", AuditEntryORM.operation, AuditEntryORM.timestamp)
Index("idx_audit_entries_compliance", AuditEntryORM.compliance_tag, AuditEntryORM.timestamp)
Index("idx_audit_entries_severity", AuditEntryORM.severity, AuditEntryORM.timestamp)


__all__ = ["AuditEntryORM"]
