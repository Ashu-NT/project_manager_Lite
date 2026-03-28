from __future__ import annotations

from datetime import datetime, timedelta

from core.platform.notifications.domain_events import domain_events
from core.modules.project_management.domain.collaboration import TaskPresenceStatusItem
from core.platform.access.authorization import require_project_permission
from core.platform.auth.authorization import require_permission


class CollaborationPresenceMixin:
    def touch_task_presence(self, task_id: str, *, activity: str = "reviewing") -> None:
        task = self._require_task(task_id)
        require_permission(self._user_session, "collaboration.read", operation_label="update task presence")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="update task presence",
        )
        username = self._principal_primary_alias()
        if not username:
            return
        principal = self._user_session.principal if self._user_session is not None else None
        self._presence_repo.touch(
            task_id=task_id,
            user_id=str(getattr(principal, "user_id", "") or "").strip() or None,
            username=username,
            display_name=getattr(principal, "display_name", None),
            activity=activity,
        )
        self._session.commit()
        domain_events.collaboration_changed.emit(task_id)

    def clear_task_presence(self, task_id: str) -> None:
        task = self._require_task(task_id)
        require_permission(self._user_session, "collaboration.read", operation_label="clear task presence")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="clear task presence",
        )
        username = self._principal_primary_alias()
        if not username:
            return
        self._presence_repo.clear(task_id=task_id, username=username)
        self._session.commit()
        domain_events.collaboration_changed.emit(task_id)

    def list_task_presence(self, task_id: str) -> list[TaskPresenceStatusItem]:
        task = self._require_task(task_id)
        require_permission(self._user_session, "collaboration.read", operation_label="view task presence")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="view task presence",
        )
        project = self._project_repo.get(task.project_id)
        return self._presence_items_for_tasks(
            tasks=[task],
            project_name_by_id={task.project_id: project.name if project is not None else ""},
            limit=50,
        )

    def list_active_presence(self, *, limit: int = 200) -> list[TaskPresenceStatusItem]:
        require_permission(self._user_session, "collaboration.read", operation_label="view active task presence")
        tasks = self._accessible_tasks_for_collaboration()
        if not tasks:
            return []
        project_name_by_id = {task.project_id: self._project_name(task.project_id) for task in tasks}
        return self._presence_items_for_tasks(
            tasks=tasks,
            project_name_by_id=project_name_by_id,
            limit=limit,
        )

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
            since=datetime.now() - timedelta(seconds=self._presence_ttl_seconds),
            limit=limit,
        )
        principal = self._user_session.principal if self._user_session is not None else None
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
                )
            )
        return items


__all__ = ["CollaborationPresenceMixin"]
