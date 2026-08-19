from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.shared.models.data_table_model import DynamicTableModel

from src.ui_qml.modules.project_management.controllers.common import (
    run_mutation,
    serialize_selector_options,
    serialize_task_collection_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectTasksWorkspacePresenter,
)
from src.ui_qml.modules.project_management.presenters.tasks.assignment_mapper import (
    to_assignment_table_row,
)

_EMPTY_ASSIGNMENT_PREVIEW: dict[str, object] = {
    "ok": True,
    "overallocationPct": 0.0,
    "conflictProjects": [],
    "skillsMatched": True,
    "certsValid": True,
    "hasWarnings": False,
    "warningMessages": [],
    "isBlocked": False,
    "blockMessages": [],
    "capacityKnown": False,
    "availableCapacityHoursLabel": "",
    "existingCommittedHoursLabel": "",
    "proposedCommittedHoursLabel": "",
    "resultingCommittedHoursLabel": "",
    "peakUtilizationPercent": 0.0,
    "capacityStatus": "UNKNOWN",
    "capacityStatusLabel": "Capacity unknown",
    "conflictDateLabels": [],
}


class PMAssignmentController(QObject):
    """Owns assignment domain data and assignment mutations."""

    assignmentOptionsChanged = Signal()
    assignmentsChanged = Signal()
    taskSkillRequirementsChanged = Signal()
    assignmentPreviewChanged = Signal()
    projectResourceUsageChanged = Signal()

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
        self._assignments_table_model = DynamicTableModel(self)
        self._assignments: dict[str, object] = {
            "title": "", "subtitle": "", "emptyState": "", "items": []
        }
        self._task_skill_requirements: dict[str, object] = {
            "title": "Skill Requirements",
            "subtitle": "",
            "emptyState": "Select a task to review skill and certification requirements.",
            "items": [],
        }
        self._assignment_preview: dict[str, object] = dict(_EMPTY_ASSIGNMENT_PREVIEW)
        self._project_resource_usage: dict[str, object] | None = None

    # ── Populate from workspace state ────────────────────────────────

    def _update(self, workspace_state: object) -> None:
        self._set_assignment_options(
            serialize_selector_options(workspace_state.assignment_options)
        )
        self._set_assignments(
            serialize_task_collection_view_model(workspace_state.assignments)
        )
        self._assignments_table_model.set_rows(
            [
                to_assignment_table_row(item)
                for item in workspace_state.assignments.items
            ]
        )

    # ── Properties ───────────────────────────────────────────────────

    @Property("QVariantList", notify=assignmentOptionsChanged)
    def assignmentOptions(self) -> list[dict[str, str]]:
        return self._assignment_options

    @Property("QVariantMap", notify=assignmentsChanged)
    def assignments(self) -> dict[str, object]:
        return self._assignments

    @Property(QObject, constant=True)
    def assignmentsTableModel(self) -> DynamicTableModel:
        return self._assignments_table_model

    @Property("QVariantMap", notify=taskSkillRequirementsChanged)
    def taskSkillRequirements(self) -> dict[str, object]:
        return self._task_skill_requirements

    @Property("QVariantMap", notify=assignmentPreviewChanged)
    def assignmentPreview(self) -> dict[str, object]:
        return self._assignment_preview

    @Property("QVariantMap", notify=projectResourceUsageChanged)
    def projectResourceUsage(self) -> dict[str, object]:
        return self._project_resource_usage or {}

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
    def updateAssignmentPlannedHours(
        self, payload: dict[str, object]
    ) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.update_assignment_planned_hours(
                dict(payload)
            ),
            success_message="Planned work updated.",
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

    @Slot(str, result="QVariantMap")
    def acceptAssignment(self, assignment_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.accept_assignment(assignment_id),
            success_message="Assignment accepted.",
            on_success=self._facade_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def declineAssignment(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.decline_assignment(dict(payload)),
            success_message="Assignment declined.",
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
                "isValid": False,
                "canAssign": False,
                "requiresApproval": False,
                "isBlocked": True,
                "hasWarnings": False,
                "violationMessages": [str(exc)],
                "warningMessages": [],
                "summary": str(exc),
            }

    @Slot("QVariantMap", result="QVariantMap")
    def previewAssignment(self, payload: dict[str, object]) -> dict[str, object]:
        try:
            result = self._presenter.preview_assignment(dict(payload))
        except Exception as exc:
            result = dict(_EMPTY_ASSIGNMENT_PREVIEW)
            result.update({
                "ok": False,
                "skillsMatched": False,
                "certsValid": False,
                "isBlocked": True,
                "blockMessages": [str(exc)],
            })
        self._set_assignment_preview(result)
        return result

    @Slot()
    def clearAssignmentPreview(self) -> None:
        self._set_assignment_preview(dict(_EMPTY_ASSIGNMENT_PREVIEW))

    @Slot(str)
    def loadProjectResourceUsage(self, project_resource_id: str) -> None:
        """Project Resource Context for the inspector (docs §44 follow-up)
        -- fetched alongside the capacity preview when a row is selected,
        not calculated in QML."""
        try:
            usage = self._presenter.get_project_resource_usage(project_resource_id)
        except Exception:
            usage = None
        self._project_resource_usage = usage
        self.projectResourceUsageChanged.emit()

    @Slot()
    def clearProjectResourceUsage(self) -> None:
        self._project_resource_usage = None
        self.projectResourceUsageChanged.emit()

    # ── Skill requirements update (separate from assignments/_update) ─

    def _update_skill_requirements(self, workspace_state: object) -> None:
        self._set_task_skill_requirements(
            serialize_task_collection_view_model(
                workspace_state.task_skill_requirements
            )
        )

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
        self._assignments_table_model.set_rows(v.get("items", []))
        self.assignmentsChanged.emit()

    def _set_task_skill_requirements(self, v: dict) -> None:
        if v == self._task_skill_requirements:
            return
        self._task_skill_requirements = v
        self.taskSkillRequirementsChanged.emit()

    def _set_assignment_preview(self, v: dict) -> None:
        self._assignment_preview = v
        self.assignmentPreviewChanged.emit()


__all__ = ["PMAssignmentController"]
