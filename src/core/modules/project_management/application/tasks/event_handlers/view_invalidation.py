from __future__ import annotations

from src.core.modules.project_management.application.tasks.task_events import (
    TaskAssignmentChanged,
    TaskCreated,
    TaskDependencyChanged,
    TaskHierarchyChanged,
    TaskProfileUpdated,
    TaskProgressChanged,
    TaskRemoved,
    TaskScheduleChanged,
    TaskStatusChanged,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    ResourceScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

TASK_CATEGORY = "task"
TASK_MODULE_CODE = "project_management"

TASK_LIST_SCOPE_CODE = "task_list"
TASK_DETAIL_SCOPE_CODE = "task_detail"
TASK_SCHEDULE_SCOPE_CODE = "task_schedule"
TASK_ASSIGNMENTS_SCOPE_CODE = "task_assignments"
TASK_DEPENDENCIES_SCOPE_CODE = "task_dependencies"
DASHBOARD_TASK_METRICS_SCOPE_CODE = "dashboard_task_metrics"

_TaskEvent = (
    TaskCreated
    | TaskProfileUpdated
    | TaskHierarchyChanged
    | TaskStatusChanged
    | TaskProgressChanged
    | TaskScheduleChanged
    | TaskRemoved
    | TaskAssignmentChanged
    | TaskDependencyChanged
)

_Target = tuple[str, str, str, str, str]


def build_task_view_invalidation_handler(channel: ViewInvalidationChannel):
    """One handler for all 9 Task DomainEvent classes -- P45B's final ViewInvalidation
    design (P45A-FINAL-CLOSURE §46-54). Dedupes by (correlation_id, exact target/scope
    identity) so N per-task facts sharing one project (bulk leveling, bulk status,
    Project cascade delete, Financial Change sibling reschedule) still produce exactly
    one hint per distinct target -- DomainEvent volume is never conflated with UI
    rebuild volume."""

    current_correlation_id: list[str | None] = [None]
    notified_targets: set[_Target] = set()

    def _target(scope_code: str, scope: ResourceScope) -> _Target:
        return (scope_code, scope.tenant_id, scope.organization_id, scope.entity_type, scope.entity_id)

    def _notify(scope_code: str, entity_type: str, entity_id: str, event: _TaskEvent) -> None:
        scope = ResourceScope(
            tenant_id=event.tenant_id,
            organization_id=event.organization_id,
            module_code=TASK_MODULE_CODE,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        target = _target(scope_code, scope)
        if target in notified_targets:
            return
        notified_targets.add(target)
        channel.notify(
            ViewInvalidationHint(
                scope=scope,
                category=TASK_CATEGORY,
                scope_code=scope_code,
                entity_type=entity_type,
                entity_id=entity_id,
            )
        )

    def handle_task_event(event: _TaskEvent, context: DomainEventContext) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified_targets.clear()

        project_id = getattr(event, "project_id", None) or ""
        organization_id = event.organization_id

        if isinstance(event, TaskAssignmentChanged):
            _notify(TASK_ASSIGNMENTS_SCOPE_CODE, "task", event.task_id, event)
            _notify(TASK_ASSIGNMENTS_SCOPE_CODE, "resource", event.resource_id, event)
            _notify(TASK_DETAIL_SCOPE_CODE, "task", event.task_id, event)
            return

        if isinstance(event, TaskDependencyChanged):
            _notify(TASK_DEPENDENCIES_SCOPE_CODE, "project", project_id, event)
            _notify(TASK_SCHEDULE_SCOPE_CODE, "project", project_id, event)
            _notify(TASK_DETAIL_SCOPE_CODE, "task", event.predecessor_task_id, event)
            _notify(TASK_DETAIL_SCOPE_CODE, "task", event.successor_task_id, event)
            return

        # All remaining classes carry task_id directly (Created/ProfileUpdated/
        # HierarchyChanged/StatusChanged/ProgressChanged/ScheduleChanged/Removed).
        task_id = getattr(event, "task_id", "") or ""
        _notify(TASK_LIST_SCOPE_CODE, "project", project_id, event)
        _notify(TASK_DETAIL_SCOPE_CODE, "task", task_id, event)
        _notify(DASHBOARD_TASK_METRICS_SCOPE_CODE, "organization", organization_id, event)
        if isinstance(event, (TaskHierarchyChanged, TaskScheduleChanged, TaskRemoved)):
            _notify(TASK_SCHEDULE_SCOPE_CODE, "project", project_id, event)

    return handle_task_event


__all__ = [
    "build_task_view_invalidation_handler",
    "TASK_CATEGORY",
    "TASK_MODULE_CODE",
    "TASK_LIST_SCOPE_CODE",
    "TASK_DETAIL_SCOPE_CODE",
    "TASK_SCHEDULE_SCOPE_CODE",
    "TASK_ASSIGNMENTS_SCOPE_CODE",
    "TASK_DEPENDENCIES_SCOPE_CODE",
    "DASHBOARD_TASK_METRICS_SCOPE_CODE",
]
