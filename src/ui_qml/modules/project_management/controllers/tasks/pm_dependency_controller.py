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
        self._dependencies_table_model = DynamicTableModel(self)
        self._dependencies: dict[str, object] = {
            "title": "", "subtitle": "", "emptyState": "", "items": []
        }
        self._task_id = ""
        self._dependencies.update({"searchText": "", "direction": "all", "dependencyType": "all",
                                   "page": 1, "pageSize": 25, "total": 0,
                                   "sortKey": "linkedTask", "sortDirection": "asc"})

    # ── Populate from workspace state ────────────────────────────────

    def _update(self, workspace_state: object) -> None:
        self._task_id = str(getattr(workspace_state, "selected_task_id", "") or "")
        self._set_dependency_task_options(
            serialize_selector_options(workspace_state.dependency_task_options)
        )
        self._set_dependency_type_options(
            serialize_selector_options(workspace_state.dependency_type_options)
        )
        if self._task_id:
            self._reload()

    def _reload(self, **changes) -> None:
        state = dict(self._dependencies)
        state.update(changes)
        if any(key not in {"page", "pageSize"} for key in changes): state["page"] = 1
        page = self._presenter.build_task_dependencies_page(
            task_id=self._task_id, search_text=str(state.get("searchText", "")),
            direction=str(state.get("direction", "all")),
            dependency_type=str(state.get("dependencyType", "all")),
            page=int(state.get("page", 1)), page_size=int(state.get("pageSize", 25)),
            sort_key=str(state.get("sortKey", "linkedTask")),
            sort_direction=str(state.get("sortDirection", "asc")))
        self._set_dependencies({"title": "Dependencies", "subtitle": f"{page['total']} matching relationship(s).",
                                "emptyState": "No dependencies match the selected filters.", **state, **page})

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

    @Property(QObject, constant=True)
    def dependenciesTableModel(self) -> DynamicTableModel:
        return self._dependencies_table_model

    @Slot(str)
    def setSearch(self, value: str) -> None: self._reload(searchText=str(value or "").strip())

    @Slot(str, str)
    def setFilters(self, direction: str, dependency_type: str) -> None:
        self._reload(direction=direction, dependencyType=dependency_type)

    @Slot(int)
    def setPage(self, value: int) -> None: self._reload(page=max(1, value))

    @Slot(int)
    def setPageSize(self, value: int) -> None: self._reload(pageSize=max(1, value), page=1)

    @Slot(str, int)
    def setSort(self, key: str, direction: int) -> None:
        from PySide6.QtCore import Qt
        self._reload(sortKey=key,
                     sortDirection="desc" if direction == Qt.DescendingOrder.value else "asc")

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

    @Slot("QVariantMap", result="QVariantMap")
    def updateDependency(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.update_dependency(dict(payload)),
            success_message="Dependency updated.",
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

    # ── Non-persisting impact preview (Phase N/N9) ─────────────────────
    # QML performs zero schedule calculation -- every preview here comes
    # straight from the same canonical CPM engine the committed schedule
    # uses. These are reads, not mutations: no busy toggling, no facade
    # refresh, no success/error feedback message plumbing.

    @Slot("QVariantMap", result="QVariantMap")
    def previewCreateDependency(self, payload: dict[str, object]) -> dict[str, object]:
        try:
            return self._presenter.preview_create_dependency(dict(payload))
        except Exception:
            return {"available": False, "isValid": True, "code": "", "summary": "",
                    "detail": "", "riskLevel": "unknown", "affectedTaskCount": 0,
                    "largestShiftDays": 0, "rows": [], "suggestions": []}

    @Slot("QVariantMap", result="QVariantMap")
    def previewUpdateDependency(self, payload: dict[str, object]) -> dict[str, object]:
        try:
            return self._presenter.preview_update_dependency(dict(payload))
        except Exception:
            return {"available": False, "isValid": True, "code": "", "summary": "",
                    "detail": "", "riskLevel": "unknown", "affectedTaskCount": 0,
                    "largestShiftDays": 0, "rows": [], "suggestions": []}

    @Slot(str, result="QVariantMap")
    def previewDeleteDependency(self, dependency_id: str) -> dict[str, object]:
        try:
            return self._presenter.preview_delete_dependency(dependency_id)
        except Exception:
            return {"available": False, "isValid": True, "code": "", "summary": "",
                    "detail": "", "riskLevel": "unknown", "affectedTaskCount": 0,
                    "largestShiftDays": 0, "rows": [], "suggestions": []}

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
        self._dependencies_table_model.set_rows(v.get("items", []))
        self.dependenciesChanged.emit()


__all__ = ["PMDependencyController"]
