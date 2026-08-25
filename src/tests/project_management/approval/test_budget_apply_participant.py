"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): `BudgetApprovalParticipant` +
`build_budget_approval_deps` -- proves the participant is genuinely session-parameterizable
(the Step-2 readiness criterion) and behaves identically to `BudgetService`'s own
`_apply_approval_decision`/`_apply_rejection_decision` (kept unmodified -- `approve_budget`/
`reject_budget`'s direct-apply path still calls them too).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.domain.financials.budget import BudgetStatus
from src.core.modules.project_management.infrastructure.approval.budget_apply_participant import (
    BudgetApprovalParticipant,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.models.approval.contracts import ApprovalPostCommitEvent
from src.core.platform.domain.approval import ApprovalRequest
from src.infra.composition.approval_apply_dependencies.budget import build_budget_approval_deps
from src.infra.persistence.orm.base import Base


def _make_project(services, name: str = "Budget Project"):
    return services["project_service"].create_project(name, financial_currency_code="USD")


def _login(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


def _submitted_budget(services, session):
    project = _make_project(services)
    budget_service = services["budget_service"]
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="APPROVAL-TEST", name="Approval test cost code"
    )
    budget = budget_service.create_budget(project.id, "Initial Budget")
    budget_service.add_line(
        budget.id,
        cost_code_id=cost_code.id,
        description="Line 1",
        amount=Decimal("1000"),
        expected_budget_version=budget.row_version,
    )
    budget = budget_service.get_budget(budget.id)
    budget = budget_service.submit_budget(
        budget.id, submitted_by="admin", expected_version=budget.row_version
    )
    session.expire_all()
    return project, budget


def _approval_request(budget, *, expected_version: int, notes: str = "") -> ApprovalRequest:
    return ApprovalRequest.create(
        request_type="budget.approve",
        entity_type="project_budget",
        entity_id=budget.id,
        project_id=budget.project_id,
        organization_id=budget.organization_id,
        payload={
            "budget_id": budget.id,
            "expected_version": expected_version,
            "notes": notes,
        },
        requested_by_user_id="requester-1",
        requested_by_username="requester",
    )


def _deps(services, session):
    return build_budget_approval_deps(
        session,
        user_session=services["user_session"],
        tenant_context_service=services["tenant_context_service"],
    )


def test_participant_apply_approves_budget_on_the_supplied_session(services, session):
    _login(services, "admin", "ChangeMe123!")
    project, budget = _submitted_budget(services, session)

    deps = _deps(services, session)
    request = _approval_request(budget, expected_version=budget.row_version)

    result = BudgetApprovalParticipant().apply(request, deps)

    approved = deps.budget_service._budget_repo.get(budget.id)
    assert approved.status == BudgetStatus.APPROVED
    assert approved.approved_by == services["user_session"].principal.user_id
    assert result.post_commit_events == (
        ApprovalPostCommitEvent("budgets_changed", project.id),
    )


def test_participant_never_calls_commit_or_rollback(services, session, monkeypatch):
    """The participant stages only -- the caller (today: ApprovalService on the shared Session;
    from Step 2 onward: its own PlatformUnitOfWork) owns transaction completion."""
    _login(services, "admin", "ChangeMe123!")
    _, budget = _submitted_budget(services, session)
    deps = _deps(services, session)
    request = _approval_request(budget, expected_version=budget.row_version)

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("the participant must never commit or roll back its own Session")

    monkeypatch.setattr(type(session), "commit", _forbidden)
    monkeypatch.setattr(type(session), "rollback", _forbidden)

    BudgetApprovalParticipant().apply(request, deps)


def test_participant_reject_requires_authenticated_actor(services, session):
    _login(services, "admin", "ChangeMe123!")
    _, budget = _submitted_budget(services, session)
    deps = build_budget_approval_deps(
        session,
        user_session=_BlankUserSession(),
        tenant_context_service=services["tenant_context_service"],
    )
    request = _approval_request(budget, expected_version=budget.row_version)

    with pytest.raises(BusinessRuleError, match="authenticated principal"):
        BudgetApprovalParticipant().reject(request, deps)


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

        assert deps_a.budget_service._session is session_a
        assert deps_b.budget_service._session is session_b
        assert deps_a.budget_service._budget_repo.session is session_a
        assert deps_b.budget_service._budget_repo.session is session_b
        assert deps_a.budget_service is not deps_b.budget_service
        assert deps_a.budget_service._enterprise_audit_service is not (
            deps_b.budget_service._enterprise_audit_service
        )
        assert deps_a.budget_service._enterprise_audit_service._session is session_a
        assert deps_b.budget_service._enterprise_audit_service._session is session_b
        assert deps_a.budget_service._approval_service is None, (
            "the apply path must never reach back into ApprovalService"
        )
    finally:
        session_a.close()
        session_b.close()


def test_dependencies_factory_never_opens_its_own_session(services, session):
    deps = _deps(services, session)
    assert deps.budget_service._session is session, (
        "the factory must use the supplied Session, never a fresh one"
    )
