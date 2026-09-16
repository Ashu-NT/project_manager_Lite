from __future__ import annotations

from collections.abc import Sequence

from src.core.platform.api.desktop.support._support import execute_desktop_operation
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.history.audit.models.audit_entry import AuditEntryDto
from src.core.platform.application.history.audit.enterprise_audit_service import EnterpriseAuditService
from src.core.platform.domain.history.audit.audit_entry import AuditEntry


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
        module: str | None = None,
        workspace_id: str | None = None,
        operation_prefixes: Sequence[str] | None = None,
    ) -> DesktopApiResult[tuple[AuditEntryDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._to_dto(entry)
                for entry in self._service.list_recent(
                    limit=limit,
                    entity_type=entity_type,
                    operation=operation,
                    severity=severity,
                    module=module,
                    workspace_id=workspace_id,
                    operation_prefixes=operation_prefixes,
                )
            )
        )

    def list_for_overview(self, *, limit: int = 50) -> tuple[AuditEntryDto, ...]:
        """Entries for a contextual admin-overview audit preview."""
        try:
            entries = self._service.list_recent(limit=limit)
        except Exception:
            return ()
        return tuple(self._to_dto(entry) for entry in entries)

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
            category=entry.category,
            result=entry.result,
            tenant_id=entry.tenant_id,
            organization_id=entry.organization_id,
            entity_parent_id=entry.entity_parent_id,
            before_data=entry.before_data,
            after_data=entry.after_data,
            changed_fields=entry.changed_fields,
            metadata=dict(entry.metadata),
        )


__all__ = ["PlatformEnterpriseAuditDesktopApi"]
