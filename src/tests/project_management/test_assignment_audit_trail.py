"""Dedicated assignment/status audit trail: parent_entity_id linkage + action_prefix filter."""

from __future__ import annotations

from types import SimpleNamespace

from src.core.modules.project_management.application.tasks.commands.assignment_activity import (
    record_assignment_action,
)
from src.core.platform.domain.history.activity.activity_entry import ActivityEntry


class _FakeActivityService:
    def __init__(self) -> None:
        self.recorded: list[dict] = []

    def record(self, **kwargs):
        self.recorded.append(kwargs)
        return SimpleNamespace(id=f"activity-{len(self.recorded)}")


def test_record_assignment_action_links_parent_entity_id_to_task():
    activity_service = _FakeActivityService()
    owner = SimpleNamespace(_activity_service=activity_service)

    record_assignment_action(
        owner,
        action="assignment.add",
        assignment_id="assign-1",
        project_id="proj-1",
        task_id="task-1",
        task_name="Cable Pull",
        resource_name="Alex Taylor",
    )

    assert len(activity_service.recorded) == 1
    call = activity_service.recorded[0]
    assert call["entity_type"] == "task_assignment"
    assert call["entity_id"] == "assign-1"
    assert call["parent_entity_id"] == "task-1"
    assert call["workspace_id"] == "proj-1"


def test_record_assignment_action_without_task_id_leaves_parent_entity_id_none():
    activity_service = _FakeActivityService()
    owner = SimpleNamespace(_activity_service=activity_service)

    record_assignment_action(
        owner,
        action="assignment.add",
        assignment_id="assign-1",
        project_id="proj-1",
        task_name="Cable Pull",
        resource_name="Alex Taylor",
    )

    assert activity_service.recorded[0]["parent_entity_id"] is None


def test_activity_repository_filters_by_parent_entity_id_and_action_prefix(services):
    session = services["session"]
    repo = services["activity_service"]._activity_repo

    repo.add(
        ActivityEntry.create(
            action="assignment.add",
            entity_type="task_assignment",
            entity_id="assign-1",
            module="project_management",
            actor_id="user-1",
            workspace_id="proj-1",
            parent_entity_id="task-1",
            human_message="assignment.add",
        )
    )
    repo.add(
        ActivityEntry.create(
            action="assignment.accept",
            entity_type="task_assignment",
            entity_id="assign-1",
            module="project_management",
            actor_id="user-1",
            workspace_id="proj-1",
            parent_entity_id="task-1",
            human_message="assignment.accept",
        )
    )
    repo.add(
        ActivityEntry.create(
            action="task.set_status",
            entity_type="task",
            entity_id="task-1",
            module="project_management",
            actor_id="user-1",
            workspace_id="proj-1",
            parent_entity_id=None,
            human_message="task.set_status",
        )
    )
    repo.add(
        ActivityEntry.create(
            action="assignment.add",
            entity_type="task_assignment",
            entity_id="assign-2",
            module="project_management",
            actor_id="user-1",
            workspace_id="proj-1",
            parent_entity_id="task-2",
            human_message="assignment.add",
        )
    )
    session.commit()

    for_task_1 = repo.list_recent(parent_entity_id="task-1")
    assert {entry.action for entry in for_task_1} == {"assignment.add", "assignment.accept"}

    only_accept_actions = repo.list_recent(action_prefix="assignment.accept")
    assert len(only_accept_actions) == 1
    assert only_accept_actions[0].entity_id == "assign-1"

    only_assignment_actions = repo.list_recent(action_prefix="assignment.")
    assert {entry.entity_id for entry in only_assignment_actions} == {"assign-1", "assign-2"}
