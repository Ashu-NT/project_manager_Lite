from __future__ import annotations

from typing import Any, Self

from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    DependencyRepository,
    TaskRepository,
)
from src.core.modules.project_management.contracts.uow.tasks.task_unit_of_work import (
    TaskUnitOfWorkFactory,
)
from src.core.platform.application.history.activity.activity_service import (
    ActivityService,
)
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.repositories.time_management.time.contracts import (
    TimeEntryRepository,
)
from src.core.shared.events.domain_event_context import DomainEventContext


class TaskParticipantUnitOfWork:

    def __init__(
        self,
        *,
        tasks: Any,
        assignments: Any,
        dependencies: Any,
        project_resources: Any,
        time_entries: Any,
        enterprise_audit_service: Any,
        activity_service: Any,
        collected_events: list,
    ) -> None:
        self.tasks = tasks
        self.assignments = assignments
        self.dependencies = dependencies
        self.project_resources = project_resources
        self.time_entries = time_entries
        self._enterprise_audit_service = enterprise_audit_service
        self._activity_service = activity_service
        self._collected_events = collected_events

    def record_event(self, event: object) -> None:
        self._collected_events.append(event)

    def commit(self) -> None:
        return None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class TaskUowScope:
    """Select the operation-owned UoW or the caller-owned approval transaction."""

    def __init__(
        self,
        *,
        factory: TaskUnitOfWorkFactory | None,
        tasks: TaskRepository,
        assignments: AssignmentRepository,
        dependencies: DependencyRepository,
        project_resources: ProjectResourceRepository | None,
        time_entries: TimeEntryRepository | None,
        enterprise_audit_service: EnterpriseAuditService | None,
        activity_service: ActivityService | None,
    ) -> None:
        self._factory = factory
        self._tasks = tasks
        self._assignments = assignments
        self._dependencies = dependencies
        self._project_resources = project_resources
        self._time_entries = time_entries
        self._enterprise_audit_service = enterprise_audit_service
        self._activity_service = activity_service
        self._pending_events: list = []

    def create(self, context: DomainEventContext | None = None):
        if self._factory is not None:
            return self._factory.create(
                context=context or DomainEventContext(correlation_id=generate_id())
            )
        self._pending_events = []
        return TaskParticipantUnitOfWork(
            tasks=self._tasks,
            assignments=self._assignments,
            dependencies=self._dependencies,
            project_resources=self._project_resources,
            time_entries=self._time_entries,
            enterprise_audit_service=self._enterprise_audit_service,
            activity_service=self._activity_service,
            collected_events=self._pending_events,
        )

    def take_pending_events(self) -> tuple:
        events = tuple(self._pending_events)
        self._pending_events = []
        return events


__all__ = ["TaskParticipantUnitOfWork", "TaskUowScope"]
