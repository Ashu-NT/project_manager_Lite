"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): `BaselineApprovalParticipant` +
`build_baseline_approval_deps` -- proves the participant is genuinely session-parameterizable
(the Step-2 readiness criterion) and behaves identically to `BaselineService`'s own
`_apply_baseline_creation_decision` (kept unmodified -- `create_baseline`'s direct-apply path
still calls it too).
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.domain.scheduling.baseline import BaselineStatus
from src.core.modules.project_management.infrastructure.approval.baseline_apply_participant import (
    BaselineApprovalParticipant,
)
from src.core.platform.contract.models.approval.contracts import ApprovalPostCommitEvent
from src.core.platform.domain.approval import ApprovalRequest
from src.infra.composition.approval_apply_dependencies.baseline import (
    build_baseline_approval_deps,
)
from src.infra.persistence.orm.base import Base


def _make_project(services, name: str = "Baseline Project"):
    return services["project_service"].create_project(name, "")


def _login(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


def _project_with_tasks(services):
    project = _make_project(services)
    task_service = services["task_service"]
    task_service.create_task(
        project.id, "Task A", start_date=date(2024, 1, 1), duration_days=2
    )
    task_service.create_task(
        project.id, "Task B", start_date=date(2024, 1, 3), duration_days=2
    )
    return project


def _approval_request(services, project, *, name: str = "My Baseline") -> ApprovalRequest:
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="test approval request"
    )
    return ApprovalRequest.create(
        request_type="baseline.create",
        entity_type="project_baseline",
        entity_id=project.id,
        tenant_id=tenant_id,
        project_id=project.id,
        organization_id=project.organization_id,
        payload={
            "project_id": project.id,
            "project_name": project.name,
            "name": name,
        },
        requested_by_user_id="requester-1",
        requested_by_username="requester",
    )


def _deps(services, session):
    return build_baseline_approval_deps(
        session,
        user_session=services["user_session"],
        tenant_context_service=services["tenant_context_service"],
        calendar=services["work_calendar_engine"],
        project_calendar_adapter=services["scheduling_engine"]._project_calendar_adapter,
    )


def test_participant_apply_creates_baseline_on_the_supplied_session(services, session):
    _login(services, "admin", "ChangeMe123!")
    project = _project_with_tasks(services)

    deps = _deps(services, session)
    request = _approval_request(services, project)

    result = BaselineApprovalParticipant().apply(request, deps)

    baseline = deps.baseline_service._baselines.get_latest_for_project(project.id)
    assert baseline is not None
    assert baseline.name == "My Baseline"
    assert baseline.status == BaselineStatus.DRAFT
    tasks = deps.baseline_service._baselines.list_tasks(baseline.id)
    assert len(tasks) == 2
    assert result.post_commit_events == (
        ApprovalPostCommitEvent("baseline_changed", project.id),
    )


def test_participant_never_calls_commit_or_rollback(services, session, monkeypatch):
    """The participant stages only -- the caller (today: ApprovalService on the shared Session;
    from Step 2 onward: its own PlatformUnitOfWork) owns transaction completion."""
    _login(services, "admin", "ChangeMe123!")
    project = _project_with_tasks(services)
    deps = _deps(services, session)
    request = _approval_request(services, project)

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("the participant must never commit or roll back its own Session")

    monkeypatch.setattr(type(session), "commit", _forbidden)
    monkeypatch.setattr(type(session), "rollback", _forbidden)

    BaselineApprovalParticipant().apply(request, deps)


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

        assert deps_a.baseline_service._session is session_a
        assert deps_b.baseline_service._session is session_b
        assert deps_a.baseline_service._baselines.session is session_a
        assert deps_b.baseline_service._baselines.session is session_b
        assert deps_a.baseline_service is not deps_b.baseline_service

        assert deps_a.baseline_service._sched is not deps_b.baseline_service._sched
        assert deps_a.baseline_service._sched._session is session_a
        assert deps_b.baseline_service._sched._session is session_b

        assert deps_a.baseline_service._activity_service is not (
            deps_b.baseline_service._activity_service
        )
        assert deps_a.baseline_service._activity_service._session is session_a
        assert deps_b.baseline_service._activity_service._session is session_b

        assert deps_a.baseline_service._approval_service is None, (
            "the apply path must never reach back into ApprovalService"
        )
        assert deps_b.baseline_service._approval_service is None
    finally:
        session_a.close()
        session_b.close()


def test_dependencies_factory_never_opens_its_own_session(services, session):
    deps = _deps(services, session)
    assert deps.baseline_service._session is session, (
        "the factory must use the supplied Session, never a fresh one"
    )
