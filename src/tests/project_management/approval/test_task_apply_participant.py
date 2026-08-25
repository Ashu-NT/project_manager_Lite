"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): `TaskApprovalParticipant` +
`build_task_approval_deps` -- proves the participant is genuinely session-parameterizable
(the Step-2 readiness criterion) and behaves identically to `TaskService`'s own
``_apply_dependency_add_decision``/``_apply_dependency_remove_decision``/
``_apply_dependency_update_decision``/``_apply_task_scheduling_constraint_decision``/
``_apply_resource_leveling_plan_decision`` (all kept unmodified -- the direct-apply,
non-governed paths on `TaskService` still call them too).
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.domain.enums import ConstraintType, DependencyType
from src.core.modules.project_management.infrastructure.approval.task_apply_participant import (
    TaskApprovalParticipant,
)
from src.core.platform.contract.models.approval.contracts import ApprovalPostCommitEvent
from src.core.platform.domain.approval import ApprovalRequest
from src.infra.composition.approval_apply_dependencies.task import build_task_approval_deps
from src.infra.persistence.orm.base import Base


def _login(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


def _make_two_tasks(services, name: str = "Task Approval Participant"):
    ps = services["project_service"]
    ts = services["task_service"]
    project = ps.create_project(name, "")
    a = ts.create_task(project.id, "Task A", "", start_date=date(2026, 9, 1), duration_days=2)
    b = ts.create_task(project.id, "Task B", "", duration_days=2)
    return project, a, b


def _make_task(services, name: str = "Task Approval Participant Constraint"):
    ps = services["project_service"]
    ts = services["task_service"]
    project = ps.create_project(name, "")
    task = ts.create_task(project.id, "Constrained Task", "", start_date=date(2026, 9, 1), duration_days=3)
    return project, task


def _dependency_add_request(project, predecessor, successor) -> ApprovalRequest:
    return ApprovalRequest.create(
        request_type="dependency.add",
        entity_type="task_dependency",
        entity_id=successor.id,
        project_id=project.id,
        organization_id=project.organization_id,
        payload={
            "predecessor_id": predecessor.id,
            "predecessor_name": predecessor.name,
            "successor_id": successor.id,
            "successor_name": successor.name,
            "dependency_type": DependencyType.FINISH_TO_START.value,
            "lag_days": 0,
        },
        requested_by_user_id="requester-1",
        requested_by_username="requester",
    )


def _constraint_update_request(project, task, *, constraint_type, constraint_date) -> ApprovalRequest:
    return ApprovalRequest.create(
        request_type="task.constraint.update",
        entity_type="task",
        entity_id=task.id,
        project_id=project.id,
        organization_id=project.organization_id,
        payload={
            "task_id": task.id,
            "task_name": task.name,
            "constraint_type": constraint_type.value if constraint_type is not None else None,
            "constraint_date": constraint_date.isoformat() if constraint_date is not None else None,
            "expected_version": task.version,
        },
        requested_by_user_id="requester-1",
        requested_by_username="requester",
    )


def _deps(services, session):
    return build_task_approval_deps(
        session,
        user_session=services["user_session"],
        tenant_context_service=services["tenant_context_service"],
        work_calendar_engine=services["work_calendar_engine"],
        enterprise_calendar_resolver=services["enterprise_calendar_resolver"],
        calendar_assignment_service=services["calendar_assignment_service"],
    )


def test_participant_apply_dependency_add_adds_dependency_on_the_supplied_session(services, session):
    _login(services, "admin", "ChangeMe123!")
    project, a, b = _make_two_tasks(services)

    deps = _deps(services, session)
    request = _dependency_add_request(project, a, b)

    result = TaskApprovalParticipant().apply_dependency_add(request, deps)

    persisted = deps.task_service._dependency_repo.list_by_task(a.id)
    assert len(persisted) == 1
    assert persisted[0].predecessor_task_id == a.id
    assert persisted[0].successor_task_id == b.id
    assert persisted[0].dependency_type == DependencyType.FINISH_TO_START
    assert result.post_commit_events == (
        ApprovalPostCommitEvent("tasks_changed", project.id),
    )


def test_participant_apply_task_constraint_update_updates_task_on_the_supplied_session(services, session):
    _login(services, "admin", "ChangeMe123!")
    project, task = _make_task(services)

    deps = _deps(services, session)
    # A Friday -- a working day, matching test_task_constraint_governance.py's pattern.
    constraint_date = date(2026, 9, 18)
    request = _constraint_update_request(
        project, task, constraint_type=ConstraintType.MUST_START_ON, constraint_date=constraint_date
    )

    result = TaskApprovalParticipant().apply_task_constraint_update(request, deps)

    updated = deps.task_service._task_repo.get(task.id)
    assert updated.constraint_type is ConstraintType.MUST_START_ON
    assert updated.constraint_date == constraint_date
    assert updated.start_date == constraint_date
    assert result.post_commit_events == (
        ApprovalPostCommitEvent("tasks_changed", project.id),
    )


def test_participant_never_calls_commit_or_rollback(services, session, monkeypatch):
    """The participant stages only -- the caller (today: ApprovalService on the shared Session;
    from Step 2 onward: its own PlatformUnitOfWork) owns transaction completion."""
    _login(services, "admin", "ChangeMe123!")
    project, a, b = _make_two_tasks(services)
    deps = _deps(services, session)
    request = _dependency_add_request(project, a, b)

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("the participant must never commit or roll back its own Session")

    monkeypatch.setattr(type(session), "commit", _forbidden)
    monkeypatch.setattr(type(session), "rollback", _forbidden)

    TaskApprovalParticipant().apply_dependency_add(request, deps)


def test_dependencies_factory_binds_every_transaction_sensitive_field_to_the_supplied_session(
    tmp_path, services
):
    engine_a = create_engine(f"sqlite:///{tmp_path}/deps_a.db", future=True)
    engine_b = create_engine(f"sqlite:///{tmp_path}/deps_b.db", future=True)
    Base.metadata.create_all(engine_a)
    Base.metadata.create_all(engine_b)
    session_a = sessionmaker(bind=engine_a, future=True)()
    session_b = sessionmaker(bind=engine_b, future=True)()
    try:
        deps_a = _deps(services, session_a)
        deps_b = _deps(services, session_b)

        assert deps_a.task_service._session is session_a
        assert deps_b.task_service._session is session_b
        assert deps_a.task_service._task_repo.session is session_a
        assert deps_b.task_service._task_repo.session is session_b
        assert deps_a.task_service._dependency_repo.session is session_a
        assert deps_b.task_service._dependency_repo.session is session_b
        assert deps_a.task_service is not deps_b.task_service
        assert deps_a.task_service._activity_service is not deps_b.task_service._activity_service
        assert deps_a.task_service._activity_service._session is session_a
        assert deps_b.task_service._activity_service._session is session_b
        assert deps_a.task_service._scheduling_engine is not deps_b.task_service._scheduling_engine
        assert deps_a.task_service._scheduling_engine._session is session_a
        assert deps_b.task_service._scheduling_engine._session is session_b
        assert deps_a.task_service._approval_service is None, (
            "the apply path must never reach back into ApprovalService"
        )
        assert deps_b.task_service._approval_service is None
    finally:
        session_a.close()
        session_b.close()


def test_dependencies_factory_never_opens_its_own_session(services, session):
    deps = _deps(services, session)
    assert deps.task_service._session is session, (
        "the factory must use the supplied Session, never a fresh one"
    )
