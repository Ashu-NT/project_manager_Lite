from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.modules.project_management.controllers.common import (
    run_mutation,
    serialize_collaboration_collection_view_model,
    serialize_selector_options,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectTasksWorkspacePresenter,
)


class PMCollaborationController(QObject):
    """Owns collaboration domain data, presence management, and comment mutations."""

    collaborationMentionOptionsChanged = Signal()
    collaborationDocumentOptionsChanged = Signal()
    collaborationCommentsChanged = Signal()
    collaborationPresenceChanged = Signal()

    def __init__(
        self,
        *,
        presenter: ProjectTasksWorkspacePresenter,
        facade_refresh: Callable[[], None],
        set_is_busy: Callable[[bool], None],
        set_error_message: Callable[[str], None],
        set_feedback_message: Callable[[str], None],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._facade_refresh = facade_refresh
        self._set_is_busy = set_is_busy
        self._set_error_message = set_error_message
        self._set_feedback_message = set_feedback_message
        self._presence_session_task_id = ""
        self._presence_session_activity = ""
        self._presence_override_task_id = ""
        self._last_selected_task_id = ""
        self._collaboration_mention_options: list[dict[str, str]] = []
        self._collaboration_document_options: list[dict[str, str]] = []
        self._collaboration_comments: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._collaboration_presence: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }

    def _update(self, workspace_state: object) -> None:
        self._set_collaboration_mention_options(
            serialize_selector_options(workspace_state.collaboration_mention_options)
        )
        self._set_collaboration_document_options(
            serialize_selector_options(workspace_state.collaboration_document_options)
        )
        self._set_collaboration_comments(
            serialize_collaboration_collection_view_model(
                workspace_state.collaboration_comments
            )
        )
        self._set_collaboration_presence(
            serialize_collaboration_collection_view_model(
                workspace_state.collaboration_presence
            )
        )

    def sync_review_presence(self, selected_task_id: str) -> None:
        self._last_selected_task_id = (selected_task_id or "").strip()
        if self._presence_override_task_id:
            return
        if self._last_selected_task_id:
            self._set_task_presence(self._last_selected_task_id, "reviewing")
            return
        self._clear_current_task_presence()

    def on_destroyed_cleanup(self, *_args: object) -> None:
        try:
            self._presence_override_task_id = ""
            self._clear_current_task_presence()
        except Exception:
            pass

    @Property("QVariantList", notify=collaborationMentionOptionsChanged)
    def collaborationMentionOptions(self) -> list[dict[str, str]]:
        return self._collaboration_mention_options

    @Property("QVariantList", notify=collaborationDocumentOptionsChanged)
    def collaborationDocumentOptions(self) -> list[dict[str, str]]:
        return self._collaboration_document_options

    @Property("QVariantMap", notify=collaborationCommentsChanged)
    def collaborationComments(self) -> dict[str, object]:
        return self._collaboration_comments

    @Property("QVariantMap", notify=collaborationPresenceChanged)
    def collaborationPresence(self) -> dict[str, object]:
        return self._collaboration_presence

    @Slot(str, str, result="QVariantMap")
    def beginTaskPresence(self, task_id: str, activity: str) -> dict[str, object]:
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id:
            return {
                "ok": False,
                "message": "Task ID is required to start a presence session.",
            }
        normalized_activity = (activity or "").strip() or "reviewing"
        previous_override = self._presence_override_task_id
        try:
            self._presence_override_task_id = normalized_task_id
            self._set_task_presence(normalized_task_id, normalized_activity)
            return {"ok": True, "message": ""}
        except Exception as exc:  # pragma: no cover
            self._presence_override_task_id = previous_override
            self._set_error_message(str(exc))
            return {"ok": False, "message": str(exc)}

    @Slot(str, result="QVariantMap")
    def endTaskPresence(self, task_id: str) -> dict[str, object]:
        normalized_task_id = (task_id or "").strip()
        try:
            if (
                normalized_task_id
                and normalized_task_id == self._presence_override_task_id
            ):
                self._presence_override_task_id = ""
            self.sync_review_presence(self._last_selected_task_id)
            return {"ok": True, "message": ""}
        except Exception as exc:  # pragma: no cover
            self._set_error_message(str(exc))
            return {"ok": False, "message": str(exc)}

    @Slot("QVariantMap", result="QVariantMap")
    def postTaskComment(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.post_task_comment(dict(payload)),
            success_message="Task collaboration update posted.",
            on_success=self._facade_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def markTaskCollaborationRead(self, task_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.mark_task_collaboration_read(task_id),
            success_message="Task collaboration mentions marked as read.",
            on_success=self._facade_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _set_task_presence(self, task_id: str, activity: str) -> None:
        norm_id = (task_id or "").strip()
        norm_act = (activity or "").strip() or "reviewing"
        if not norm_id:
            self._clear_current_task_presence()
            return
        if (
            norm_id == self._presence_session_task_id
            and norm_act == self._presence_session_activity
        ):
            return
        # Keep presence updates on the controller path because the presenter
        # reuses the app-scoped service graph and shared ORM session.
        if self._presence_session_task_id and (
            self._presence_session_task_id != norm_id
            or self._presence_session_activity != norm_act
        ):
            old_id = self._presence_session_task_id
            self._presence_session_task_id = ""
            self._presence_session_activity = ""
            self._presenter.clear_task_collaboration_presence(old_id)
        self._presenter.touch_task_collaboration_presence(
            norm_id,
            activity=norm_act,
        )
        self._presence_session_task_id = norm_id
        self._presence_session_activity = norm_act

    def _clear_current_task_presence(self) -> None:
        if not self._presence_session_task_id:
            return
        clear_id = self._presence_session_task_id
        self._presence_session_task_id = ""
        self._presence_session_activity = ""
        self._presenter.clear_task_collaboration_presence(clear_id)

    def _set_collaboration_mention_options(self, v: list) -> None:
        if v == self._collaboration_mention_options:
            return
        self._collaboration_mention_options = v
        self.collaborationMentionOptionsChanged.emit()

    def _set_collaboration_document_options(self, v: list) -> None:
        if v == self._collaboration_document_options:
            return
        self._collaboration_document_options = v
        self.collaborationDocumentOptionsChanged.emit()

    def _set_collaboration_comments(self, v: dict) -> None:
        if v == self._collaboration_comments:
            return
        self._collaboration_comments = v
        self.collaborationCommentsChanged.emit()

    def _set_collaboration_presence(self, v: dict) -> None:
        if v == self._collaboration_presence:
            return
        self._collaboration_presence = v
        self.collaborationPresenceChanged.emit()


__all__ = ["PMCollaborationController"]
