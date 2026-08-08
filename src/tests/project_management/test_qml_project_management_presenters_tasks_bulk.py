from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QSettings

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementTaskViewStore,
)
from src.core.modules.project_management.api.desktop import (
    build_project_management_collaboration_desktop_api,
    build_project_management_tasks_desktop_api,
)
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.modules.project_management.domain.enums import (
    DependencyType,
    TaskStatus,
)
from src.core.platform.domain.master_data.documents import DocumentStorageKind


class _FakePmRuntimeApi:
    def __init__(self, organization_id: str | None = "org-1") -> None:
        self._organization_id = organization_id

    def get_runtime_context(self) -> DesktopApiResult[SimpleNamespace]:
        organization = (
            SimpleNamespace(id=self._organization_id)
            if self._organization_id is not None
            else None
        )
        return DesktopApiResult(
            ok=True,
            data=SimpleNamespace(active_organization=organization),
        )


class _FakeCollaborationService:
    def __init__(self) -> None:
        self.marked_task_ids: list[str] = []
        self.posted_comments: list[dict[str, object]] = []
        self.touched_presence: list[tuple[str, str]] = []
        self.cleared_presence: list[str] = []
        self._comments: list[SimpleNamespace] = []
        self._comment_documents: dict[str, list[SimpleNamespace]] = {}

    def list_workspace_snapshot(self, *, limit: int = 200) -> SimpleNamespace:
        return SimpleNamespace(notifications=[], inbox=[], recent_activity=[], active_presence=[])

    def mark_task_mentions_read(self, task_id: str) -> None:
        self.marked_task_ids.append(task_id)

    def list_comments(self, task_id: str) -> list[SimpleNamespace]:
        return [c for c in self._comments if c.task_id == task_id]

    def list_comment_documents(self, task_id: str) -> dict[str, list[SimpleNamespace]]:
        comment_ids = {c.id for c in self.list_comments(task_id)}
        return {cid: list(docs) for cid, docs in self._comment_documents.items() if cid in comment_ids}

    def list_mention_candidates(self, task_id: str) -> list[SimpleNamespace]:
        return []

    def list_available_documents(self, *, active_only: bool = True) -> list[SimpleNamespace]:
        return []

    def list_task_presence(self, task_id: str) -> list[SimpleNamespace]:
        return []

    def touch_task_presence(self, task_id: str, *, activity: str = "reviewing") -> None:
        self.touched_presence.append((task_id, activity))

    def clear_task_presence(self, task_id: str) -> None:
        self.cleared_presence.append(task_id)

    def get_task_comment_action_context(self, task_id: str) -> SimpleNamespace:
        return SimpleNamespace(
            principal_user_id="user-alex",
            can_read=bool(task_id),
            can_manage=bool(task_id),
        )

    def post_comment(self, *, task_id, body, attachments=(), linked_document_ids=(), parent_comment_id=None) -> SimpleNamespace:
        comment = SimpleNamespace(id="comment-1", task_id=task_id, author_username="alex", body=body, mentions=[], attachments=list(attachments), created_at=datetime(2026, 5, 1, 10, 15))
        self._comments.append(comment)
        return comment


