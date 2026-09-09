from __future__ import annotations

from typing import Any


class TaskParticipantUnitOfWork:

    def __init__(
        self,
        *,
        tasks: Any,
        assignments: Any,
        dependencies: Any,
        enterprise_audit_service: Any,
        activity_service: Any,
        collected_events: list,
    ) -> None:
        self.tasks = tasks
        self.assignments = assignments
        self.dependencies = dependencies
        self._enterprise_audit_service = enterprise_audit_service
        self._activity_service = activity_service
        self._collected_events = collected_events

    def record_event(self, event: object) -> None:
        self._collected_events.append(event)

    def commit(self) -> None:
        return None

    def __enter__(self) -> "TaskParticipantUnitOfWork":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


__all__ = ["TaskParticipantUnitOfWork"]
