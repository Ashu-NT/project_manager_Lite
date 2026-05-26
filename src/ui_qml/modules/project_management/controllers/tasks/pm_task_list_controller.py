from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementUndoCommand,
    ProjectManagementUndoStack,
    run_mutation,
    serialize_selector_options,
    serialize_task_catalog_overview_view_model,
    serialize_task_detail_view_model,
    serialize_task_record_view_models,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectTasksWorkspacePresenter,
)


class PMTaskListController(QObject):
    """Owns task-list domain data, bulk selection, and task mutations."""

    overviewChanged = Signal()
    projectOptionsChanged = Signal()
    statusOptionsChanged = Signal()
    bulkStatusOptionsChanged = Signal()
    priorityOptionsChanged = Signal()
    scheduleOptionsChanged = Signal()
    tasksChanged = Signal()
    selectedTaskChanged = Signal()
    selectedTaskIdsChanged = Signal()
    selectedTaskCountChanged = Signal()
    selectedTaskDoneCountChanged = Signal()
    taskActionHistoryChanged = Signal()

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
        self._task_action_history = ProjectManagementUndoStack(max_depth=25)
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._project_options: list[dict[str, str]] = []
        self._status_options: list[dict[str, str]] = []
        self._bulk_status_options: list[dict[str, str]] = []
        self._priority_options: list[dict[str, str]] = []
        self._schedule_options: list[dict[str, str]] = []
        self._tasks: dict[str, object] = {
            "title": "", "subtitle": "", "emptyState": "", "items": []
        }
        self._selected_task: dict[str, object] = {
            "id": "", "title": "", "statusLabel": "", "subtitle": "",
            "description": "", "emptyState": "", "fields": [], "state": {},
        }
        self._selected_task_ids: list[str] = []
        self._selected_task_count = 0
        self._selected_task_done_count = 0

    # ── Populate from workspace state ────────────────────────────────

    def _update(self, workspace_state: object) -> None:
        self._set_overview(
            serialize_task_catalog_overview_view_model(workspace_state.overview)
        )
        self._set_project_options(
            serialize_selector_options(workspace_state.project_options)
        )
        self._set_status_options(
            serialize_selector_options(workspace_state.status_options)
        )
        self._set_bulk_status_options(
            serialize_selector_options(workspace_state.bulk_status_options)
        )
        self._set_priority_options(
            serialize_selector_options(workspace_state.priority_options)
        )
        self._set_schedule_options(
            serialize_selector_options(workspace_state.schedule_options)
        )
        items = serialize_task_record_view_models(workspace_state.tasks)
        self._reconcile_task_bulk_selection(items)
        self._set_tasks({
            "title": "Task Catalog",
            "subtitle": (
                "Edit delivery tasks, progress, and execution priorities."
            ),
            "emptyState": workspace_state.empty_state,
            "items": items,
        })
        self._set_selected_task(
            serialize_task_detail_view_model(workspace_state.selected_task_detail)
        )

    def updateSelectedTaskOnly(self, workspace_state: object) -> None:
        self._set_selected_task(
            serialize_task_detail_view_model(workspace_state.selected_task_detail)
        )

    def selectTaskPreview(self, task_id: str) -> None:
        normalized = (task_id or "").strip()
        if not normalized:
            return
        preview = self._build_task_preview(normalized)
        if preview is not None:
            self._set_selected_task(preview)

    # ── Properties ───────────────────────────────────────────────────

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=projectOptionsChanged)
    def projectOptions(self) -> list[dict[str, str]]:
        return self._project_options

    @Property("QVariantList", notify=statusOptionsChanged)
    def statusOptions(self) -> list[dict[str, str]]:
        return self._status_options

    @Property("QVariantList", notify=bulkStatusOptionsChanged)
    def bulkStatusOptions(self) -> list[dict[str, str]]:
        return self._bulk_status_options

    @Property("QVariantList", notify=priorityOptionsChanged)
    def priorityOptions(self) -> list[dict[str, str]]:
        return self._priority_options

    @Property("QVariantList", notify=scheduleOptionsChanged)
    def scheduleOptions(self) -> list[dict[str, str]]:
        return self._schedule_options

    @Property("QVariantMap", notify=tasksChanged)
    def tasks(self) -> dict[str, object]:
        return self._tasks

    @Property("QVariantMap", notify=selectedTaskChanged)
    def selectedTask(self) -> dict[str, object]:
        return self._selected_task

    @Property("QVariantList", notify=selectedTaskIdsChanged)
    def selectedTaskIds(self) -> list[str]:
        return list(self._selected_task_ids)

    @Property(int, notify=selectedTaskCountChanged)
    def selectedTaskCount(self) -> int:
        return self._selected_task_count

    @Property(int, notify=selectedTaskDoneCountChanged)
    def selectedTaskDoneCount(self) -> int:
        return self._selected_task_done_count

    @Property(bool, notify=taskActionHistoryChanged)
    def canUndoTaskAction(self) -> bool:
        return self._task_action_history.can_undo()

    @Property(bool, notify=taskActionHistoryChanged)
    def canRedoTaskAction(self) -> bool:
        return self._task_action_history.can_redo()

    @Property(str, notify=taskActionHistoryChanged)
    def nextUndoLabel(self) -> str:
        return self._task_action_history.next_undo_label() or ""

    @Property(str, notify=taskActionHistoryChanged)
    def nextRedoLabel(self) -> str:
        return self._task_action_history.next_redo_label() or ""

    # ── Bulk-selection slots ──────────────────────────────────────────

    @Slot(str, bool)
    def setTaskBulkSelection(self, task_id: str, selected: bool) -> None:
        normalized = (task_id or "").strip()
        if not normalized:
            return
        current = list(self._selected_task_ids)
        if selected:
            if normalized not in current:
                current.append(normalized)
        else:
            current = [tid for tid in current if tid != normalized]
        self._set_selected_task_ids(current)
        self._sync_selected_task_stats(self._tasks.get("items", []))

    @Slot()
    def selectVisibleTasks(self) -> None:
        ids = [
            str(item.get("id", "") or "").strip()
            for item in self._tasks.get("items", [])
            if str(item.get("id", "") or "").strip()
        ]
        self._set_selected_task_ids(ids)
        self._sync_selected_task_stats(self._tasks.get("items", []))

    @Slot()
    def clearTaskBulkSelection(self) -> None:
        if not self._selected_task_ids:
            return
        self._set_selected_task_ids([])
        self._sync_selected_task_stats(self._tasks.get("items", []))

    # ── Mutation slots ────────────────────────────────────────────────

    @Slot("QVariantMap", result="QVariantMap")
    def createTask(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.create_task(dict(payload)),
            success_message="Task created.",
            on_success=self._facade_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateTask(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.update_task(dict(payload)),
            success_message="Task updated.",
            on_success=self._facade_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateProgress(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.update_progress(dict(payload)),
            success_message="Task progress updated.",
            on_success=self._facade_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deleteTask(self, task_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.delete_task(task_id),
            success_message="Task deleted.",
            on_success=self._facade_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def applyBulkStatus(self, payload: dict[str, object]) -> dict[str, object]:
        merged = dict(payload)
        merged.setdefault("taskIds", list(self._selected_task_ids))
        history_command = self._build_bulk_status_history_command(merged)
        return run_mutation(
            operation=lambda: self._presenter.apply_bulk_status(merged),
            success_message="Bulk task status applied.",
            on_success=lambda: self._on_bulk_status_success(history_command),
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantList", result="QVariantMap")
    def bulkDeleteTasks(self, task_ids: list[object]) -> dict[str, object]:
        normalized_ids = [
            str(tid or "").strip() for tid in task_ids if str(tid or "").strip()
        ]
        return run_mutation(
            operation=lambda: self._presenter.bulk_delete_tasks(normalized_ids),
            success_message="Selected tasks deleted.",
            on_success=lambda: (self.clearTaskBulkSelection(), self._facade_refresh()),
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(result="QVariantMap")
    def undoLastTaskAction(self) -> dict[str, object]:
        if not self._task_action_history.can_undo():
            return {"ok": False, "message": "Nothing to undo."}
        label = self._task_action_history.next_undo_label() or "task action"
        return run_mutation(
            operation=self._undo_task_action,
            success_message=f"Undid {label}.",
            on_success=self._facade_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(result="QVariantMap")
    def redoLastTaskAction(self) -> dict[str, object]:
        if not self._task_action_history.can_redo():
            return {"ok": False, "message": "Nothing to redo."}
        label = self._task_action_history.next_redo_label() or "task action"
        return run_mutation(
            operation=self._redo_task_action,
            success_message=f"Redid {label}.",
            on_success=self._facade_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    # ── Private helpers ───────────────────────────────────────────────

    def _reconcile_task_bulk_selection(self, task_items: list[dict]) -> None:
        visible_ids = {
            str(item.get("id", "") or "").strip()
            for item in task_items
            if str(item.get("id", "") or "").strip()
        }
        reconciled = [tid for tid in self._selected_task_ids if tid in visible_ids]
        self._set_selected_task_ids(reconciled)
        self._sync_selected_task_stats(task_items)

    def _sync_selected_task_stats(self, task_items: list[dict]) -> None:
        selected_ids = set(self._selected_task_ids)
        count = len(selected_ids)
        done_count = sum(
            1
            for item in task_items
            if str(item.get("id", "") or "").strip() in selected_ids
            and str(
                (item.get("state", {}) if isinstance(item.get("state"), dict) else {}).get(
                    "status", ""
                ) or ""
            ).strip().upper() == "DONE"
        )
        self._set_selected_task_count(count)
        self._set_selected_task_done_count(done_count)

    def _on_bulk_status_success(
        self, history_command: ProjectManagementUndoCommand | None
    ) -> None:
        if history_command is not None:
            self._task_action_history.record(history_command)
            self.taskActionHistoryChanged.emit()
        self._facade_refresh()

    def _undo_task_action(self) -> None:
        self._task_action_history.undo()
        self.taskActionHistoryChanged.emit()

    def _redo_task_action(self) -> None:
        self._task_action_history.redo()
        self.taskActionHistoryChanged.emit()

    def _build_bulk_status_history_command(
        self, payload: dict[str, object]
    ) -> ProjectManagementUndoCommand | None:
        target_status = str(payload.get("status", "") or "").strip().upper()
        raw_ids = payload.get("taskIds", []) or []
        task_ids = [str(tid or "").strip() for tid in raw_ids if str(tid or "").strip()]
        if not target_status or not task_ids:
            return None
        items_by_id = {
            str(item.get("id", "") or "").strip(): item
            for item in self._tasks.get("items", [])
            if str(item.get("id", "") or "").strip()
        }
        changes: list[tuple[str, str, str]] = []
        for task_id in task_ids:
            item = items_by_id.get(task_id)
            if item is None:
                continue
            state = item.get("state", {})
            if not isinstance(state, dict):
                continue
            current = str(state.get("status", "") or "").strip().upper()
            if not current or current == target_status:
                continue
            changes.append((task_id, current, target_status))
        if not changes:
            return None
        reopen_pct = payload.get("reopenPercentComplete", "")

        def _apply(task_changes: list[tuple[str, str, str]], direction: int) -> None:
            grouped: dict[str, list[str]] = {}
            for tid, old_s, new_s in task_changes:
                status = old_s if direction == 0 else new_s
                grouped.setdefault(status, []).append(tid)
            for status, grouped_ids in grouped.items():
                mut: dict[str, object] = {"taskIds": grouped_ids, "status": status}
                if (
                    direction == 1
                    and status == "IN_PROGRESS"
                    and reopen_pct not in ("", None)
                    and any(
                        old == "DONE" and new == "IN_PROGRESS"
                        for _, old, new in task_changes
                    )
                ):
                    mut["reopenPercentComplete"] = reopen_pct
                self._presenter.apply_bulk_status(mut)

        label = (
            f"Bulk status -> {target_status.replace('_', ' ').title()} "
            f"({len(changes)} task(s))"
        )
        return ProjectManagementUndoCommand(
            label=label,
            redo=lambda: _apply(changes, 1),
            undo=lambda: _apply(changes, 0),
        )

    def _build_task_preview(self, task_id: str) -> dict[str, object] | None:
        selected_item = next(
            (
                item
                for item in self._tasks.get("items", [])
                if str(item.get("id", "") or "").strip() == task_id
            ),
            None,
        )
        if selected_item is None:
            return None
        state = (
            dict(selected_item.get("state", {}))
            if isinstance(selected_item.get("state"), dict)
            else {}
        )
        return {
            "id": task_id,
            "title": str(selected_item.get("title", "") or ""),
            "statusLabel": str(selected_item.get("statusLabel", "") or ""),
            "subtitle": str(selected_item.get("subtitle", "") or ""),
            "description": "",
            "emptyState": "",
            "fields": [
                {
                    "label": "Project",
                    "value": str(state.get("projectName", "") or "—"),
                    "supportingText": "",
                },
                {
                    "label": "Start",
                    "value": str(state.get("startDateLabel", "") or "—"),
                    "supportingText": "",
                },
                {
                    "label": "Finish",
                    "value": str(state.get("endDateLabel", "") or "—"),
                    "supportingText": "",
                },
                {
                    "label": "Priority",
                    "value": str(state.get("priorityLabel", "") or "—"),
                    "supportingText": "",
                },
            ],
            "state": state,
        }

    # ── Private setters ───────────────────────────────────────────────

    def _set_overview(self, v: dict) -> None:
        if v == self._overview:
            return
        self._overview = v
        self.overviewChanged.emit()

    def _set_project_options(self, v: list) -> None:
        if v == self._project_options:
            return
        self._project_options = v
        self.projectOptionsChanged.emit()

    def _set_status_options(self, v: list) -> None:
        if v == self._status_options:
            return
        self._status_options = v
        self.statusOptionsChanged.emit()

    def _set_bulk_status_options(self, v: list) -> None:
        if v == self._bulk_status_options:
            return
        self._bulk_status_options = v
        self.bulkStatusOptionsChanged.emit()

    def _set_priority_options(self, v: list) -> None:
        if v == self._priority_options:
            return
        self._priority_options = v
        self.priorityOptionsChanged.emit()

    def _set_schedule_options(self, v: list) -> None:
        if v == self._schedule_options:
            return
        self._schedule_options = v
        self.scheduleOptionsChanged.emit()

    def _set_tasks(self, v: dict) -> None:
        if v == self._tasks:
            return
        self._tasks = v
        self.tasksChanged.emit()

    def _set_selected_task(self, v: dict) -> None:
        if v == self._selected_task:
            return
        self._selected_task = v
        self.selectedTaskChanged.emit()

    def _set_selected_task_ids(self, v: list[str]) -> None:
        normalized = [str(tid or "").strip() for tid in v if str(tid or "").strip()]
        if normalized == self._selected_task_ids:
            return
        self._selected_task_ids = normalized
        self.selectedTaskIdsChanged.emit()

    def _set_selected_task_count(self, v: int) -> None:
        if v == self._selected_task_count:
            return
        self._selected_task_count = v
        self.selectedTaskCountChanged.emit()

    def _set_selected_task_done_count(self, v: int) -> None:
        if v == self._selected_task_done_count:
            return
        self._selected_task_done_count = v
        self.selectedTaskDoneCountChanged.emit()


__all__ = ["PMTaskListController"]
