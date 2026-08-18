from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from src.tests.ui_runtime_helpers import wait_until
from src.tests.project_management._pm_task_service_helpers import build_task_controller_bundle
from src.ui_qml.modules.project_management.presenters.tasks.assignment_command_handler import (
    preview_assignment,
)
from src.ui_qml.modules.project_management.presenters.tasks.assignment_mapper import (
    to_assignment_record_view_model,
    to_assignment_table_row,
)


def _fake_assignment(**overrides):
    defaults = dict(
        id="assign-1",
        task_id="task-1",
        resource_id="resource-1",
        resource_name="Alice Brown",
        allocation_percent=50.0,
        hours_logged="18",
        project_resource_id="pr-1",
        response_status="accepted",
        response_status_label="Accepted",
        can_manage=True,
        can_accept=False,
        can_decline=False,
        allocated_planned_hours="32",
        version=2,
        project_resource_version=3,
        capacity_known=True,
        capacity_status="OVER_CAPACITY",
        capacity_status_label="Over capacity",
        available_capacity_hours_label="40.0 h",
        committed_capacity_hours_label="48.0 h",
        capacity_headroom_hours_label="-8.0 h",
        peak_utilization_percent=120.0,
        remaining_planned_hours_label="14.0 h",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_assignment_mapper_state_carries_capacity_facts_verbatim() -> None:
    view_model = to_assignment_record_view_model(_fake_assignment())

    assert view_model.state["capacityKnown"] is True
    assert view_model.state["capacityStatus"] == "OVER_CAPACITY"
    assert view_model.state["capacityStatusLabel"] == "Over capacity"
    assert view_model.state["availableCapacityLabel"] == "40.0 h"
    assert view_model.state["committedCapacityLabel"] == "48.0 h"
    assert view_model.state["capacityHeadroomLabel"] == "-8.0 h"
    assert view_model.state["peakUtilizationPercent"] == 120.0
    assert view_model.state["remainingPlannedLabel"] == "14.0 h"


def test_assignment_mapper_table_row_flattens_state_for_data_table() -> None:
    view_model = to_assignment_record_view_model(_fake_assignment())
    row = to_assignment_table_row(view_model)

    assert row["id"] == "assign-1"
    assert row["resourceName"] == "Alice Brown"
    assert row["allocationLabel"] == "50.0%"
    assert row["plannedLabel"] == "32.00 h"
    assert row["actualLabel"] == "18.00 h"
    assert row["remainingLabel"] == "14.0 h"
    assert row["capacityStatus"] == "OVER_CAPACITY"
    assert row["capacityStatusLabel"] == "Over capacity"
    # Full state remains available on the row for inspector/action lookups.
    assert row["state"]["projectResourceId"] == "pr-1"


def test_assignment_mapper_defaults_capacity_fields_when_absent() -> None:
    """An assignment DTO without the capacity fields (e.g. an older/fake
    desktop API in other tests) must not crash the mapper -- it degrades to
    the explicit UNKNOWN vocabulary, never a fabricated zero."""
    bare = SimpleNamespace(
        id="assign-2",
        task_id="task-1",
        resource_id="resource-2",
        resource_name="Bob",
        allocation_percent=20.0,
        hours_logged="2",
        project_resource_id="pr-2",
        response_status="pending",
        response_status_label="Pending",
        can_manage=True,
        can_accept=True,
        can_decline=True,
        allocated_planned_hours="8",
    )

    view_model = to_assignment_record_view_model(bare)
    row = to_assignment_table_row(view_model)

    assert view_model.state["capacityKnown"] is False
    assert view_model.state["capacityStatus"] == "UNKNOWN"
    assert view_model.state["capacityStatusLabel"] == "Capacity unknown"
    assert row["capacityStatusLabel"] == "Capacity unknown"


def test_pm_assignment_preview_maps_availability_and_policy_evidence() -> None:
    captured_calls = []

    def _fake_preview_assignment(
        task_id, project_resource_id, *, proposed_allocation_percent, exclude_assignment_id
    ):
        captured_calls.append((task_id, project_resource_id, proposed_allocation_percent, exclude_assignment_id))
        return SimpleNamespace(
            overallocation_pct=25.0,
            conflict_projects=("Project Alpha", "Project Beta"),
            skills_matched=False,
            certs_valid=True,
            has_warnings=True,
            warning_messages=("Missing commissioning skill",),
            is_blocked=True,
            block_messages=("Assignment policy blocked",),
            capacity_known=True,
            available_capacity_hours_label="40.0 h",
            existing_committed_hours_label="20.0 h",
            proposed_committed_hours_label="30.0 h",
            resulting_committed_hours_label="50.0 h",
            peak_utilization_percent=125.0,
            capacity_status="OVER_CAPACITY",
            capacity_status_label="Over capacity",
            conflict_date_labels=("2026-06-01",),
        )

    desktop_api = SimpleNamespace(preview_assignment=_fake_preview_assignment)

    result = preview_assignment(
        desktop_api,
        {
            "taskId": "task-1",
            "projectResourceId": "project-resource-1",
            "proposedAllocationPercent": "60.0",
            "excludeAssignmentId": "assign-9",
        },
    )

    assert captured_calls == [("task-1", "project-resource-1", 60.0, "assign-9")]
    assert result == {
        "ok": True,
        "overallocationPct": 25.0,
        "conflictProjects": ["Project Alpha", "Project Beta"],
        "skillsMatched": False,
        "certsValid": True,
        "hasWarnings": True,
        "warningMessages": ["Missing commissioning skill"],
        "isBlocked": True,
        "blockMessages": ["Assignment policy blocked"],
        "capacityKnown": True,
        "availableCapacityHoursLabel": "40.0 h",
        "existingCommittedHoursLabel": "20.0 h",
        "proposedCommittedHoursLabel": "30.0 h",
        "resultingCommittedHoursLabel": "50.0 h",
        "peakUtilizationPercent": 125.0,
        "capacityStatus": "OVER_CAPACITY",
        "capacityStatusLabel": "Over capacity",
        "conflictDateLabels": ["2026-06-01"],
    }


def test_pm_assignment_preview_defaults_proposed_allocation_to_100_and_no_exclusion() -> None:
    captured_calls = []

    def _fake_preview_assignment(
        task_id, project_resource_id, *, proposed_allocation_percent, exclude_assignment_id
    ):
        captured_calls.append((task_id, project_resource_id, proposed_allocation_percent, exclude_assignment_id))
        return SimpleNamespace(
            overallocation_pct=0.0,
            conflict_projects=(),
            skills_matched=True,
            certs_valid=True,
            has_warnings=False,
            warning_messages=(),
            is_blocked=False,
            block_messages=(),
            capacity_known=False,
            available_capacity_hours_label="",
            existing_committed_hours_label="",
            proposed_committed_hours_label="",
            resulting_committed_hours_label="",
            peak_utilization_percent=0.0,
            capacity_status="UNKNOWN",
            capacity_status_label="Capacity unknown",
            conflict_date_labels=(),
        )

    desktop_api = SimpleNamespace(preview_assignment=_fake_preview_assignment)

    preview_assignment(
        desktop_api,
        {"taskId": "task-1", "projectResourceId": "project-resource-1"},
    )

    assert captured_calls == [("task-1", "project-resource-1", 100.0, None)]


def test_pm_tasks_search_filters(tmp_path: Path, qapp) -> None:
    bundle = build_task_controller_bundle(tmp_path)
    controller = bundle["controller"]

    controller.setSearchText("priority>=90")

    assert [item["title"] for item in controller.tasks["items"]] == ["Punchlist Closeout"]

    controller.clearFilters()

    assert controller.searchText == ""


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


def test_pm_tasks_move_wbs_action_uses_the_desktop_contract(tmp_path: Path, qapp) -> None:
    bundle = build_task_controller_bundle(tmp_path)
    controller = bundle["controller"]
    task_service = bundle["task_service"]
    task = task_service.get_task("task-1")

    result = controller.moveTaskInWbs(
        {
            "taskId": task.id,
            "parentTaskId": "",
            "wbsCode": "9",
            "sortOrder": 0,
            "expectedVersion": task.version,
        }
    )
    qapp.processEvents()

    assert result == {"ok": True, "message": "Task WBS position updated."}
    assert task_service.get_task("task-1").wbs_code == "9"


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

    reply_result = controller.postTaskComment(
        {
            "taskId": "task-1",
            "body": "Replying to the update.",
            "parentCommentId": "comment-1",
        }
    )
    edit_result = controller.editTaskComment(
        {
            "commentId": "comment-1",
            "body": "Updated execution window.",
            "expectedRevision": 1,
        }
    )
    reaction_result = controller.reactToTaskComment(
        {"commentId": "comment-1", "emoji": "\N{THUMBS UP SIGN}"}
    )
    removal_result = controller.removeTaskCommentReaction(
        {"commentId": "comment-1", "emoji": "\N{THUMBS UP SIGN}"}
    )
    delete_result = controller.deleteTaskComment(
        {
            "commentId": "comment-1",
            "expectedRevision": 4,
            "reason": "Superseded guidance",
        }
    )

    assert reply_result["ok"] is True
    assert collaboration_service.posted_comments[-1]["parent_comment_id"] == "comment-1"
    assert edit_result == {"ok": True, "message": "Comment updated."}
    assert reaction_result == {"ok": True, "message": "Reaction added."}
    assert removal_result == {"ok": True, "message": "Reaction removed."}
    assert delete_result == {"ok": True, "message": "Comment deleted."}
    assert collaboration_service.edited_comment_ids == ["comment-1"]
    assert collaboration_service.deleted_comment_ids == ["comment-1"]
    assert collaboration_service._comments[0].deletion_reason == "Superseded guidance"

    begin_presence_result = controller.beginTaskPresence("task-1", "editing")
    assert begin_presence_result["ok"] is True

    heartbeat_count = len(collaboration_service.touched_presence)
    controller._collab_ctrl._on_runtime_heartbeat()
    assert len(collaboration_service.touched_presence) == heartbeat_count + 1
    assert collaboration_service.touched_presence[-1] == ("task-1", "editing")

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


def test_pm_assignment_response_actions_are_exposed_and_executed(tmp_path: Path, qapp) -> None:
    bundle = build_task_controller_bundle(tmp_path)
    controller = bundle["controller"]
    task_service = bundle["task_service"]

    controller.activateTask("task-1")
    controller.loadSelectedTaskAssignments()
    wait_until(qapp, lambda: len(controller.assignments["items"]) == 1)

    assignment_item = controller.assignments["items"][0]
    assert assignment_item["state"]["canAccept"] is True
    assert assignment_item["state"]["canDecline"] is True

    accepted = controller.acceptAssignment("assign-1")
    assert accepted == {"ok": True, "message": "Assignment accepted."}
    assert task_service._assignments["assign-1"].response_status == "accepted"

    task_service._assignments["assign-1"].response_status = "pending"
    controller.refresh()
    wait_until(
        qapp,
        lambda: controller.assignments["items"][0]["state"]["responseStatus"] == "pending",
    )
    declined = controller.declineAssignment(
        {
            "assignmentId": "assign-1",
            "reason": "Capacity committed to commissioning",
        }
    )
    assert declined == {"ok": True, "message": "Assignment declined."}
    assert task_service._assignments["assign-1"].response_status == "declined"
    assert task_service._assignments["assign-1"].decline_reason == "Capacity committed to commissioning"
    assert controller.selectedTaskCount == 0
