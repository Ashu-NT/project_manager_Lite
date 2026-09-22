from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from src.core.platform.contract.repositories.history.activity.contracts import ActivityRepository
from src.core.platform.domain.history.activity.activity_entry import ActivityEntry
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContext, TenantContextService


_DEFAULT_ACTIVITY_PAGE_SIZE = 25
ACTIVITY_PAGE_SIZE_OPTIONS: tuple[int, ...] = (25, 50, 100)


@dataclass(frozen=True)
class ActivityPage:
    items: list[ActivityEntry] = field(default_factory=list)
    total: int = 0
    filtered_total: int = 0
    page: int = 1
    page_size: int = _DEFAULT_ACTIVITY_PAGE_SIZE


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
        organization_id: str | None = None,
        human_message: str = "",
        details: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        parent_entity_id: str | None = None,
        type: str = "info",
        visibility: str = "workspace",
        icon: str | None = None,
        color: str | None = None,
        related_entity_type: str | None = None,
        related_entity_id: str | None = None,
        commit: bool = False,
    ) -> ActivityEntry:
        principal = self._user_session.principal if self._user_session else None
        actor_id = principal.user_id if principal else None
        # organization_id is an explicit override, not always the caller's
        # active organization -- e.g. recording "Organization created" must
        # attribute the entry to the NEW organization's own id, which is
        # rarely the caller's active one. Falls back to the active org (or
        # None) only when the caller doesn't already know the right one.
        resolved_organization_id = organization_id
        tenant_id: str | None = None
        tc = self._tenant_context_service
        if tc is not None:
            try:
                tenant_id = tc.get_active_tenant_id()
            except Exception:
                pass
            if resolved_organization_id is None:
                try:
                    resolved_organization_id = tc.require_active_organization_id(
                        operation_label="record activity"
                    )
                except Exception:
                    resolved_organization_id = None
        entry = ActivityEntry.create(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            module=module,
            actor_id=actor_id,
            workspace_id=workspace_id,
            tenant_id=tenant_id,
            organization_id=resolved_organization_id,
            type=type,
            human_message=human_message or action,
            details=details or {},
            context=context or {},
            parent_entity_id=parent_entity_id,
            icon=icon,
            color=color,
            visibility=visibility,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
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
        require_any_permission(
            self._user_session,
            ("settings.manage", "activity.read"),
            operation_label="view activity entries",
        )
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

    def list_recent_for_organization_id(
        self,
        organization_id: str,
        limit: int = 200,
        *,
        entity_type: str | None = None,
        entity_types: Sequence[str] | None = None,
        module: str | None = None,
        workspace_id: str | None = None,
        parent_entity_id: str | None = None,
        action_prefix: str | None = None,
    ) -> list[ActivityEntry]:
        """Activity for a specific organization, regardless of which
        organization is currently active in the caller's session -- used by
        Organization Detail, which may be viewing an organization the user
        hasn't switched their active context to."""
        require_any_permission(
            self._user_session,
            ("settings.manage", "activity.read"),
            operation_label="view activity entries",
        )
        scope = self._require_scope(operation_label="list activity for organization")
        return self._activity_repo.list_recent(
            limit=limit,
            tenant_id=scope.tenant_id,
            organization_id=organization_id,
            entity_type=entity_type,
            entity_types=entity_types,
            module=module,
            workspace_id=workspace_id,
            parent_entity_id=parent_entity_id,
            action_prefix=action_prefix,
        )

    def list_recent_page_for_organization(
        self,
        organization_id: str,
        *,
        page: int = 1,
        page_size: int = _DEFAULT_ACTIVITY_PAGE_SIZE,
        search: str = "",
        entity_type: str | None = None,
        entity_types: Sequence[str] | None = None,
        since: datetime | None = None,
    ) -> ActivityPage:
        """Full, paginated + searchable Activity workspace for a specific
        organization, regardless of which organization is currently active
        in the caller's session -- the "real" Activity tab, as opposed to
        `list_recent_for_organization_id`'s bounded Overview preview. Same
        organization-scoping rule and permission check as that method."""
        require_any_permission(
            self._user_session,
            ("settings.manage", "activity.read"),
            operation_label="view activity entries",
        )
        scope = self._require_scope(operation_label="list activity for organization")
        normalized_page = max(1, page)
        normalized_page_size = (
            page_size if page_size in ACTIVITY_PAGE_SIZE_OPTIONS else _DEFAULT_ACTIVITY_PAGE_SIZE
        )
        items, total, filtered_total = self._activity_repo.list_page_recent(
            page=normalized_page,
            page_size=normalized_page_size,
            tenant_id=scope.tenant_id,
            organization_id=organization_id,
            entity_type=entity_type,
            entity_types=entity_types,
            search=search,
            since=since,
        )
        return ActivityPage(
            items=items,
            total=total,
            filtered_total=filtered_total,
            page=normalized_page,
            page_size=normalized_page_size,
        )

    def list_recent_for_entity(
        self,
        entity_type: str,
        entity_id: str,
        organization_id: str,
        limit: int = 200,
    ) -> list[ActivityEntry]:
        """Activity for one specific entity (e.g. one Site), scoped to an
        EXPLICIT organization_id -- not the caller's ambient active
        organization -- since the entity's own detail page may be showing
        data for an organization the caller hasn't switched into. Mirrors
        list_recent_for_organization_id's explicit-scope rule, narrowed to
        one entity_id rather than the whole organization."""
        require_any_permission(
            self._user_session,
            ("settings.manage", "activity.read"),
            operation_label="view activity entries",
        )
        scope = self._require_scope(operation_label="list activity for entity")
        return self._activity_repo.list_recent(
            limit=limit,
            tenant_id=scope.tenant_id,
            organization_id=organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )

    def list_recent_page_for_entity(
        self,
        entity_type: str,
        entity_id: str,
        organization_id: str,
        *,
        page: int = 1,
        page_size: int = _DEFAULT_ACTIVITY_PAGE_SIZE,
        search: str = "",
        since: datetime | None = None,
    ) -> ActivityPage:
        """Full, paginated + searchable Activity workspace for one specific
        entity -- the real Activity tab, as opposed to
        list_recent_for_entity's bounded Overview preview. Same
        explicit-organization-scoping rule as list_recent_page_for_organization."""
        require_any_permission(
            self._user_session,
            ("settings.manage", "activity.read"),
            operation_label="view activity entries",
        )
        scope = self._require_scope(operation_label="list activity for entity")
        normalized_page = max(1, page)
        normalized_page_size = (
            page_size if page_size in ACTIVITY_PAGE_SIZE_OPTIONS else _DEFAULT_ACTIVITY_PAGE_SIZE
        )
        items, total, filtered_total = self._activity_repo.list_page_recent(
            page=normalized_page,
            page_size=normalized_page_size,
            tenant_id=scope.tenant_id,
            organization_id=organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            search=search,
            since=since,
        )
        return ActivityPage(
            items=items,
            total=total,
            filtered_total=filtered_total,
            page=normalized_page,
            page_size=normalized_page_size,
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


__all__ = ["ActivityService", "ActivityPage", "ACTIVITY_PAGE_SIZE_OPTIONS"]
