from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.core.modules.project_management.application.tasks.event_handlers.view_invalidation import (
    DASHBOARD_TASK_METRICS_SCOPE_CODE,
    TASK_ASSIGNMENTS_SCOPE_CODE,
    TASK_CATEGORY,
    TASK_DEPENDENCIES_SCOPE_CODE,
    TASK_DETAIL_SCOPE_CODE,
    TASK_LIST_SCOPE_CODE,
    TASK_PROFILE_SCOPE_CODE,
    TASK_SCHEDULE_SCOPE_CODE,
)
from src.core.shared.events.view_invalidation import (
    ExactOrganization,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)
from src.ui_qml.shared.adapters.scoped_view_invalidation_subscription import (
    ScopedViewInvalidationSubscription,
)


class TaskViewInvalidationAdapter(QObject):
    """The single QML-facing entry point for all Task ViewInvalidation hints
    (P45B-CLOSURE item 32): controllers/presenters connect to these signals
    instead of subscribing to any of the 9 Task DomainEvent classes directly.
    One instance is shared across every PM controller in a shell/workspace via
    the composition root (mirroring `TaskCommentViewInvalidationAdapter`'s own
    P44B precedent)."""

    taskListStale = Signal(str)  # project_id
    taskProfileStale = Signal(str)  # project_id (narrower: name/identity/existence only)
    taskDetailStale = Signal(str)  # task_id
    taskScheduleStale = Signal(str)  # project_id
    taskAssignmentsForTaskStale = Signal(str)  # task_id
    taskAssignmentsForResourceStale = Signal(str)  # resource_id
    taskDependenciesStale = Signal(str)  # project_id
    dashboardTaskMetricsStale = Signal(str)  # organization_id

    def __init__(
        self,
        *,
        channel: ViewInvalidationChannel | None,
        tenant_id: str,
        organization_id: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._subscription = ScopedViewInvalidationSubscription(channel=channel, on_hint=self._on_hint)
        self.set_active_scope(tenant_id=tenant_id, organization_id=organization_id)

    def set_active_scope(self, *, tenant_id: str, organization_id: str) -> None:
        self._subscription.replace_filter(
            ExactOrganization(tenant_id, organization_id) if tenant_id and organization_id else None
        )

    def _on_hint(self, hint: ViewInvalidationHint) -> None:
        if hint.category != TASK_CATEGORY:
            return
        entity_id = hint.entity_id or ""
        if hint.scope_code == TASK_LIST_SCOPE_CODE:
            self.taskListStale.emit(entity_id)
        elif hint.scope_code == TASK_PROFILE_SCOPE_CODE:
            self.taskProfileStale.emit(entity_id)
        elif hint.scope_code == TASK_DETAIL_SCOPE_CODE:
            self.taskDetailStale.emit(entity_id)
        elif hint.scope_code == TASK_SCHEDULE_SCOPE_CODE:
            self.taskScheduleStale.emit(entity_id)
        elif hint.scope_code == TASK_ASSIGNMENTS_SCOPE_CODE:
            if hint.entity_type == "resource":
                self.taskAssignmentsForResourceStale.emit(entity_id)
            else:
                self.taskAssignmentsForTaskStale.emit(entity_id)
        elif hint.scope_code == TASK_DEPENDENCIES_SCOPE_CODE:
            self.taskDependenciesStale.emit(entity_id)
        elif hint.scope_code == DASHBOARD_TASK_METRICS_SCOPE_CODE:
            self.dashboardTaskMetricsStale.emit(entity_id)

    def dispose(self) -> None:
        self._subscription.dispose()


__all__ = ["TaskViewInvalidationAdapter"]
