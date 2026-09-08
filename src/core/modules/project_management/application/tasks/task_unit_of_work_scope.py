from __future__ import annotations

from typing import Any


class TaskParticipantUnitOfWork:
    """The canonical transaction-boundary-delegating counterpart to
    `SqlAlchemyTaskUnitOfWork`, not a legacy compatibility shim -- there is no
    old/new signal bridging here, no deprecated path, nothing temporary. It
    exists because a Task mutation command must run identically regardless of
    which operation owns its physical transaction: `SqlAlchemyTaskUnitOfWork`
    is used when a direct desktop-API command owns its own transaction (the
    main, long-lived `TaskService` built with a real `task_uow_factory` in
    `project_registry.py`); `TaskParticipantUnitOfWork` is used when the
    CALLER already owns one -- a participant-scoped `TaskService` built with
    `task_uow_factory=None`. Exactly two real callers exist today:
    `task_apply_participant.py`'s five Task-native approval decisions, and
    `FinancialChangeService._task_service` (wired the same way in
    `approval_apply_dependencies/financial_change.py`), whose schedule branch
    calls `_apply_approved_schedule_changes` then retrieves the facts via
    `_take_pending_task_events()`. (Project's `delete_project` cascade and
    TimeEntry's `hours_logged` sync do NOT go through this class at all --
    both record their `TaskRemoved`/`TaskAssignmentChanged` fact directly onto
    their OWN already-owned `SqlAlchemyUnitOfWorkBase`, never constructing a
    `TaskService` or this scope class; an earlier version of this docstring
    listed them here in error.) Per P45A-FINAL-CLOSURE §45: the aggregate owns
    its fact, the calling operation owns the transaction boundary. This is the
    permanent shape of that split, not an interim state -- both branches
    always report through the same typed `TaskAssignmentChanged`/
    `TaskScheduleChanged`/etc. vocabulary; only the commit/dispatch mechanics
    differ.

    Mutations run directly against the already-injected repos/session; there
    is no second commit here -- `commit()` is a deliberate no-op, and the
    caller collects whatever typed fact(s) were recorded via
    `collected_events` (`TaskService._take_pending_task_events()`) instead of
    them being dispatched by this object -- the caller's own UoW/transactional
    dispatcher owns precommit/postcommit delivery. This class exists so every
    Task mutation method can call `self._task_uow(...)` uniformly regardless
    of which boundary applies.
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

    def __enter__(self) -> "TaskParticipantUnitOfWork":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


__all__ = ["TaskParticipantUnitOfWork"]
