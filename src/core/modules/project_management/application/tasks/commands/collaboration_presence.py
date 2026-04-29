from __future__ import annotations

from src.core.platform.access.authorization import require_project_permission
from src.core.platform.auth.authorization import require_permission
from src.core.platform.notifications.domain_events import domain_events


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


__all__ = ["CollaborationPresenceCommandMixin"]
