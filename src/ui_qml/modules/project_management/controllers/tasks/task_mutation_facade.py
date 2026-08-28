from __future__ import annotations


def generate_entity_code(controller, entity_type: str, payload: dict[str, object]) -> str:
    return controller._task_list.generateEntityCode(entity_type, payload)


def create_task(controller, payload: dict[str, object]) -> dict[str, object]:
    return controller._task_list.createTask(payload)


def update_task(controller, payload: dict[str, object]) -> dict[str, object]:
    return controller._task_list.updateTask(payload)


def update_task_scheduling_constraint(controller, payload: dict[str, object]) -> dict[str, object]:
    return controller._task_list.updateSchedulingConstraint(payload)


def move_task_in_wbs(controller, payload: dict[str, object]) -> dict[str, object]:
    return controller._task_list.moveTaskInWbs(payload)


def update_progress(controller, payload: dict[str, object]) -> dict[str, object]:
    return controller._task_list.updateProgress(payload)


def delete_task(controller, task_id: str) -> dict[str, object]:
    return controller._task_list.deleteTask(task_id)


def apply_bulk_status(controller, payload: dict[str, object]) -> dict[str, object]:
    return controller._task_list.applyBulkStatus(payload)


def bulk_delete_tasks(controller, task_ids: list[object]) -> dict[str, object]:
    return controller._task_list.bulkDeleteTasks(task_ids)


def undo_last_task_action(controller) -> dict[str, object]:
    return controller._task_list.undoLastTaskAction()


def redo_last_task_action(controller) -> dict[str, object]:
    return controller._task_list.redoLastTaskAction()


def create_assignment(controller, payload: dict[str, object]) -> dict[str, object]:
    return controller._assignments_ctrl.createAssignment(payload)


def update_assignment_allocation(controller, payload: dict[str, object]) -> dict[str, object]:
    return controller._assignments_ctrl.updateAssignmentAllocation(payload)


def update_assignment_planned_hours(controller, payload: dict[str, object]) -> dict[str, object]:
    return controller._assignments_ctrl.updateAssignmentPlannedHours(payload)


def delete_assignment(controller, assignment_id: str) -> dict[str, object]:
    return controller._assignments_ctrl.deleteAssignment(assignment_id)


def accept_assignment(controller, assignment_id: str) -> dict[str, object]:
    return controller._assignments_ctrl.acceptAssignment(assignment_id)


def decline_assignment(controller, payload: dict[str, object]) -> dict[str, object]:
    return controller._assignments_ctrl.declineAssignment(payload)


def validate_assignment(controller, payload: dict[str, object]) -> dict[str, object]:
    return controller._assignments_ctrl.validateAssignment(payload)


def create_dependency(controller, payload: dict[str, object]) -> dict[str, object]:
    return controller._dependencies_ctrl.createDependency(payload)


def update_dependency(controller, payload: dict[str, object]) -> dict[str, object]:
    return controller._dependencies_ctrl.updateDependency(payload)


def delete_dependency(controller, dependency_id: str) -> dict[str, object]:
    return controller._dependencies_ctrl.deleteDependency(dependency_id)


def add_task_time_entry(controller, payload: dict[str, object]) -> dict[str, object]:
    return controller._time_ctrl.addTaskTimeEntry(payload)


def update_task_time_entry(controller, payload: dict[str, object]) -> dict[str, object]:
    return controller._time_ctrl.updateTaskTimeEntry(payload)


def delete_task_time_entry(
    controller,
    entry_id: str,
    expected_version: int,
) -> dict[str, object]:
    return controller._time_ctrl.deleteTaskTimeEntry(entry_id, expected_version)


def post_task_comment(controller, payload: dict[str, object]) -> dict[str, object]:
    return controller._collab_ctrl.postTaskComment(payload)


def edit_task_comment(controller, payload: dict[str, object]) -> dict[str, object]:
    return controller._collab_ctrl.editTaskComment(payload)


def delete_task_comment(controller, payload: dict[str, object]) -> dict[str, object]:
    return controller._collab_ctrl.deleteTaskComment(payload)


def react_to_task_comment(controller, payload: dict[str, object]) -> dict[str, object]:
    return controller._collab_ctrl.reactToTaskComment(payload)


def remove_task_comment_reaction(
    controller,
    payload: dict[str, object],
) -> dict[str, object]:
    return controller._collab_ctrl.removeTaskCommentReaction(payload)


def mark_task_collaboration_read(controller, task_id: str) -> dict[str, object]:
    return controller._collab_ctrl.markTaskCollaborationRead(task_id)


def begin_task_presence(controller, task_id: str, activity: str) -> dict[str, object]:
    return controller._collab_ctrl.beginTaskPresence(task_id, activity)


def end_task_presence(controller, task_id: str) -> dict[str, object]:
    return controller._collab_ctrl.endTaskPresence(task_id)


__all__ = [
    "accept_assignment",
    "add_task_time_entry",
    "apply_bulk_status",
    "begin_task_presence",
    "bulk_delete_tasks",
    "create_assignment",
    "create_dependency",
    "create_task",
    "delete_task_comment",
    "delete_assignment",
    "decline_assignment",
    "delete_dependency",
    "delete_task",
    "delete_task_time_entry",
    "end_task_presence",
    "edit_task_comment",
    "generate_entity_code",
    "mark_task_collaboration_read",
    "move_task_in_wbs",
    "post_task_comment",
    "react_to_task_comment",
    "redo_last_task_action",
    "remove_task_comment_reaction",
    "undo_last_task_action",
    "update_assignment_allocation",
    "update_assignment_planned_hours",
    "update_dependency",
    "update_progress",
    "update_task",
    "validate_assignment",
]
