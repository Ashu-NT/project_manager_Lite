from __future__ import annotations

import json
from pathlib import Path

from src.tests.ui_runtime_helpers import wait_until
from src.tests.project_management._pm_task_service_helpers import build_task_controller_bundle


def test_pm_tasks_search_and_view_management(tmp_path: Path, qapp) -> None:
    bundle = build_task_controller_bundle(tmp_path)
    controller = bundle["controller"]
    settings = bundle["settings"]

    controller.setSearchText("priority>=90")

    assert [item["title"] for item in controller.tasks["items"]] == ["Punchlist Closeout"]

    save_view_result = controller.saveCurrentTaskView("High Focus")

    assert save_view_result == {"ok": True, "message": 'Saved task view "High Focus".'}
    assert controller.selectedTaskViewName == "High Focus"
    assert controller.taskViewOptions[-1]["value"] == "High Focus"
    assert json.loads(
        str(settings.value("tenant/org-1/task/saved_views", "{}"))
    ) == {"High Focus": {"priority": 0, "query": "priority>=90", "schedule": 0, "status": 0}}
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


def test_pm_tasks_bulk_status_undo_redo_and_select(tmp_path: Path, qapp) -> None:
    bundle = build_task_controller_bundle(tmp_path)
    controller = bundle["controller"]

    controller.clearFilters()
    controller.selectTask("task-1")
    controller.setTaskBulkSelection("task-1", True)
    controller.setTaskBulkSelection("task-4", True)

    assert controller.selectedTaskIds == ["task-1", "task-4"]
    assert controller.selectedTaskCount == 2
    assert controller.selectedTaskDoneCount == 1

    bulk_status_result = controller.applyBulkStatus(
        {"status": "IN_PROGRESS", "reopenPercentComplete": "50"}
    )
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


def test_pm_tasks_time_entries_collaboration_and_bulk_delete(tmp_path: Path, qapp) -> None:
    bundle = build_task_controller_bundle(tmp_path)
    controller = bundle["controller"]
    collaboration_service = bundle["collaboration_service"]
    timesheets_api = bundle["timesheets_api"]

    controller.activateTask("task-1")
    wait_until(
        qapp,
        lambda: controller.selectedTask["description"] == "Primary feeder cable installation.",
    )
    controller.loadSelectedTaskTime()

    time_entry_result = controller.addTaskTimeEntry(
        {"assignmentId": "assign-1", "entryDate": "2026-05-06", "hours": "2.5", "note": "Punchlist support"}
    )

    assert time_entry_result == {"ok": True, "message": "Task time entry added."}
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

    controller.setStatusFilter("all")
    controller.setSearchText("")
    controller.setTaskBulkSelection("task-1", True)
    controller.setTaskBulkSelection("task-4", True)

    bulk_delete_result = controller.bulkDeleteTasks(["task-1", "task-4"])
    qapp.processEvents()

    assert bulk_delete_result == {"ok": True, "message": "Selected tasks deleted."}
    assert [item["id"] for item in controller.tasks["items"]] == ["task-2", "task-3"]
    assert controller.selectedTaskIds == []
    assert controller.selectedTaskCount == 0
