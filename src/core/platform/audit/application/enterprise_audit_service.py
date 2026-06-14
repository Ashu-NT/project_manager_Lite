from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.core.platform.audit.contracts import AuditRepository
from src.core.platform.audit.domain.audit_entry import AuditEntry
from src.core.platform.auth.authorization import require_permission
from src.core.platform.auth.domain.session import UserSessionContext


class EnterpriseAuditService:
    def __init__(
        self,
        session: Session,
        audit_repo: AuditRepository,
        user_session: UserSessionContext | None = None,
        tenant_context_service: Any = None,
    ) -> None:
        self._session = session
        self._audit_repo = audit_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service

    def record(
        self,
        *,
        operation: str,
        entity_type: str,
        entity_id: str,
        module: str,
        actor_id: str | None = None,
        actor_type: str = "user",
        actor_username: str | None = None,
        actor_ip: str | None = None,
        actor_user_agent: str | None = None,
        entity_parent_id: str | None = None,
        field: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
        organization_id: str | None = None,
        workspace_id: str | None = None,
        request_id: str | None = None,
        source: str = "api",
        severity: str = "low",
        compliance_tag: str = "none",
        metadata: dict[str, Any] | None = None,
        commit: bool = False,
    ) -> AuditEntry:
        principal = self._user_session.principal if self._user_session else None
        resolved_actor_id = actor_id if actor_id is not None else (
            principal.user_id if principal else None
        )
        resolved_actor_username = actor_username if actor_username is not None else (
            principal.username if principal else None
        )
        resolved_organization_id = organization_id
        if resolved_organization_id is None:
            resolved_organization_id = self._active_organization_id()

        tenant_id: str | None = None
        tc = self._tenant_context_service
        if tc is not None:
            try:
                tenant_id = tc.get_active_tenant_id()
            except Exception:
                pass

        entry = AuditEntry.create(
            operation=operation,
            entity_type=entity_type,
            entity_id=entity_id,
            module=module,
            actor_id=resolved_actor_id,
            actor_type=actor_type,
            actor_username=resolved_actor_username,
            actor_ip=actor_ip,
            actor_user_agent=actor_user_agent,
            entity_parent_id=entity_parent_id,
            field=field,
            old_value=old_value,
            new_value=new_value,
            tenant_id=tenant_id,
            organization_id=resolved_organization_id,
            workspace_id=workspace_id,
            request_id=request_id,
            source=source,
            severity=severity,
            compliance_tag=compliance_tag,
            metadata=metadata,
        )
        self._audit_repo.add(entry)
        if commit:
            self._session.commit()
        return entry

    def list_recent(
        self,
        limit: int = 100,
        *,
        entity_type: str | None = None,
        operation: str | None = None,
        severity: str | None = None,
    ) -> list[AuditEntry]:
        require_permission(self._user_session, "audit.read", operation_label="view audit entries")
        organization_id = self._active_organization_id()
        if organization_id and hasattr(self._audit_repo, "list_recent_for_organization"):
            return self._audit_repo.list_recent_for_organization(
                organization_id,
                limit=limit,
                entity_type=entity_type,
                operation=operation,
                severity=severity,
            )
        return self._audit_repo.list_recent(
            limit=limit,
            entity_type=entity_type,
            operation=operation,
            severity=severity,
        )

    def _active_organization_id(self) -> str | None:
        tc = self._tenant_context_service
        if tc is None:
            return None
        try:
            return tc.require_active_organization_id(operation_label="enterprise audit")
        except Exception:
            return None


__all__ = ["EnterpriseAuditService"]
