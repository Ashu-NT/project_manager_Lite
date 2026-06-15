import json
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QSettings

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementTaskViewStore,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectDashboardPresenter,
    ProjectFinancialsWorkspacePresenter,
    build_project_management_workspace_presenters,
)
from src.ui_qml.modules.project_management.routes import build_project_management_routes
from src.core.modules.project_management.api.desktop import (
    build_project_management_collaboration_desktop_api,
    build_project_management_dashboard_desktop_api,
    build_project_management_financials_desktop_api,
    build_project_management_projects_desktop_api,
    build_project_management_register_desktop_api,
    build_project_management_resources_desktop_api,
    build_project_management_scheduling_desktop_api,
    build_project_management_tasks_desktop_api,
)
from src.api.desktop.runtime import build_desktop_api_registry
from src.api.desktop.platform import ApprovalRequestDto, ApprovalStatus, DesktopApiResult
from src.core.modules.project_management.domain.enums import (
    CostType,
    DependencyType,
    ProjectStatus,
    TaskStatus,
    WorkerType,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.core.platform.documents import DocumentStorageKind
from src.tests.ui_runtime_helpers import wait_until
from src.ui_qml.modules.project_management.presenters.collaboration import (
    ProjectCollaborationWorkspacePresenter,
)


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
        self._comments: list[SimpleNamespace] = [
            SimpleNamespace(
                id="comment-1",
                task_id="task-1",
                author_username="jamie",
                body="Please review the updated execution window.",
                mentions=["planner"],
                attachments=["handover.txt"],
                created_at=datetime(2026, 5, 1, 8, 45),
            )
        ]
        self._comment_documents: dict[str, list[SimpleNamespace]] = {
            "comment-1": [
                SimpleNamespace(
                    id="doc-1",
                    document_code="PM-ATT-001",
                    title="handover.txt",
                    document_type=SimpleNamespace(value="GENERAL"),
                    storage_kind=DocumentStorageKind.FILE_PATH,
                    storage_uri="handover.txt",
                    file_name="procedure.pdf",
                ),
                SimpleNamespace(
                    id="doc-ref-1",
                    document_code="PM-REF-001",
                    title="ticket-123",
                    document_type=SimpleNamespace(value="GENERAL"),
                    storage_kind=DocumentStorageKind.REFERENCE,
                    storage_uri="ticket-123",
                    file_name="",
                ),
            ]
        }

    def list_workspace_snapshot(self, *, limit: int = 200) -> SimpleNamespace:
        assert limit == 200
        return SimpleNamespace(
            notifications=[],
            inbox=[],
            recent_activity=[],
            active_presence=[],
        )

    def mark_task_mentions_read(self, task_id: str) -> None:
        self.marked_task_ids.append(task_id)

    def list_comments(self, task_id: str) -> list[SimpleNamespace]:
        return [comment for comment in self._comments if comment.task_id == task_id]

    def list_comment_documents(self, task_id: str) -> dict[str, list[SimpleNamespace]]:
        comment_ids = {comment.id for comment in self.list_comments(task_id)}
        return {
            comment_id: list(documents)
            for comment_id, documents in self._comment_documents.items()
            if comment_id in comment_ids
        }

    def list_mention_candidates(self, task_id: str) -> list[SimpleNamespace]:
        if task_id != "task-1":
            return []
        return [
            SimpleNamespace(handle="planner", label="@planner  Alex Taylor  Planner"),
            SimpleNamespace(handle="supervisor", label="@supervisor  Jordan Blake  Supervisor"),
        ]

    def list_available_documents(self, *, active_only: bool = True) -> list[SimpleNamespace]:
        assert active_only is True
        return [
            SimpleNamespace(
                id="doc-1",
                document_code="PM-LINK-001",
                title="Shared Method Statement",
            ),
            SimpleNamespace(
                id="doc-2",
                document_code="PM-LINK-002",
                title="Commissioning Checklist",
            ),
        ]

    def list_task_presence(self, task_id: str) -> list[SimpleNamespace]:
        if task_id != "task-1":
            return []
        return [
            SimpleNamespace(
                task_id="task-1",
                task_name="Cable Pull",
                project_id="proj-1",
                project_name="Plant Upgrade",
                username="planner",
                display_name="Alex Taylor",
                activity="reviewing",
                last_seen_at=datetime(2026, 5, 1, 9, 35),
                is_self=True,
            )
        ]

    def touch_task_presence(self, task_id: str, *, activity: str = "reviewing") -> None:
        self.touched_presence.append((task_id, activity))

    def clear_task_presence(self, task_id: str) -> None:
        self.cleared_presence.append(task_id)

    def post_comment(
        self,
        *,
        task_id: str,
        body: str,
        attachments=(),
        linked_document_ids=(),
    ) -> SimpleNamespace:
        self.posted_comments.append(
            {
                "task_id": task_id,
                "body": body,
                "attachments": tuple(attachments),
                "linked_document_ids": tuple(linked_document_ids),
            }
        )
        comment = SimpleNamespace(
            id="comment-posted-1",
            task_id=task_id,
            author_username="alex",
            body=body,
            mentions=["planner"],
            attachments=list(attachments),
            created_at=datetime(2026, 5, 1, 10, 15),
        )
        self._comments.append(comment)
        self._comment_documents[comment.id] = [
            SimpleNamespace(
                id="doc-2",
                document_code="PM-LINK-002",
                title="Commissioning Checklist",
                document_type=SimpleNamespace(value="GENERAL"),
                storage_kind=DocumentStorageKind.REFERENCE,
                storage_uri="ticket-456",
                file_name="",
            )
        ]
        return comment


class _FakeTaskService:
    def __init__(self, tasks: list[SimpleNamespace] | None = None) -> None:
        self._tasks = {
            task.id: task
            for task in (tasks or [])
        }
        self._assignments: dict[str, SimpleNamespace] = {}
        self._dependencies: dict[str, SimpleNamespace] = {}
        self._project_resource_lookup: dict[str, str] = {}

    def list_tasks_for_project(self, project_id: str) -> list[SimpleNamespace]:
        return [
            task
            for task in self._tasks.values()
            if task.project_id == project_id
        ]

    def get_task(self, task_id: str) -> SimpleNamespace | None:
        return self._tasks.get(task_id)

    def set_status(self, task_id: str, status: TaskStatus) -> None:
        task = self._tasks[task_id]
        task.status = status
        task.version += 1

    def update_progress(
        self,
        task_id: str,
        *,
        percent_complete: float | None = None,
        actual_start: date | None = None,
        actual_end: date | None = None,
        status: TaskStatus | None = None,
        expected_version: int | None = None,
    ) -> SimpleNamespace:
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

    def register_project_resource(self, project_resource_id: str, resource_id: str) -> None:
        self._project_resource_lookup[project_resource_id] = resource_id

    def list_assignments_for_task(self, task_id: str) -> list[SimpleNamespace]:
        return [
            assignment
            for assignment in self._assignments.values()
            if assignment.task_id == task_id
        ]

    def assign_project_resource(
        self,
        *,
        task_id: str,
        project_resource_id: str,
        allocation_percent: float,
    ) -> SimpleNamespace:
        assignment = SimpleNamespace(
            id=f"assign-{len(self._assignments) + 1}",
            task_id=task_id,
            resource_id=self._project_resource_lookup.get(
                project_resource_id,
                project_resource_id,
            ),
            allocation_percent=allocation_percent,
            hours_logged=0.0,
            project_resource_id=project_resource_id,
        )
        self._assignments[assignment.id] = assignment
        return assignment

    def add_dependency(
        self,
        *,
        predecessor_id: str,
        successor_id: str,
        dependency_type: str,
        lag_days: int = 0,
    ) -> SimpleNamespace:
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
        return [
            dependency
            for dependency in self._dependencies.values()
            if dependency.predecessor_task_id == task_id
            or dependency.successor_task_id == task_id
        ]


def _build_task_record(
    *,
    task_id: str,
    project_id: str,
    name: str,
    description: str,
    status: TaskStatus,
    start_date: date | None,
    end_date: date | None,
    duration_days: int | None,
    priority: int,
    percent_complete: float,
    deadline: date | None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=task_id,
        project_id=project_id,
        name=name,
        description=description,
        status=status,
        start_date=start_date,
        end_date=end_date,
        duration_days=duration_days,
        priority=priority,
        percent_complete=percent_complete,
        actual_start=None,
        actual_end=None,
        deadline=deadline,
        version=1,
    )


def test_project_management_workspace_catalog_exposes_typed_tasks_controller(
    tmp_path: Path,
    qapp,
) -> None:
    class _FakeTaskTimesheetsDesktopApi:
        def __init__(self) -> None:
            self.added_entries: list[dict[str, object]] = []

        def build_assignment_snapshot(self, assignment_id, *, period_start=None):
            assert assignment_id == "assign-1"
            selected_period_start = (
                period_start.isoformat() if period_start is not None else "2026-05-01"
            )
            entry_rows = [
                SimpleNamespace(
                    entry_id="entry-1",
                    entry_date_label="2026-05-03",
                    hours=6.0,
                    hours_label="6.00h",
                    note="Cable tray installation",
                    author_username="alex",
                ),
                *[
                    SimpleNamespace(
                        entry_id=row["entry_id"],
                        entry_date_label=row["entry_date"],
                        hours=row["hours"],
                        hours_label=f"{float(row['hours']):.2f}h",
                        note=row["note"],
                        author_username="alex",
                    )
                    for row in self.added_entries
                ],
            ]
            total_hours = sum(float(entry.hours or 0.0) for entry in entry_rows)
            return SimpleNamespace(
                assignment=SimpleNamespace(
                    value="assign-1",
                    label="Plant Upgrade | Cable Pull | Alex Taylor",
                    project_id="proj-1",
                ),
                period_options=(
                    SimpleNamespace(value="2026-05-01", label="May 2026"),
                    SimpleNamespace(value="2026-04-01", label="Apr 2026"),
                ),
                selected_period_start=selected_period_start,
                period_summary=SimpleNamespace(
                    period_id="period-1",
                    period_start_label="May 2026",
                    period_end_label="2026-05-31",
                    status="OPEN",
                    status_label="Open",
                    resource_id="res-1",
                    resource_name="Alex Taylor",
                    total_hours_label=f"{total_hours:.2f}h",
                    entry_count=len(entry_rows),
                    submitted_by_username="-",
                    submitted_at_label="-",
                    decided_by_username="-",
                    decided_at_label="-",
                    decision_note="",
                ),
                entries=tuple(entry_rows),
                resource_period_total_hours_label=f"{total_hours:.2f}h",
                scope_summary=(
                    f"Task period entries: {len(entry_rows)} | "
                    f"Resource month total: {total_hours:.2f}h"
                ),
            )

        def add_time_entry(self, command):
            entry_id = f"entry-{len(self.added_entries) + 2}"
            self.added_entries.append(
                {
                    "entry_id": entry_id,
                    "entry_date": command.entry_date.isoformat(),
                    "hours": float(command.hours),
                    "note": command.note or "",
                }
            )
            return SimpleNamespace(id=entry_id)

        def update_time_entry(self, command):
            for row in self.added_entries:
                if row["entry_id"] == command.entry_id:
                    row["entry_date"] = command.entry_date.isoformat()
                    row["hours"] = float(command.hours)
                    row["note"] = command.note or ""
                    return SimpleNamespace(id=command.entry_id)
            return SimpleNamespace(id=command.entry_id)

        def delete_time_entry(self, entry_id):
            self.added_entries = [
                row for row in self.added_entries if row["entry_id"] != entry_id
            ]

        def submit_period(self, *, resource_id, period_start, note=""):
            return SimpleNamespace(resource_id=resource_id, period_start=period_start, note=note)

        def lock_period(self, *, resource_id, period_start, note=""):
            return SimpleNamespace(resource_id=resource_id, period_start=period_start, note=note)

        def unlock_period(self, period_id, *, note=""):
            return SimpleNamespace(period_id=period_id, note=note)

    task_service = _FakeTaskService(
        [
            _build_task_record(
                task_id="task-1",
                project_id="proj-1",
                name="Cable Pull",
                description="Primary feeder cable installation.",
                status=TaskStatus.IN_PROGRESS,
                start_date=date(2026, 5, 3),
                end_date=date(2026, 5, 6),
                duration_days=4,
                priority=70,
                percent_complete=45.0,
                deadline=date(2026, 5, 7),
            ),
            _build_task_record(
                task_id="task-2",
                project_id="proj-1",
                name="Punchlist Closeout",
                description="Commissioning closeout walkdown.",
                status=TaskStatus.BLOCKED,
                start_date=date(2026, 5, 8),
                end_date=date(2026, 5, 9),
                duration_days=2,
                priority=95,
                percent_complete=0.0,
                deadline=date(2026, 5, 9),
            ),
            _build_task_record(
                task_id="task-3",
                project_id="proj-2",
                name="Lighting Retrofit",
                description="Warehouse fixture replacement.",
                status=TaskStatus.TODO,
                start_date=date(2026, 5, 10),
                end_date=date(2026, 5, 12),
                duration_days=3,
                priority=40,
                percent_complete=0.0,
                deadline=date(2026, 5, 13),
            ),
            _build_task_record(
                task_id="task-4",
                project_id="proj-1",
                name="As-Built Handover",
                description="Finalize turnover package and as-built dossier.",
                status=TaskStatus.DONE,
                start_date=date(2026, 5, 10),
                end_date=date(2026, 5, 10),
                duration_days=1,
                priority=50,
                percent_complete=100.0,
                deadline=date(2026, 5, 10),
            ),
        ]
    )
    task_service.register_project_resource("pr-1", "res-1")
    task_service.assign_project_resource(
        task_id="task-1",
        project_resource_id="pr-1",
        allocation_percent=55.0,
    )
    task_service.add_dependency(
        predecessor_id="task-1",
        successor_id="task-2",
        dependency_type="FS",
        lag_days=2,
    )
    tasks_api = build_project_management_tasks_desktop_api(
        project_service=SimpleNamespace(
            list_projects=lambda: [
                SimpleNamespace(id="proj-1", name="Plant Upgrade"),
                SimpleNamespace(id="proj-2", name="Warehouse Retrofit"),
            ]
        ),
        task_service=task_service,
        project_resource_service=SimpleNamespace(
            list_by_project=lambda project_id: [
                SimpleNamespace(
                    id="pr-1",
                    project_id="proj-1",
                    resource_id="res-1",
                    hourly_rate=90.0,
                    currency_code="EUR",
                    is_active=True,
                )
            ]
            if project_id == "proj-1"
            else []
        ),
        resource_service=SimpleNamespace(
            list_resources=lambda: [
                SimpleNamespace(
                    id="res-1",
                    name="Alex Taylor",
                    is_active=True,
                    hourly_rate=85.0,
                    currency_code="EUR",
                )
            ]
        ),
    )
    collaboration_service = _FakeCollaborationService()
    collaboration_api = build_project_management_collaboration_desktop_api(
        collaboration_service=collaboration_service
    )
    timesheets_api = _FakeTaskTimesheetsDesktopApi()
    settings = QSettings(str(tmp_path / "pm-task-views.ini"), QSettings.IniFormat)
    settings.clear()
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(
            platform_runtime=_FakePmRuntimeApi("org-1"),
            project_management_tasks=tasks_api,
            project_management_collaboration=collaboration_api,
            project_management_timesheets=timesheets_api,
        ),
        task_view_store=ProjectManagementTaskViewStore(settings),
    )

    controller = catalog.tasksWorkspace

    assert controller.workspace["routeId"] == "project_management.tasks"
    assert controller.overview["title"] == "Tasks"
    metrics_by_label = {
        metric["label"]: metric for metric in controller.overview["metrics"]
    }
    assert metrics_by_label["Mentions"]["value"] == "0"
    assert metrics_by_label["Notifications"]["value"] == "0"
    assert metrics_by_label["Active now"]["value"] == "0"
    assert controller.canUndoTaskAction is False
    assert controller.canRedoTaskAction is False
    assert controller.projectOptions[0]["label"] == "All Projects"
    assert controller.projectOptions[1]["label"] == "Plant Upgrade"
    assert controller.selectedProjectId == ""
    assert controller.selectedTaskId == "task-1"
    assert controller.priorityOptions[0]["label"] == "All priorities"
    assert controller.scheduleOptions[0]["value"] == "all"
    assert controller.taskViewOptions == [{"value": "", "label": "Current Filters"}]
    assert controller.tasks["items"][0]["title"] == "Cable Pull"
    assert controller.selectedTask["title"] == "Cable Pull"
    assert controller.assignmentOptions == []
    assert controller.assignments["items"] == []
    assert controller.selectedAssignmentId == ""
    assert controller.dependencies["items"] == []
    assert controller.dependencyTypeOptions == []
    assert controller.dependencyTaskOptions == []
    assert controller.timePeriodOptions == []
    assert controller.timeEntries["items"] == []
    assert controller.collaborationMentionOptions == []
    assert controller.collaborationDocumentOptions == []
    assert controller.collaborationComments["items"] == []
    assert controller.collaborationPresence["items"] == []
    assert collaboration_service.touched_presence == []

    controller.activateTask("task-1")
    wait_until(
        qapp,
        lambda: controller.selectedTask["description"]
        == "Primary feeder cable installation.",
    )

    assert controller.assignmentOptions == []
    assert controller.assignments["items"] == []
    assert controller.selectedAssignmentId == ""
    assert controller.dependencies["items"] == []
    assert controller.dependencyTypeOptions == []
    assert controller.dependencyTaskOptions == []
    assert collaboration_service.touched_presence == []

    controller.setTaskReviewActive(True)
    wait_until(
        qapp,
        lambda: collaboration_service.touched_presence
        and collaboration_service.touched_presence[-1] == ("task-1", "reviewing"),
    )

    controller.loadSelectedTaskAssignments()

    assert controller.assignmentOptions[0]["label"] == "Alex Taylor (90.00 EUR/hr)"
    assert controller.assignments["items"][0]["title"] == "Alex Taylor"
    assert controller.selectedAssignmentId == "assign-1"

    controller.loadSelectedTaskDependencies()

    assert controller.dependencies["items"][0]["title"] == "Punchlist Closeout"
    assert controller.dependencyTypeOptions[0]["value"] == "FS"
    assert controller.dependencyTaskOptions[0]["value"] == "task-2"

    controller.loadSelectedTaskTime()

    assert controller.timePeriodOptions[0]["value"] == "2026-05-01"
    assert controller.timeEntries["items"][0]["title"] == "2026-05-03"
    assert controller.timeAssignmentSummary["state"]["assignmentId"] == "assign-1"
    assert controller.selectedTimeEntry["fields"][0]["value"] == "2026-05-03"

    controller.loadSelectedTaskCollaboration()

    assert controller.collaborationMentionOptions[0]["value"] == "planner"
    assert controller.collaborationDocumentOptions[0]["value"] == "doc-1"
    assert controller.collaborationComments["items"][0]["title"] == "@jamie"
    assert controller.collaborationPresence["items"][0]["title"] == "Alex Taylor (@planner)"
    assert controller.bulkStatusOptions[0]["value"] == "TODO"

    controller.setSearchText("priority>=90")

    assert [item["title"] for item in controller.tasks["items"]] == [
        "Punchlist Closeout"
    ]

    save_view_result = controller.saveCurrentTaskView("High Focus")

    assert save_view_result == {
        "ok": True,
        "message": 'Saved task view "High Focus".',
    }
    assert controller.selectedTaskViewName == "High Focus"
    assert controller.taskViewOptions[-1]["value"] == "High Focus"
    assert json.loads(
        str(settings.value("tenant/org-1/task/saved_views", "{}"))
    ) == {
        "High Focus": {
            "priority": 0,
            "query": "priority>=90",
            "schedule": 0,
            "status": 0,
        }
    }
    assert "task/saved_views" not in set(settings.allKeys())

    controller.clearFilters()

    assert controller.searchText == ""
    assert controller.selectedTaskViewName == ""

    controller.selectTaskView("High Focus")
    apply_view_result = controller.applySelectedTaskView()

    assert apply_view_result == {
        "ok": True,
        "message": 'Applied task view "High Focus".',
    }
    assert controller.searchText == "priority>=90"
    assert [item["title"] for item in controller.tasks["items"]] == [
        "Punchlist Closeout"
    ]

    delete_view_result = controller.deleteSelectedTaskView()

    assert delete_view_result == {
        "ok": True,
        "message": 'Deleted task view "High Focus".',
    }
    assert controller.taskViewOptions == [{"value": "", "label": "Current Filters"}]

    controller.clearFilters()
    controller.selectTask("task-1")

    controller.setTaskBulkSelection("task-1", True)
    controller.setTaskBulkSelection("task-4", True)

    assert controller.selectedTaskIds == ["task-1", "task-4"]
    assert controller.selectedTaskCount == 2
    assert controller.selectedTaskDoneCount == 1

    bulk_status_result = controller.applyBulkStatus(
        {
            "status": "IN_PROGRESS",
            "reopenPercentComplete": "50",
        }
    )
    qapp.processEvents()

    assert bulk_status_result == {
        "ok": True,
        "message": "Bulk task status applied.",
    }
    assert controller.canUndoTaskAction is True
    assert controller.nextUndoLabel.startswith("Bulk status -> In Progress")
    reopened_task = next(
        item for item in controller.tasks["items"] if item["id"] == "task-4"
    )
    assert reopened_task["statusLabel"] == "In Progress"
    assert reopened_task["state"]["status"] == "IN_PROGRESS"
    assert controller.selectedTaskDoneCount == 0

    undo_result = controller.undoLastTaskAction()
    qapp.processEvents()

    assert undo_result["ok"] is True
    assert controller.canRedoTaskAction is True
    assert controller.nextRedoLabel.startswith("Bulk status -> In Progress")
    restored_task = next(
        item for item in controller.tasks["items"] if item["id"] == "task-4"
    )
    assert restored_task["statusLabel"] == "Done"
    assert restored_task["state"]["status"] == "DONE"

    redo_result = controller.redoLastTaskAction()
    qapp.processEvents()

    assert redo_result["ok"] is True
    assert controller.canUndoTaskAction is True
    redone_task = next(
        item for item in controller.tasks["items"] if item["id"] == "task-4"
    )
    assert redone_task["statusLabel"] == "In Progress"
    assert redone_task["state"]["status"] == "IN_PROGRESS"

    controller.clearTaskBulkSelection()

    assert controller.selectedTaskIds == []
    assert controller.selectedTaskCount == 0

    controller.selectVisibleTasks()

    assert set(controller.selectedTaskIds) == {"task-1", "task-2", "task-3", "task-4"}
    assert controller.selectedTaskCount == 4

    controller.clearTaskBulkSelection()

    time_entry_result = controller.addTaskTimeEntry(
        {
            "assignmentId": "assign-1",
            "entryDate": "2026-05-06",
            "hours": "2.5",
            "note": "Punchlist support",
        }
    )

    assert time_entry_result == {
        "ok": True,
        "message": "Task time entry added.",
    }
    assert timesheets_api.added_entries[-1]["hours"] == 2.5
    controller.loadSelectedTaskTime()
    assert any(item["title"] == "2026-05-06" for item in controller.timeEntries["items"])

    post_result = controller.postTaskComment(
        {
            "taskId": "task-1",
            "body": "Please review the linked checklist with @planner.",
            "attachments": ["handover.txt"],
            "linkedDocumentIds": ["doc-2"],
        }
    )

    assert post_result == {
        "ok": True,
        "message": "Task collaboration update posted.",
    }
    assert collaboration_service.posted_comments[-1]["linked_document_ids"] == ("doc-2",)

    begin_presence_result = controller.beginTaskPresence("task-1", "editing")

    assert begin_presence_result["ok"] is True

    end_presence_result = controller.endTaskPresence("task-1")

    assert end_presence_result["ok"] is True
    assert collaboration_service.touched_presence[-1] == ("task-1", "reviewing")

    controller.setStatusFilter("BLOCKED")

    assert controller.selectedStatusFilter == "BLOCKED"
    assert [item["title"] for item in controller.tasks["items"]] == ["Punchlist Closeout"]

    controller.setSearchText("cable")

    assert controller.tasks["items"] == []
    assert controller.emptyState == "No tasks match the current filters."

    controller.setStatusFilter("all")
    controller.setSearchText("")
    controller.setTaskBulkSelection("task-1", True)
    controller.setTaskBulkSelection("task-4", True)

    bulk_delete_result = controller.bulkDeleteTasks(["task-1", "task-4"])
    qapp.processEvents()

    assert bulk_delete_result == {
        "ok": True,
        "message": "Selected tasks deleted.",
    }
    assert [item["id"] for item in controller.tasks["items"]] == ["task-2", "task-3"]
    assert controller.selectedTaskIds == []
    assert controller.selectedTaskCount == 0
