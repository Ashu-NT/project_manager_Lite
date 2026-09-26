from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class AuditEntryORM(Base):
    __tablename__ = "audit_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    actor_id: Mapped[str | None] = mapped_column(String, nullable=True)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False, default="user", server_default="user")
    actor_username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    actor_display_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    actor_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    authentication_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    impersonated_by_actor_id: Mapped[str | None] = mapped_column(String, nullable=True)
    service_account_id: Mapped[str | None] = mapped_column(String, nullable=True)

    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    entity_parent_id: Mapped[str | None] = mapped_column(String, nullable=True)
    entity_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="COMPLIANCE", server_default="COMPLIANCE")
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="low", server_default="low")
    result: Mapped[str] = mapped_column(String(16), nullable=False, default="SUCCESS", server_default="SUCCESS")
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)

    before_data_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_data_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_fields_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    module: Mapped[str] = mapped_column(String(64), nullable=False, default="platform", server_default="platform")
    tenant_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=True,
    )
    organization_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    workspace_id: Mapped[str | None] = mapped_column(String, nullable=True)
    project_id: Mapped[str | None] = mapped_column(String, nullable=True)

    request_id: Mapped[str | None] = mapped_column(String, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    causation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="DESKTOP_UI", server_default="DESKTOP_UI")

    permission_used: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approval_request_id: Mapped[str | None] = mapped_column(String, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}", server_default="{}")


Index("idx_audit_entries_tenant_ts", AuditEntryORM.tenant_id, AuditEntryORM.timestamp)
Index("idx_audit_entries_org_ts", AuditEntryORM.organization_id, AuditEntryORM.timestamp)
Index("idx_audit_entries_entity", AuditEntryORM.entity_type, AuditEntryORM.entity_id)
Index("idx_audit_entries_actor", AuditEntryORM.actor_id, AuditEntryORM.timestamp)
Index("idx_audit_entries_operation", AuditEntryORM.operation, AuditEntryORM.timestamp)
Index("idx_audit_entries_category", AuditEntryORM.category, AuditEntryORM.timestamp)
Index("idx_audit_entries_severity", AuditEntryORM.severity, AuditEntryORM.timestamp)
Index("idx_audit_entries_project", AuditEntryORM.project_id, AuditEntryORM.timestamp)
Index("idx_audit_entries_correlation", AuditEntryORM.correlation_id)


__all__ = ["AuditEntryORM"]
