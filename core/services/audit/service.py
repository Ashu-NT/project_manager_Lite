from __future__ import annotations

from typing import Any, List

from sqlalchemy.orm import Session

from core.interfaces import AuditLogRepository
from core.models import AuditLogEntry
from core.services.auth.session import UserSessionContext


class AuditService:
    def __init__(
        self,
        session: Session,
        audit_repo: AuditLogRepository,
        user_session: UserSessionContext | None = None,
    ):
        self._session = session
        self._audit_repo = audit_repo
        self._user_session = user_session

    def record(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str,
        project_id: str | None = None,
        details: dict[str, Any] | None = None,
        commit: bool = False,
    ) -> AuditLogEntry:
        principal = self._user_session.principal if self._user_session else None
        entry = AuditLogEntry.create(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_user_id=principal.user_id if principal else None,
            actor_username=principal.username if principal else None,
            project_id=project_id,
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
    ) -> List[AuditLogEntry]:
        return self._audit_repo.list_recent(
            limit=limit,
            project_id=project_id,
            entity_type=entity_type,
        )


__all__ = ["AuditService"]