class _FakeTaskService:
    def __init__(self, tasks: list[SimpleNamespace] | None = None) -> None:
        self._tasks = {task.id: task for task in (tasks or [])}
        self._assignments: dict[str, SimpleNamespace] = {}
        self._dependencies: dict[str, SimpleNamespace] = {}
        self._project_resource_lookup: dict[str, str] = {}

    def list_tasks_for_project(self, project_id: str) -> list[SimpleNamespace]:
        return [t for t in self._tasks.values() if t.project_id == project_id]

    def get_task(self, task_id: str) -> SimpleNamespace | None:
        return self._tasks.get(task_id)

    def set_status(self, task_id: str, status: TaskStatus) -> None:
        task = self._tasks[task_id]
        task.status = status
        task.version += 1

    def set_tasks_status(
        self,
        task_ids: tuple[str, ...],
        status: TaskStatus,
        *,
        reopen_percent_complete: float | None = None,
    ) -> list[SimpleNamespace]:
        changed: list[SimpleNamespace] = []
        for task_id in task_ids:
            task = self._tasks.get(task_id)
            if task is None or task.status == status:
                continue
            if reopen_percent_complete is not None and status == TaskStatus.IN_PROGRESS:
                task.percent_complete = reopen_percent_complete
            self.set_status(task_id, status)
            changed.append(task)
        return changed

    def update_progress(self, task_id, *, percent_complete=None, actual_start=None, actual_end=None, status=None, expected_version=None) -> SimpleNamespace:
        task = self._tasks[task_id]
        if percent_complete is not None:
            task.percent_complete = float(percent_complete)
        if actual_start is not None:
            task.actual_start = actual_start
        if actual_end is not None:
            task.actual_end = actual_end
        if status is not None:
            task.status = status
        task.version += 1
        return task

    def delete_task(self, task_id: str) -> None:
        del self._tasks[task_id]

    def delete_tasks(self, task_ids: tuple[str, ...]) -> tuple[str, ...]:
        deleted: list[str] = []
        for task_id in task_ids:
            if task_id in self._tasks:
                self.delete_task(task_id)
                deleted.append(task_id)
        return tuple(deleted)

    def register_project_resource(self, project_resource_id: str, resource_id: str) -> None:
        self._project_resource_lookup[project_resource_id] = resource_id

    def list_assignments_for_task(self, task_id: str) -> list[SimpleNamespace]:
        return [a for a in self._assignments.values() if a.task_id == task_id]

    def assign_project_resource(self, *, task_id, project_resource_id, allocation_percent) -> SimpleNamespace:
        assignment = SimpleNamespace(
            id=f"assign-{len(self._assignments) + 1}",
            task_id=task_id,
            resource_id=self._project_resource_lookup.get(project_resource_id, project_resource_id),
            allocation_percent=allocation_percent,
            hours_logged=0.0,
            project_resource_id=project_resource_id,
        )
        self._assignments[assignment.id] = assignment
        return assignment

    def add_dependency(self, *, predecessor_id, successor_id, dependency_type, lag_days=0) -> SimpleNamespace:
        dependency = SimpleNamespace(
            id=f"dep-{len(self._dependencies) + 1}",
            predecessor_task_id=predecessor_id,
            successor_task_id=successor_id,
            dependency_type=DependencyType(str(dependency_type)),
            lag_days=lag_days,
        )
        self._dependencies[dependency.id] = dependency
        return dependency

    def list_dependencies_for_task(self, task_id: str) -> list[SimpleNamespace]:
        return [d for d in self._dependencies.values() if d.predecessor_task_id == task_id or d.successor_task_id == task_id]


class _FakeTaskTimesheetsDesktopApi:
    def build_assignment_snapshot(self, assignment_id, *, period_start=None):
        return SimpleNamespace(
            assignment=SimpleNamespace(value=assignment_id, label="", project_id="proj-1"),
            period_options=(),
            selected_period_start="",
            period_summary=SimpleNamespace(period_id="", period_start_label="", period_end_label="", status="OPEN", status_label="Open", resource_id="", resource_name="", total_hours_label="0.00h", entry_count=0, submitted_by_username="-", submitted_at_label="-", decided_by_username="-", decided_at_label="-", decision_note=""),
            entries=(),
            resource_period_total_hours_label="0.00h",
            scope_summary="",
        )


def _build_task_record(*, task_id, project_id, name, description, status, start_date, end_date, duration_days, priority, percent_complete, deadline) -> SimpleNamespace:
    return SimpleNamespace(
        id=task_id, project_id=project_id, name=name, description=description, status=status,
        start_date=start_date, end_date=end_date, duration_days=duration_days, priority=priority,
        percent_complete=percent_complete, actual_start=None, actual_end=None, deadline=deadline, version=1,
    )


def _build_catalog(tmp_path: Path, task_service):
    tasks_api = build_project_management_tasks_desktop_api(
        project_service=SimpleNamespace(
            list_for_task_workspace=lambda: [
                SimpleNamespace(id="proj-1", name="Plant Upgrade"),
                SimpleNamespace(id="proj-2", name="Warehouse Retrofit"),
            ]
        ),
        task_service=task_service,
        project_resource_service=SimpleNamespace(
            list_for_task_workspace=lambda project_id: []
        ),
        resource_service=SimpleNamespace(list_for_task_workspace=lambda **_kwargs: []),
    )
    collaboration_service = _FakeCollaborationService()
    collaboration_api = build_project_management_collaboration_desktop_api(collaboration_service=collaboration_service)
    settings = QSettings(str(tmp_path / "pm-task-views.ini"), QSettings.IniFormat)
    settings.clear()
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(
            platform_runtime=_FakePmRuntimeApi("org-1"),
            project_management_tasks=tasks_api,
            project_management_collaboration=collaboration_api,
            project_management_timesheets=_FakeTaskTimesheetsDesktopApi(),
        ),
        task_view_store=ProjectManagementTaskViewStore(settings),
    )
    return catalog


