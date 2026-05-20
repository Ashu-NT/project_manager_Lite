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


class PMDependencyController(QObject):
    """Owns dependency domain data and dependency mutations."""

    dependencyTaskOptionsChanged = Signal()
    dependencyTypeOptionsChanged = Signal()
    dependenciesChanged = Signal()

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
        self._dependency_task_options: list[dict[str, str]] = []
        self._dependency_type_options: list[dict[str, str]] = []
        self._dependencies: dict[str, object] = {
            "title": "", "subtitle": "", "emptyState": "", "items": []
        }

    # ── Populate from workspace state ────────────────────────────────

    def _update(self, workspace_state: object) -> None:
        self._set_dependency_task_options(
            serialize_selector_options(workspace_state.dependency_task_options)
        )
        self._set_dependency_type_options(
            serialize_selector_options(workspace_state.dependency_type_options)
        )
        self._set_dependencies(
            serialize_task_collection_view_model(workspace_state.dependencies)
        )

    # ── Properties ───────────────────────────────────────────────────

    @Property("QVariantList", notify=dependencyTaskOptionsChanged)
    def dependencyTaskOptions(self) -> list[dict[str, str]]:
        return self._dependency_task_options

    @Property("QVariantList", notify=dependencyTypeOptionsChanged)
    def dependencyTypeOptions(self) -> list[dict[str, str]]:
        return self._dependency_type_options

    @Property("QVariantMap", notify=dependenciesChanged)
    def dependencies(self) -> dict[str, object]:
        return self._dependencies

    # ── Mutation slots ────────────────────────────────────────────────

    @Slot("QVariantMap", result="QVariantMap")
    def createDependency(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.create_dependency(dict(payload)),
            success_message="Dependency created.",
            on_success=self._facade_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deleteDependency(self, dependency_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.delete_dependency(dependency_id),
            success_message="Dependency removed.",
            on_success=self._facade_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    # ── Private setters ───────────────────────────────────────────────

    def _set_dependency_task_options(self, v: list) -> None:
        if v == self._dependency_task_options:
            return
        self._dependency_task_options = v
        self.dependencyTaskOptionsChanged.emit()

    def _set_dependency_type_options(self, v: list) -> None:
        if v == self._dependency_type_options:
            return
        self._dependency_type_options = v
        self.dependencyTypeOptionsChanged.emit()

    def _set_dependencies(self, v: dict) -> None:
        if v == self._dependencies:
            return
        self._dependencies = v
        self.dependenciesChanged.emit()


__all__ = ["PMDependencyController"]
