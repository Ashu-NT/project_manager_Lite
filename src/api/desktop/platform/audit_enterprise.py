from __future__ import annotations

from src.api.desktop.platform._support import execute_desktop_operation
from src.api.desktop.platform.models import DesktopApiResult
from src.api.desktop.platform.models.audit_entry import AuditEntryDto
from src.core.platform.audit.application.enterprise_audit_service import EnterpriseAuditService
from src.core.platform.audit.domain.audit_entry import AuditEntry

_SEVERITY_COLOR: dict[str, str] = {
    "critical": "red",
    "high": "orange",
    "medium": "yellow",
    "low": "green",
}

_ENTITY_TYPE_LABEL: dict[str, str] = {
    "auth_session": "Auth Session",
    "user_account": "User Account",
    "organization": "Organization",
    "role": "Role",
    "permission": "Permission",
    "tenant": "Tenant",
    "approval": "Approval",
}


class PlatformEnterpriseAuditDesktopApi:
    """Desktop-facing adapter for the enterprise compliance/security audit feed."""

    def __init__(self, *, enterprise_audit_service: EnterpriseAuditService) -> None:
        self._service = enterprise_audit_service

    def list_recent(
        self,
        *,
        limit: int = 100,
        entity_type: str | None = None,
        operation: str | None = None,
        severity: str | None = None,
    ) -> DesktopApiResult[tuple[AuditEntryDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._to_dto(entry)
                for entry in self._service.list_recent(
                    limit=limit,
                    entity_type=entity_type,
                    operation=operation,
                    severity=severity,
                )
            )
        )

    def list_for_overview(self, *, limit: int = 50) -> list[dict]:
        """Return pre-formatted dicts ready for AppWidgets.ActivityFeed."""
        try:
            entries = self._service.list_recent(limit=limit)
        except Exception:
            return []
        return [self._to_feed_item(entry) for entry in entries]

    def _to_dto(self, entry: AuditEntry) -> AuditEntryDto:
        return AuditEntryDto(
            id=entry.id,
            timestamp=entry.timestamp,
            operation=entry.operation,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            module=entry.module,
            actor_id=entry.actor_id,
            actor_username=entry.actor_username,
            actor_type=entry.actor_type,
            source=entry.source,
            severity=entry.severity,
            compliance_tag=entry.compliance_tag,
            tenant_id=entry.tenant_id,
            organization_id=entry.organization_id,
            entity_parent_id=entry.entity_parent_id,
            changed_field=entry.field,
            old_value=entry.old_value,
            new_value=entry.new_value,
            metadata=dict(entry.metadata),
        )

    def _to_feed_item(self, entry: AuditEntry) -> dict:
        actor_label = entry.actor_username or entry.actor_id or "System"
        entity_label = _ENTITY_TYPE_LABEL.get(entry.entity_type, entry.entity_type.replace("_", " ").title())
        ts = entry.timestamp.strftime("%Y-%m-%d %H:%M UTC")
        tag_parts = [p for p in (entry.compliance_tag, entry.source) if p and p != "none"]
        supporting = " · ".join(tag_parts) if tag_parts else ""
        return {
            "id": entry.id,
            "title": f"{actor_label} — {entry.operation.replace('.', ' ').replace('_', ' ')}",
            "statusLabel": entry.severity.capitalize(),
            "subtitle": entity_label,
            "metaText": ts,
            "supportingText": supporting,
            "state": {
                "color": _SEVERITY_COLOR.get(entry.severity, "grey"),
                "icon": "security",
            },
        }


__all__ = ["PlatformEnterpriseAuditDesktopApi"]
