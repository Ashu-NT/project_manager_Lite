from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.modules.project_management.controllers.common import (
    run_mutation,
    serialize_selector_options,
    serialize_task_collection_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectTasksWorkspacePresenter,
)


class PMAssignmentController(QObject):
    """Owns assignment domain data and assignment mutations."""

    assignmentOptionsChanged = Signal()
    assignmentsChanged = Signal()

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
        self._assignment_options: list[dict[str, str]] = []
        self._assignments: dict[str, object] = {
            "title": "", "subtitle": "", "emptyState": "", "items": []
        }

    # ── Populate from workspace state ────────────────────────────────

    def _update(self, workspace_state: object) -> None:
        self._set_assignment_options(
            serialize_selector_options(workspace_state.assignment_options)
        )
        self._set_assignments(
            serialize_task_collection_view_model(workspace_state.assignments)
        )

    # ── Properties ───────────────────────────────────────────────────

    @Property("QVariantList", notify=assignmentOptionsChanged)
    def assignmentOptions(self) -> list[dict[str, str]]:
        return self._assignment_options

    @Property("QVariantMap", notify=assignmentsChanged)
    def assignments(self) -> dict[str, object]:
        return self._assignments

    # ── Mutation slots ────────────────────────────────────────────────

    @Slot("QVariantMap", result="QVariantMap")
    def createAssignment(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.create_assignment(dict(payload)),
            success_message="Assignment created.",
            on_success=self._facade_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateAssignmentAllocation(
        self, payload: dict[str, object]
    ) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.update_assignment_allocation(
                dict(payload)
            ),
            success_message="Assignment allocation updated.",
            on_success=self._facade_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def setAssignmentHours(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.set_assignment_hours(dict(payload)),
            success_message="Assignment effort updated.",
            on_success=self._facade_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deleteAssignment(self, assignment_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.delete_assignment(assignment_id),
            success_message="Assignment removed.",
            on_success=self._facade_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def validateAssignment(self, payload: dict[str, object]) -> dict[str, object]:
        try:
            return self._presenter.validate_assignment(dict(payload))
        except Exception as exc:
            return {
                "ok": False,
                "isValid": True,
                "canAssign": True,
                "requiresApproval": False,
                "isBlocked": False,
                "hasWarnings": False,
                "violationMessages": [],
                "warningMessages": [],
                "summary": str(exc),
            }

    # ── Private setters ───────────────────────────────────────────────

    def _set_assignment_options(self, v: list) -> None:
        if v == self._assignment_options:
            return
        self._assignment_options = v
        self.assignmentOptionsChanged.emit()

    def _set_assignments(self, v: dict) -> None:
        if v == self._assignments:
            return
        self._assignments = v
        self.assignmentsChanged.emit()


__all__ = ["PMAssignmentController"]
