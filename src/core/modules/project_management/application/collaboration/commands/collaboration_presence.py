from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.collaboration.event_handlers.view_invalidation import (
    notify_task_presence_stale,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)


class CollaborationPresenceCommandMixin:
    def touch_task_presence(self, task_id: str, *, activity: str = "reviewing") -> None:
        task = self._require_task(task_id)
        require_permission(self._user_session, "collaboration.read", operation_label="update task presence")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="update task presence",
        )
        principal = self._user_session.principal if self._user_session is not None else None
        user_id = str(getattr(principal, "user_id", "") or "").strip()
        if not user_id:
            raise RuntimeError("Authenticated user ID is required for task presence.")
        username = self._principal_primary_alias() or user_id
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="update task presence"
        )
        with self._require_collaboration_uow_factory().create(
            context=self._new_context()
        ) as uow:
            uow.presence.touch(
                task_id=task_id,
                user_id=user_id,
                username=username,
                display_name=getattr(principal, "display_name", None),
                activity=activity,
            )
            uow.commit()
        notify_task_presence_stale(
            getattr(self, "_view_invalidation_channel", None),
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            task_id=task_id,
        )

    def clear_task_presence(self, task_id: str) -> None:
        task = self._require_task(task_id)
        require_permission(self._user_session, "collaboration.read", operation_label="clear task presence")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="clear task presence",
        )
        principal = self._user_session.principal if self._user_session is not None else None
        user_id = str(getattr(principal, "user_id", "") or "").strip()
        if not user_id:
            raise RuntimeError("Authenticated user ID is required for task presence.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="clear task presence"
        )
        with self._require_collaboration_uow_factory().create(
            context=self._new_context()
        ) as uow:
            uow.presence.clear(task_id=task_id, user_id=user_id)
            uow.commit()
        notify_task_presence_stale(
            getattr(self, "_view_invalidation_channel", None),
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            task_id=task_id,
        )


__all__ = ["CollaborationPresenceCommandMixin"]
