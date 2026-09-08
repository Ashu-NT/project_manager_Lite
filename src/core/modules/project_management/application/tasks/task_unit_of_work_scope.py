from __future__ import annotations

from typing import Any


class PassthroughTaskUnitOfWork:
    """Used when a caller other than a direct Task command already owns the
    physical transaction -- ApprovalService (approval-driven Task mutations),
    Project's own delete_project transaction (cascade deletion), or a
    Time/Approved-Time transaction (the TimeEntry -> TaskAssignment edge).

    Mutations run directly against the already-injected repos/session; there is
    no second commit here -- `commit()` is a deliberate no-op, and the caller
    collects whatever typed fact(s) were recorded via `collected_events`
    (`TaskService._take_pending_task_events()`) instead of them being
    dispatched by this object. P45A-FINAL-CLOSURE items 27/33/45: the
    aggregate owns its fact, the calling operation owns the transaction
    boundary -- this class exists so every Task mutation method can call
    `self._task_uow(...)` uniformly regardless of which boundary applies.
    """

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

    def __enter__(self) -> "PassthroughTaskUnitOfWork":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


__all__ = ["PassthroughTaskUnitOfWork"]
