"""Assignee accept/decline handoff for task assignments."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.core.modules.project_management.application.tasks.commands.assignment import (
    TaskAssignmentMixin,
)
from src.core.modules.project_management.domain.tasks.task import TaskAssignment
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, OperationNotPermittedError


class _FakeRepo:
    def __init__(self, items: dict[str, object]) -> None:
        self._items = items

    def get(self, item_id):
        return self._items.get(item_id)

    def update(self, item) -> None:
        self._items[item.id] = item

    def update_response_status_with_version_check(self, item, *, expected_version):
        assert item.version == expected_version
        self.update(item)
        return item


class _FakeAuditService:
    def record(self, **_kwargs) -> None:
        return None


class _FakeTaskUnitOfWork:
    def __init__(self, owner) -> None:
        self._owner = owner
        self.assignments = owner._assignment_repo
        self._enterprise_audit_service = _FakeAuditService()
        self._activity_service = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        return None

    def record_event(self, _event) -> None:
        return None

    def commit(self) -> None:
        self._owner._uow_commit_calls += 1


class _FakeSession:
    def __init__(self) -> None:
        self.commit_calls = 0
        self.rollback_calls = 0

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1


class _FakeAssignmentResponseService(TaskAssignmentMixin):
    def __init__(self, **attrs) -> None:
        self._uow_commit_calls = 0
        for key, value in attrs.items():
            setattr(self, key, value)

    def _active_task_scope(self, *, operation_label: str):
        del operation_label
        return SimpleNamespace(tenant_id="tenant-1", organization_id="org-1")

    def _task_uow(self):
        return _FakeTaskUnitOfWork(self)


def _make_fake_self(*, principal_user_id: str, assignment, task, resource, employee):
    return _FakeAssignmentResponseService(
        _assignment_repo=_FakeRepo({assignment.id: assignment}),
        _task_repo=_FakeRepo({task.id: task}),
        _resource_repo=_FakeRepo({resource.id: resource} if resource is not None else {}),
        _employee_repo=_FakeRepo({employee.id: employee} if employee is not None else {}),
        _user_session=SimpleNamespace(principal=SimpleNamespace(user_id=principal_user_id)),
        _session=_FakeSession(),
    )


@pytest.fixture(autouse=True)
def _bypass_permission_checks(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "src.core.modules.project_management.application.tasks.commands.assignment.require_permission",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.modules.project_management.application.tasks.commands.assignment.require_project_permission",
        lambda *args, **kwargs: None,
    )


def _seed(*, linked_user_id: str | None = "user-employee"):
    assignment = TaskAssignment.create("task-1", "res-1", allocation_percent=100.0)
    assignment.id = "assign-1"
    assignment.project_resource_id = "pr-1"
    task = SimpleNamespace(id="task-1", project_id="proj-1", name="Cable Pull")
    resource = SimpleNamespace(id="res-1", name="Alex Taylor", employee_id="emp-1" if linked_user_id else None)
    employee = SimpleNamespace(id="emp-1", user_id=linked_user_id) if linked_user_id else None
    return assignment, task, resource, employee


def test_accept_assignment_sets_status_and_timestamp():
    assignment, task, resource, employee = _seed()
    fake_self = _make_fake_self(
        principal_user_id="user-employee", assignment=assignment, task=task, resource=resource, employee=employee
    )

    result = fake_self.accept_assignment("assign-1")

    assert result.response_status == "accepted"
    assert result.responded_at is not None
    assert fake_self._uow_commit_calls == 1
    assert fake_self._session.commit_calls == 0


def test_decline_assignment_sets_status_and_timestamp():
    assignment, task, resource, employee = _seed()
    fake_self = _make_fake_self(
        principal_user_id="user-employee", assignment=assignment, task=task, resource=resource, employee=employee
    )

    result = fake_self.decline_assignment("assign-1", reason="Overloaded this sprint")

    assert result.response_status == "declined"
    assert result.responded_at is not None


def test_assignment_action_context_is_server_derived_for_assignee(monkeypatch: pytest.MonkeyPatch):
    assignment, task, resource, employee = _seed()
    fake_self = _make_fake_self(
        principal_user_id="user-employee",
        assignment=assignment,
        task=task,
        resource=resource,
        employee=employee,
    )
    monkeypatch.setattr(
        "src.core.modules.project_management.application.tasks.commands.assignment.get_authorization_engine",
        lambda: SimpleNamespace(
            has_permission=lambda *args, **kwargs: True,
            has_scope_permission=lambda *args, **kwargs: True,
        ),
    )

    context = fake_self.get_assignment_action_context("assign-1")

    assert context.can_manage is True
    assert context.can_accept is True
    assert context.can_decline is True


def test_assignment_response_cannot_reverse_a_completed_handoff():
    assignment, task, resource, employee = _seed()
    fake_self = _make_fake_self(
        principal_user_id="user-employee",
        assignment=assignment,
        task=task,
        resource=resource,
        employee=employee,
    )
    fake_self.accept_assignment("assign-1")

    with pytest.raises(BusinessRuleError) as exc:
        fake_self.decline_assignment("assign-1", reason="Changed my mind")

    assert exc.value.code == "ASSIGNMENT_ALREADY_RESPONDED"


def test_accept_assignment_rejects_non_assignee():
    assignment, task, resource, employee = _seed()
    fake_self = _make_fake_self(
        principal_user_id="someone-else", assignment=assignment, task=task, resource=resource, employee=employee
    )

    with pytest.raises(OperationNotPermittedError):
        fake_self.accept_assignment("assign-1")


def test_accept_assignment_raises_when_resource_has_no_linked_user():
    assignment, task, resource, employee = _seed(linked_user_id=None)
    fake_self = _make_fake_self(
        principal_user_id="user-employee", assignment=assignment, task=task, resource=resource, employee=employee
    )

    with pytest.raises(BusinessRuleError):
        fake_self.accept_assignment("assign-1")


def test_accept_assignment_raises_when_assignment_missing():
    fake_self = _FakeAssignmentResponseService(
        _assignment_repo=_FakeRepo({}),
        _task_repo=_FakeRepo({}),
        _resource_repo=_FakeRepo({}),
        _employee_repo=_FakeRepo({}),
        _user_session=SimpleNamespace(principal=SimpleNamespace(user_id="user-employee")),
        _session=_FakeSession(),
    )

    with pytest.raises(NotFoundError):
        fake_self.accept_assignment("missing-assignment")
