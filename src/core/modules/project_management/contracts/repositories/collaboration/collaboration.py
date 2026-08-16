from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.project_management.domain.collaboration import TaskComment, TaskPresence


class TaskCommentRepository(ABC):
    @abstractmethod
    def add(self, comment: TaskComment) -> None: ...

    @abstractmethod
    def update(self, comment: TaskComment) -> None: ...

    @abstractmethod
    def get(self, comment_id: str) -> TaskComment | None: ...

    @abstractmethod
    def list_by_task(self, task_id: str) -> list[TaskComment]: ...

    @abstractmethod
    def list_recent_for_tasks(self, task_ids: list[str], limit: int = 200) -> list[TaskComment]: ...


class TaskPresenceRepository(ABC):
    @abstractmethod
    def touch(
        self,
        *,
        task_id: str,
        user_id: str | None,
        username: str,
        display_name: str | None,
        activity: str,
    ) -> TaskPresence: ...

    @abstractmethod
    def clear(self, *, task_id: str, username: str) -> None: ...

    @abstractmethod
    def list_recent_for_tasks(
        self,
        task_ids: list[str],
        *,
        since,
        limit: int = 200,
    ) -> list[TaskPresence]: ...
