from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.core.platform.activity.contracts import ActivityRepository
from src.core.platform.activity.domain.activity_entry import ActivityEntry
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.tenancy.tenant_context import TenantContext, TenantContextService


class ActivityService:
    def __init__(
        self,
        session: Session,
        activity_repo: ActivityRepository,
        user_session: Any = None,
        tenant_context_service: TenantContextService | None = None,
    ) -> None:
        self._session = session
        self._activity_repo = activity_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service

    def record(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str,
        module: str,
        workspace_id: str | None = None,
        human_message: str = "",
        details: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        parent_entity_id: str | None = None,
        type: str = "info",
        visibility: str = "workspace",
        icon: str | None = None,
        color: str | None = None,
        commit: bool = False,
    ) -> ActivityEntry:
        principal = self._user_session.principal if self._user_session else None
        actor_id = principal.user_id if principal else None
        scope = self._require_scope(operation_label="record activity")
        entry = ActivityEntry.create(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            module=module,
            actor_id=actor_id,
            workspace_id=workspace_id,
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            type=type,
            human_message=human_message or action,
            details=details or {},
            context=context or {},
            parent_entity_id=parent_entity_id,
            icon=icon,
            color=color,
            visibility=visibility,
        )
        self._activity_repo.add(entry)
        if commit:
            self._session.commit()
        return entry

    def list_recent(
        self,
        limit: int = 200,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        module: str | None = None,
        workspace_id: str | None = None,
        parent_entity_id: str | None = None,
        action_prefix: str | None = None,
    ) -> list[ActivityEntry]:
        scope = self._require_scope(operation_label="list activity")
        return self._activity_repo.list_recent(
            limit=limit,
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            module=module,
            workspace_id=workspace_id,
            parent_entity_id=parent_entity_id,
            action_prefix=action_prefix,
        )

    def _require_scope(self, *, operation_label: str) -> TenantContext:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "ActivityService requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_organization_context(
            operation_label=operation_label
        )


__all__ = ["ActivityService"]