def test_tasks_controller_bulk_selection_and_undo_redo(tmp_path: Path, qapp) -> None:
    task_service = _FakeTaskService(
        [
            _build_task_record(task_id="task-1", project_id="proj-1", name="Cable Pull", description="", status=TaskStatus.IN_PROGRESS, start_date=date(2026, 5, 3), end_date=date(2026, 5, 6), duration_days=4, priority=70, percent_complete=45.0, deadline=date(2026, 5, 7)),
            _build_task_record(task_id="task-2", project_id="proj-1", name="Punchlist Closeout", description="", status=TaskStatus.BLOCKED, start_date=date(2026, 5, 8), end_date=date(2026, 5, 9), duration_days=2, priority=95, percent_complete=0.0, deadline=date(2026, 5, 9)),
            _build_task_record(task_id="task-3", project_id="proj-2", name="Lighting Retrofit", description="", status=TaskStatus.TODO, start_date=date(2026, 5, 10), end_date=date(2026, 5, 12), duration_days=3, priority=40, percent_complete=0.0, deadline=date(2026, 5, 13)),
            _build_task_record(task_id="task-4", project_id="proj-1", name="As-Built Handover", description="", status=TaskStatus.DONE, start_date=date(2026, 5, 10), end_date=date(2026, 5, 10), duration_days=1, priority=50, percent_complete=100.0, deadline=date(2026, 5, 10)),
        ]
    )
    catalog = _build_catalog(tmp_path, task_service)
    controller = catalog.tasksWorkspace

    controller.setTaskBulkSelection("task-1", True)
    controller.setTaskBulkSelection("task-4", True)

    assert controller.selectedTaskIds == ["task-1", "task-4"]
    assert controller.selectedTaskCount == 2
    assert controller.selectedTaskDoneCount == 1

    bulk_status_result = controller.applyBulkStatus({"status": "IN_PROGRESS", "reopenPercentComplete": "50"})
    qapp.processEvents()

    assert bulk_status_result == {"ok": True, "message": "Bulk task status applied."}
    assert controller.canUndoTaskAction is True
    assert controller.nextUndoLabel.startswith("Bulk status -> In Progress")
    reopened_task = next(item for item in controller.tasks["items"] if item["id"] == "task-4")
    assert reopened_task["statusLabel"] == "In Progress"
    assert reopened_task["state"]["status"] == "IN_PROGRESS"
    assert controller.selectedTaskDoneCount == 0

    undo_result = controller.undoLastTaskAction()
    qapp.processEvents()

    assert undo_result["ok"] is True
    assert controller.canRedoTaskAction is True
    assert controller.nextRedoLabel.startswith("Bulk status -> In Progress")
    restored_task = next(item for item in controller.tasks["items"] if item["id"] == "task-4")
    assert restored_task["statusLabel"] == "Done"
    assert restored_task["state"]["status"] == "DONE"

    redo_result = controller.redoLastTaskAction()
    qapp.processEvents()

    assert redo_result["ok"] is True
    assert controller.canUndoTaskAction is True
    redone_task = next(item for item in controller.tasks["items"] if item["id"] == "task-4")
    assert redone_task["statusLabel"] == "In Progress"
    assert redone_task["state"]["status"] == "IN_PROGRESS"

    controller.clearTaskBulkSelection()

    assert controller.selectedTaskIds == []
    assert controller.selectedTaskCount == 0

    controller.selectVisibleTasks()

    assert set(controller.selectedTaskIds) == {"task-1", "task-2", "task-3", "task-4"}
    assert controller.selectedTaskCount == 4

    controller.clearTaskBulkSelection()

    bulk_delete_result = controller.bulkDeleteTasks(["task-1", "task-4"])
    qapp.processEvents()

    assert bulk_delete_result == {"ok": True, "message": "Selected tasks deleted."}
    assert [item["id"] for item in controller.tasks["items"]] == ["task-2", "task-3"]
    assert controller.selectedTaskIds == []
    assert controller.selectedTaskCount == 0
