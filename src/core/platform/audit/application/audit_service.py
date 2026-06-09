from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.core.platform.audit.contracts import AuditLogRepository
from src.core.platform.audit.domain import AuditLogEntry
from src.core.platform.auth.authorization import require_permission
from src.core.platform.auth.domain.session import UserSessionContext


class AuditService:
    def __init__(
        self,
        session: Session,
        audit_repo: AuditLogRepository,
        user_session: UserSessionContext | None = None,
        tenant_context_service=None,
    ):
        self._session = session
        self._audit_repo = audit_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service

    def record(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str,
        project_id: str | None = None,
        details: dict[str, Any] | None = None,
        actor_user_id: str | None = None,
        actor_username: str | None = None,
        commit: bool = False,
    ) -> AuditLogEntry:
        principal = self._user_session.principal if self._user_session else None
        resolved_actor_user_id = actor_user_id if actor_user_id is not None else (
            principal.user_id if principal else None
        )
        resolved_actor_username = actor_username if actor_username is not None else (
            principal.username if principal else None
        )
        organization_id: str | None = None
        tenant_context = getattr(self, "_tenant_context_service", None)
        if tenant_context is not None:
            try:
                organization_id = tenant_context.get_active_organization_id()
            except Exception:
                pass
        entry = AuditLogEntry.create(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_user_id=resolved_actor_user_id,
            actor_username=resolved_actor_username,
            project_id=project_id,
            organization_id=organization_id,
            details=details or {},
        )
        self._audit_repo.add(entry)
        if commit:
            self._session.commit()
        return entry

    def list_recent(
        self,
        limit: int = 200,
        *,
        project_id: str | None = None,
        entity_type: str | None = None,
    ) -> list[AuditLogEntry]:
        require_permission(self._user_session, "audit.read", operation_label="view audit log")
        organization_id = self._active_organization_id(operation_label="view audit log")
        if organization_id and hasattr(self._audit_repo, "list_recent_for_organization"):
            return self._audit_repo.list_recent_for_organization(
                organization_id,
                limit=limit,
                project_id=project_id,
                entity_type=entity_type,
            )
        return self._audit_repo.list_recent(
            limit=limit,
            project_id=project_id,
            entity_type=entity_type,
        )

    def _active_organization_id(self, *, operation_label: str) -> str | None:
        tenant_context = getattr(self, "_tenant_context_service", None)
        if tenant_context is None:
            return None
        return tenant_context.require_active_organization_id(operation_label=operation_label)


__all__ = ["AuditService"]
