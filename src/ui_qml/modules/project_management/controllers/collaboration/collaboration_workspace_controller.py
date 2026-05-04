from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.core.platform.notifications.domain_events import domain_events
from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
    run_mutation,
    serialize_collaboration_collection_view_model,
    serialize_collaboration_overview_view_model,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectCollaborationWorkspacePresenter,
    ProjectManagementWorkspacePresenter,
)


class ProjectManagementCollaborationWorkspaceController(
    ProjectManagementWorkspaceControllerBase
):
    overviewChanged = Signal()
    notificationsChanged = Signal()
    inboxChanged = Signal()
    recentActivityChanged = Signal()
    activePresenceChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: ProjectManagementWorkspacePresenter | None = None,
        collaboration_workspace_presenter: ProjectCollaborationWorkspacePresenter
        | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or ProjectManagementWorkspacePresenter(
            "project_management.collaboration"
        )
        self._collaboration_workspace_presenter = (
            collaboration_workspace_presenter
            or ProjectCollaborationWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._notifications: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._inbox: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._recent_activity: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._active_presence: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._bind_domain_events()
        self.refresh()

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantMap", notify=notificationsChanged)
    def notifications(self) -> dict[str, object]:
        return self._notifications

    @Property("QVariantMap", notify=inboxChanged)
    def inbox(self) -> dict[str, object]:
        return self._inbox

    @Property("QVariantMap", notify=recentActivityChanged)
    def recentActivity(self) -> dict[str, object]:
        return self._recent_activity

    @Property("QVariantMap", notify=activePresenceChanged)
    def activePresence(self) -> dict[str, object]:
        return self._active_presence

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        try:
            self._set_error_message("")
            self._set_feedback_message("")
            self._set_workspace(
                serialize_workspace_view_model(
                    self._workspace_presenter.build_view_model()
                )
            )
            workspace_state = self._collaboration_workspace_presenter.build_workspace_state()
            self._set_overview(
                serialize_collaboration_overview_view_model(workspace_state.overview)
            )
            self._set_notifications(
                serialize_collaboration_collection_view_model(
                    workspace_state.notifications
                )
            )
            self._set_inbox(
                serialize_collaboration_collection_view_model(workspace_state.inbox)
            )
            self._set_recent_activity(
                serialize_collaboration_collection_view_model(
                    workspace_state.recent_activity
                )
            )
            self._set_active_presence(
                serialize_collaboration_collection_view_model(
                    workspace_state.active_presence
                )
            )
            self._set_empty_state(workspace_state.empty_state)
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    @Slot(str, result="QVariantMap")
    def markTaskRead(self, task_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._collaboration_workspace_presenter.mark_task_mentions_read(
                task_id
            ),
            success_message="Task mentions marked as read.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(
            "project",
            "project_tasks",
            "task_collaboration",
            scope_code="project_management",
        )
        self._subscribe_domain_signal(
            domain_events.approvals_changed,
            self._on_domain_event,
        )
        self._subscribe_domain_signal(
            domain_events.timesheet_periods_changed,
            self._on_domain_event,
        )

    def _on_domain_event(self, _payload: object) -> None:
        self._request_domain_refresh()

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_notifications(self, notifications: dict[str, object]) -> None:
        if notifications == self._notifications:
            return
        self._notifications = notifications
        self.notificationsChanged.emit()

    def _set_inbox(self, inbox: dict[str, object]) -> None:
        if inbox == self._inbox:
            return
        self._inbox = inbox
        self.inboxChanged.emit()

    def _set_recent_activity(self, recent_activity: dict[str, object]) -> None:
        if recent_activity == self._recent_activity:
            return
        self._recent_activity = recent_activity
        self.recentActivityChanged.emit()

    def _set_active_presence(self, active_presence: dict[str, object]) -> None:
        if active_presence == self._active_presence:
            return
        self._active_presence = active_presence
        self.activePresenceChanged.emit()


__all__ = ["ProjectManagementCollaborationWorkspaceController"]
