from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.collaboration.utils.visibility import (
    CollaborationVisibilityPolicy,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.contracts.reads.collaboration import (
    CollaborationWorkspaceReader,
)
from src.core.modules.project_management.contracts.repositories.collaboration.collaboration import (
    TaskPresenceRepository,
)
from src.core.modules.project_management.domain.collaboration import (
    TaskPresenceStatusItem,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)


class CollaborationPresenceQueryHandler(ProjectManagementModuleGuardMixin):
    """Bounded task / workspace presence reads within the presence TTL."""

    def __init__(
        self,
        *,
        workspace_reader: CollaborationWorkspaceReader,
        policy: CollaborationVisibilityPolicy,
        tenant_context_service,
        user_session=None,
        module_catalog_service=None,
        presence_repo: TaskPresenceRepository,
    ) -> None:
        self._workspace_reader = workspace_reader
        self._policy = policy
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service
        self._presence_repo = presence_repo
        self._presence_ttl_seconds = max(
            int(os.getenv("PM_TASK_PRESENCE_TTL_SECONDS", "900") or 900), 60
        )

    def list_task_presence(self, task_id: str) -> list[TaskPresenceStatusItem]:
        task = self._policy.require_task(task_id)
        require_permission(self._user_session, "collaboration.read", operation_label="view task presence")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="view task presence",
        )
        return self._presence_items_for_tasks(
            tasks=[task],
            project_name_by_id={task.project_id: self._policy.project_name(task.project_id)},
            limit=50,
        )

    def list_active_presence(self) -> list[TaskPresenceStatusItem]:
        require_permission(self._user_session, "collaboration.read", operation_label="view active task presence")
        scope, project_names = self._policy.collaboration_scope(
            operation_label="view active task presence"
        )
        rows = self._workspace_reader.read_active_presence(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            accessible_project_ids=tuple(project_names),
            active_since=datetime.now(UTC)
            - timedelta(seconds=self._presence_ttl_seconds),
        )
        return self._presence_items_from_facts(rows)

    def _presence_items_from_facts(self, rows) -> list[TaskPresenceStatusItem]:
        principal = self._policy.principal
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        return [
            TaskPresenceStatusItem(
                task_id=row.task_id,
                task_name=row.task_name,
                project_id=row.project_id,
                project_name=row.project_name,
                username=row.username,
                display_name=row.display_name,
                activity=row.activity,
                last_seen_at=row.last_seen_at,
                is_self=bool(principal_user_id and row.user_id == principal_user_id),
                user_id=str(row.user_id),
            )
            for row in rows
        ]

    def _presence_items_for_tasks(
        self,
        *,
        tasks,
        project_name_by_id: dict[str, str],
        limit: int,
    ) -> list[TaskPresenceStatusItem]:
        task_by_id = {task.id: task for task in tasks}
        rows = self._presence_repo.list_recent_for_tasks(
            list(task_by_id.keys()),
            since=datetime.now(UTC) - timedelta(seconds=self._presence_ttl_seconds),
            limit=limit,
        )
        principal = self._policy.principal
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        items: list[TaskPresenceStatusItem] = []
        for row in rows:
            task = task_by_id.get(row.task_id)
            if task is None:
                continue
            items.append(
                TaskPresenceStatusItem(
                    task_id=task.id,
                    task_name=task.name,
                    project_id=task.project_id,
                    project_name=project_name_by_id.get(task.project_id, ""),
                    username=row.username,
                    display_name=row.display_name,
                    activity=row.activity,
                    last_seen_at=row.last_seen_at,
                    is_self=bool(principal_user_id and row.user_id == principal_user_id),
                    user_id=row.user_id,
                )
            )
        return items


__all__ = ["CollaborationPresenceQueryHandler"]
