"""Phase 1 team-collaboration notifications: task assignment + @mention dispatch."""

from __future__ import annotations

from types import SimpleNamespace

from src.core.modules.project_management.application.tasks.commands.assignment import (
    TaskAssignmentMixin,
)
from src.core.modules.project_management.application.collaboration.commands.collaboration_comments import (
    CollaborationCommentCommandMixin,
)
from src.core.modules.project_management.domain.collaboration import TaskComment


class _FakeEmployeeRepo:
    def __init__(self, employees: dict[str, object]) -> None:
        self._employees = employees

    def get(self, employee_id):
        return self._employees.get(employee_id)


class _FakeNotificationService:
    def __init__(self) -> None:
        self.dispatched: list[dict] = []

    def dispatch(self, **kwargs):
        self.dispatched.append(kwargs)
        return SimpleNamespace(id=f"notif-{len(self.dispatched)}")


# ---------------------------------------------------------------------------
# Task assignment -> assignee notification
# ---------------------------------------------------------------------------


def test_notify_task_assigned_dispatches_when_employee_linked_to_user():
    notification_service = _FakeNotificationService()
    fake_self = SimpleNamespace(
        _employee_repo=_FakeEmployeeRepo(
            {"emp-1": SimpleNamespace(id="emp-1", user_id="user-42")}
        ),
        _notification_service=notification_service,
    )
    task = SimpleNamespace(id="task-1", project_id="proj-1", name="Cable Pull")
    resource = SimpleNamespace(id="res-1", employee_id="emp-1")

    TaskAssignmentMixin._notify_task_assigned(fake_self, task=task, resource=resource)

    assert len(notification_service.dispatched) == 1
    call = notification_service.dispatched[0]
    assert call["recipient_user_id"] == "user-42"
    assert call["category"] == "pm.task.assigned.v1"
    assert "Cable Pull" in call["body"]
    assert call["metadata"]["task_id"] == "task-1"


def test_notify_task_assigned_noop_when_employee_has_no_linked_user():
    notification_service = _FakeNotificationService()
    fake_self = SimpleNamespace(
        _employee_repo=_FakeEmployeeRepo(
            {"emp-1": SimpleNamespace(id="emp-1", user_id=None)}
        ),
        _notification_service=notification_service,
    )
    task = SimpleNamespace(id="task-1", project_id="proj-1", name="Cable Pull")
    resource = SimpleNamespace(id="res-1", employee_id="emp-1")

    TaskAssignmentMixin._notify_task_assigned(fake_self, task=task, resource=resource)

    assert notification_service.dispatched == []


def test_notify_task_assigned_noop_when_resource_has_no_employee():
    notification_service = _FakeNotificationService()
    fake_self = SimpleNamespace(
        _employee_repo=_FakeEmployeeRepo({}),
        _notification_service=notification_service,
    )
    task = SimpleNamespace(id="task-1", project_id="proj-1", name="Cable Pull")
    resource = SimpleNamespace(id="res-1", employee_id=None)

    TaskAssignmentMixin._notify_task_assigned(fake_self, task=task, resource=resource)

    assert notification_service.dispatched == []


def test_notify_task_assigned_noop_when_resource_is_none():
    notification_service = _FakeNotificationService()
    fake_self = SimpleNamespace(
        _employee_repo=_FakeEmployeeRepo({}),
        _notification_service=notification_service,
    )
    task = SimpleNamespace(id="task-1", project_id="proj-1", name="Cable Pull")

    TaskAssignmentMixin._notify_task_assigned(fake_self, task=task, resource=None)

    assert notification_service.dispatched == []


# ---------------------------------------------------------------------------
# @mention -> mentioned-user notification
# ---------------------------------------------------------------------------


def _make_comment(mentioned_user_ids: list[str]) -> TaskComment:
    return TaskComment.create(
        task_id="task-1",
        author_user_id="user-author",
        author_username="alice",
        body="please review @bob and @carol",
        mentions=["bob", "carol"],
        mentioned_user_ids=mentioned_user_ids,
    )


def test_notify_mentioned_users_dispatches_to_each_mentioned_user_excluding_author():
    notification_service = _FakeNotificationService()
    fake_self = SimpleNamespace(_notification_service=notification_service)
    task = SimpleNamespace(id="task-1", project_id="proj-1", name="Cable Pull")
    comment = _make_comment(["user-author", "user-bob", "user-carol"])

    CollaborationCommentCommandMixin._notify_mentioned_users(
        fake_self, task=task, comment=comment, author_user_id="user-author"
    )

    recipients = {call["recipient_user_id"] for call in notification_service.dispatched}
    assert recipients == {"user-bob", "user-carol"}
    assert all(
        call["category"] == "pm.comment.mentioned.v1" for call in notification_service.dispatched
    )
    assert all("Cable Pull" in call["body"] for call in notification_service.dispatched)


def test_notify_mentioned_users_noop_when_no_mentions():
    notification_service = _FakeNotificationService()
    fake_self = SimpleNamespace(_notification_service=notification_service)
    task = SimpleNamespace(id="task-1", project_id="proj-1", name="Cable Pull")
    comment = _make_comment([])

    CollaborationCommentCommandMixin._notify_mentioned_users(
        fake_self, task=task, comment=comment, author_user_id="user-author"
    )

    assert notification_service.dispatched == []
