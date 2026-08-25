"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): `ProjectCostApprovalParticipant` +
`build_project_cost_approval_deps` -- proves the participant is genuinely
session-parameterizable (the Step-2 readiness criterion) and behaves identically to
`ProjectCostEntryService`'s own `_apply_approval_decision`/`_apply_rejection_decision` (kept
unmodified -- `approve()`/`reject()`'s direct-apply path still calls them too).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.domain.financials.cost_entry import ProjectCostEntryStatus
from src.core.modules.project_management.infrastructure.approval.project_cost_apply_participant import (
    ProjectCostApprovalParticipant,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.models.approval.contracts import ApprovalPostCommitEvent
from src.core.platform.domain.approval import ApprovalRequest
from src.infra.composition.approval_apply_dependencies.project_cost import (
    build_project_cost_approval_deps,
)
from src.infra.persistence.orm.base import Base


def _make_project(services, name: str = "Cost Entry Project"):
    return services["project_service"].create_project(name)


def _login(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


def _submitted_entry(services, session):
    organization = services["organization_service"].get_active_organization()
    project = _make_project(services)
    cost_entry_service = services["cost_entry_service"]
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="APPROVAL-TEST", name="Approval test cost code"
    )
    entry = cost_entry_service.create_manual_entry(
        project_id=project.id,
        command_id=f"{project.id}-command",
        description="Travel",
        amount=Decimal("100"),
        currency_code=organization.base_currency,
        transaction_date=date(2026, 1, 10),
        cost_code_id=cost_code.id,
    )
    entry = cost_entry_service.submit(entry.id, expected_version=entry.row_version)
    session.expire_all()
    return project, entry


def _approval_request(entry, *, expected_version: int, notes: str = "") -> ApprovalRequest:
    return ApprovalRequest.create(
        request_type="project_cost.approve",
        entity_type="project_cost_entry",
        entity_id=entry.id,
        project_id=entry.project_id,
        organization_id=entry.organization_id,
        payload={
            "entry_id": entry.id,
            "expected_version": expected_version,
            "notes": notes,
        },
        requested_by_user_id="requester-1",
        requested_by_username="requester",
    )


def _deps(services, session):
    return build_project_cost_approval_deps(
        session,
        user_session=services["user_session"],
        tenant_context_service=services["tenant_context_service"],
        financial_period_service=services["financial_period_service"],
    )


def test_participant_apply_approves_entry_on_the_supplied_session(services, session):
    _login(services, "admin", "ChangeMe123!")
    project, entry = _submitted_entry(services, session)

    deps = _deps(services, session)
    request = _approval_request(entry, expected_version=entry.row_version)

    result = ProjectCostApprovalParticipant().apply(request, deps)

    approved = deps.cost_entry_service._entry_repo.get(entry.id)
    assert approved.status == ProjectCostEntryStatus.APPROVED
    assert result.post_commit_events == (
        ApprovalPostCommitEvent("cost_entries_changed", project.id),
    )


def test_participant_never_calls_commit_or_rollback(services, session, monkeypatch):
    """The participant stages only -- the caller (today: ApprovalService on the shared Session;
    from Step 2 onward: its own PlatformUnitOfWork) owns transaction completion."""
    _login(services, "admin", "ChangeMe123!")
    _, entry = _submitted_entry(services, session)
    deps = _deps(services, session)
    request = _approval_request(entry, expected_version=entry.row_version)

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("the participant must never commit or roll back its own Session")

    monkeypatch.setattr(type(session), "commit", _forbidden)
    monkeypatch.setattr(type(session), "rollback", _forbidden)

    ProjectCostApprovalParticipant().apply(request, deps)


def test_participant_reject_requires_authenticated_actor(services, session):
    _login(services, "admin", "ChangeMe123!")
    _, entry = _submitted_entry(services, session)
    deps = build_project_cost_approval_deps(
        session,
        user_session=_BlankUserSession(),
        tenant_context_service=services["tenant_context_service"],
        financial_period_service=services["financial_period_service"],
    )
    request = _approval_request(entry, expected_version=entry.row_version)

    with pytest.raises(BusinessRuleError, match="authenticated principal"):
        ProjectCostApprovalParticipant().reject(request, deps)


class _BlankUserSession:
    principal = None


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

        assert deps_a.cost_entry_service._session is session_a
        assert deps_b.cost_entry_service._session is session_b
        assert deps_a.cost_entry_service._entry_repo.session is session_a
        assert deps_b.cost_entry_service._entry_repo.session is session_b
        assert deps_a.cost_entry_service is not deps_b.cost_entry_service
        assert deps_a.cost_entry_service._enterprise_audit_service is not (
            deps_b.cost_entry_service._enterprise_audit_service
        )
        assert deps_a.cost_entry_service._enterprise_audit_service._session is session_a
        assert deps_b.cost_entry_service._enterprise_audit_service._session is session_b
        assert deps_a.cost_entry_service._approval_service is None, (
            "the apply path must never reach back into ApprovalService"
        )
    finally:
        session_a.close()
        session_b.close()


def test_dependencies_factory_never_opens_its_own_session(services, session):
    deps = _deps(services, session)
    assert deps.cost_entry_service._session is session, (
        "the factory must use the supplied Session, never a fresh one"
    )
