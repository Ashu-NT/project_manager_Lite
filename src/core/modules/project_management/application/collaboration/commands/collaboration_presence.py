from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.collaboration.event_handlers.view_invalidation import (
    notify_task_presence_stale,
)
from src.core.modules.project_management.application.collaboration.utils.visibility import (
    CollaborationVisibilityPolicy,
    new_collaboration_context,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.contracts.uow.collaboration.collaboration_unit_of_work import (
    CollaborationUnitOfWorkFactory,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)


class CollaborationPresenceCommandHandler(ProjectManagementModuleGuardMixin):
    """Presence heartbeat writes (touch/clear) followed by view invalidation."""

    def __init__(
        self,
        *,
        policy: CollaborationVisibilityPolicy,
        uow_factory: CollaborationUnitOfWorkFactory,
        tenant_context_service,
        user_session=None,
        module_catalog_service=None,
        view_invalidation_channel=None,
    ) -> None:
        self._policy = policy
        self._uow_factory = uow_factory
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service
        self._view_invalidation_channel = view_invalidation_channel

    def touch_task_presence(self, task_id: str, *, activity: str = "reviewing") -> None:
        task = self._policy.require_task(task_id)
        require_permission(self._user_session, "collaboration.read", operation_label="update task presence")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="update task presence",
        )
        principal = self._policy.principal
        user_id = str(getattr(principal, "user_id", "") or "").strip()
        if not user_id:
            raise RuntimeError("Authenticated user ID is required for task presence.")
        username = self._policy.principal_primary_alias() or user_id
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="update task presence"
        )
        with self._uow_factory.create(context=new_collaboration_context()) as uow:
            uow.presence.touch(
                task_id=task_id,
                user_id=user_id,
                username=username,
                display_name=getattr(principal, "display_name", None),
                activity=activity,
            )
            uow.commit()
        notify_task_presence_stale(
            self._view_invalidation_channel,
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            task_id=task_id,
        )

    def clear_task_presence(self, task_id: str) -> None:
        task = self._policy.require_task(task_id)
        require_permission(self._user_session, "collaboration.read", operation_label="clear task presence")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="clear task presence",
        )
        principal = self._policy.principal
        user_id = str(getattr(principal, "user_id", "") or "").strip()
        if not user_id:
            raise RuntimeError("Authenticated user ID is required for task presence.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="clear task presence"
        )
        with self._uow_factory.create(context=new_collaboration_context()) as uow:
            uow.presence.clear(task_id=task_id, user_id=user_id)
            uow.commit()
        notify_task_presence_stale(
            self._view_invalidation_channel,
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            task_id=task_id,
        )


__all__ = ["CollaborationPresenceCommandHandler"]
