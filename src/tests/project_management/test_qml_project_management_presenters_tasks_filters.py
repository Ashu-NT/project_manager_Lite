import json
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
from src.api.desktop.platform import DesktopApiResult
from src.core.modules.project_management.domain.enums import (
    DependencyType,
    TaskStatus,
)
from src.core.platform.documents import DocumentStorageKind
from src.tests.ui_runtime_helpers import wait_until

from src.tests.project_management._task_presenter_test_helpers import (
    _FakeCollaborationService,
    _FakeTaskService,
    _FakeTaskTimesheetsDesktopApi,
    _build_tasks_catalog,
    _make_task_service,
)


def test_tasks_controller_views_time_presence_filters(tmp_path: Path, qapp) -> None:
    task_service = _make_task_service()
    collaboration_service = _FakeCollaborationService()
    timesheets_api = _FakeTaskTimesheetsDesktopApi()
    catalog, settings = _build_tasks_catalog(tmp_path, task_service, collaboration_service, timesheets_api)

    controller = catalog.tasksWorkspace
    controller.loadSelectedTaskAssignments()
    controller.loadSelectedTaskCollaboration()

    controller.setSearchText("priority>=90")

    assert [item["title"] for item in controller.tasks["items"]] == ["Punchlist Closeout"]

    save_view_result = controller.saveCurrentTaskView("High Focus")

    assert save_view_result == {"ok": True, "message": 'Saved task view "High Focus".'}
    assert controller.selectedTaskViewName == "High Focus"
    assert controller.taskViewOptions[-1]["value"] == "High Focus"
    assert json.loads(str(settings.value("tenant/org-1/task/saved_views", "{}"))) == {
        "High Focus": {"priority": 0, "query": "priority>=90", "schedule": 0, "status": 0}
    }
    assert "task/saved_views" not in set(settings.allKeys())

    controller.clearFilters()

    assert controller.searchText == ""
    assert controller.selectedTaskViewName == ""

    controller.selectTaskView("High Focus")
    apply_view_result = controller.applySelectedTaskView()

    assert apply_view_result == {"ok": True, "message": 'Applied task view "High Focus".'}
    assert controller.searchText == "priority>=90"
    assert [item["title"] for item in controller.tasks["items"]] == ["Punchlist Closeout"]

    delete_view_result = controller.deleteSelectedTaskView()

    assert delete_view_result == {"ok": True, "message": 'Deleted task view "High Focus".'}
    assert controller.taskViewOptions == [{"value": "", "label": "Current Filters"}]

    controller.clearFilters()
    controller.selectTask("task-1")

    time_entry_result = controller.addTaskTimeEntry(
        {"assignmentId": "assign-1", "entryDate": "2026-05-06", "hours": "2.5", "note": "Punchlist support"}
    )

    assert time_entry_result == {"ok": True, "message": "Task time entry added."}
    assert timesheets_api.added_entries[-1]["hours"] == 2.5
    controller.loadSelectedTaskTime()
    assert any(item["title"] == "2026-05-06" for item in controller.timeEntries["items"])

    post_result = controller.postTaskComment(
        {"taskId": "task-1", "body": "Please review the linked checklist with @planner.", "attachments": ["handover.txt"], "linkedDocumentIds": ["doc-2"]}
    )

    assert post_result == {"ok": True, "message": "Task collaboration update posted."}
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
