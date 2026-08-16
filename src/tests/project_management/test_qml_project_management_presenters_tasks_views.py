from pathlib import Path

from src.tests.project_management._task_presenters_test_helpers import (
    _FakeCollaborationService,
    _FakeTaskTimesheetsDesktopApi,
    _build_tasks_catalog,
    _make_task_service,
)


def test_tasks_controller_search_time_presence_filters(tmp_path: Path, qapp) -> None:
    task_service = _make_task_service()
    collaboration_service = _FakeCollaborationService()
    timesheets_api = _FakeTaskTimesheetsDesktopApi()
    catalog, _ = _build_tasks_catalog(tmp_path, task_service, collaboration_service, timesheets_api)

    controller = catalog.tasksWorkspace
    controller.loadSelectedTaskAssignments()
    controller.loadSelectedTaskCollaboration()

    controller.setSearchText("priority>=90")

    assert [item["title"] for item in controller.tasks["items"]] == ["Punchlist Closeout"]

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
