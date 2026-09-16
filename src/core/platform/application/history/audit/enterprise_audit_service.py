from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session

from src.core.platform.contract.repositories.history.audit.contracts import AuditRepository
from src.core.platform.domain.history.audit.audit_entry import AuditEntry
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.domain.security.auth.session import UserSessionContext


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
        category: str = "COMPLIANCE",
        severity: str = "low",
        result: str = "SUCCESS",
        failure_code: str | None = None,
        actor_id: str | None = None,
        actor_type: str = "user",
        actor_username: str | None = None,
        actor_display_name: str | None = None,
        actor_ip: str | None = None,
        actor_user_agent: str | None = None,
        session_id: str | None = None,
        authentication_method: str | None = None,
        impersonated_by_actor_id: str | None = None,
        service_account_id: str | None = None,
        entity_parent_id: str | None = None,
        entity_version: str | None = None,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
        changed_fields: dict[str, Any] | None = None,
        organization_id: str | None = None,
        workspace_id: str | None = None,
        project_id: str | None = None,
        request_id: str | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        source: str = "DESKTOP_UI",
        permission_used: str | None = None,
        approval_request_id: str | None = None,
        reason: str | None = None,
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
        resolved_actor_display_name = actor_display_name if actor_display_name is not None else (
            getattr(principal, "display_name", None) if principal else None
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
            category=category,
            severity=severity,
            result=result,
            failure_code=failure_code,
            actor_id=resolved_actor_id,
            actor_type=actor_type,
            actor_username=resolved_actor_username,
            actor_display_name=resolved_actor_display_name,
            actor_ip=actor_ip,
            actor_user_agent=actor_user_agent,
            session_id=session_id,
            authentication_method=authentication_method,
            impersonated_by_actor_id=impersonated_by_actor_id,
            service_account_id=service_account_id,
            entity_parent_id=entity_parent_id,
            entity_version=entity_version,
            before_data=before_data,
            after_data=after_data,
            changed_fields=changed_fields,
            tenant_id=tenant_id,
            organization_id=resolved_organization_id,
            workspace_id=workspace_id,
            project_id=project_id,
            request_id=request_id,
            correlation_id=correlation_id,
            causation_id=causation_id,
            source=source,
            permission_used=permission_used,
            approval_request_id=approval_request_id,
            reason=reason,
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
        category: str | None = None,
        result: str | None = None,
        project_id: str | None = None,
        module: str | None = None,
        workspace_id: str | None = None,
        operation_prefixes: Sequence[str] | None = None,
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
                category=category,
                result=result,
                project_id=project_id,
                module=module,
                workspace_id=workspace_id,
                operation_prefixes=operation_prefixes,
            )
        return self._audit_repo.list_recent(
            limit=limit,
            entity_type=entity_type,
            operation=operation,
            severity=severity,
            category=category,
            result=result,
            project_id=project_id,
            module=module,
            workspace_id=workspace_id,
            operation_prefixes=operation_prefixes,
        )

    def list_recent_for_organization_id(
        self,
        organization_id: str,
        limit: int = 100,
        *,
        entity_type: str | None = None,
        entity_types: Sequence[str] | None = None,
        operation: str | None = None,
        severity: str | None = None,
        category: str | None = None,
        result: str | None = None,
        project_id: str | None = None,
        module: str | None = None,
        workspace_id: str | None = None,
        operation_prefixes: Sequence[str] | None = None,
    ) -> list[AuditEntry]:
        """Audit entries for a specific organization, regardless of which
        organization is currently active in the caller's session -- used by
        Organization Detail, which may be viewing an organization the user
        hasn't switched their active context to."""
        require_permission(self._user_session, "audit.read", operation_label="view audit entries")
        return self._audit_repo.list_recent_for_organization(
            organization_id,
            limit=limit,
            entity_type=entity_type,
            entity_types=entity_types,
            operation=operation,
            severity=severity,
            category=category,
            result=result,
            project_id=project_id,
            module=module,
            workspace_id=workspace_id,
            operation_prefixes=operation_prefixes,
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
