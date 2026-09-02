"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): `FinancialChangeApprovalParticipant` +
`build_financial_change_approval_deps` -- proves the participant is genuinely
session-parameterizable (the Step-2 readiness criterion), reproduces the
`_apply_financial_change`/`_reject_financial_change` closures' exact conditional
post-commit-event construction, and behaves identically to `FinancialChangeService`'s own
`_apply_approval_decision`/`_apply_rejection_decision` (kept unmodified).

Test-scope note: a BUDGET-only impact is enough to exercise the real, end-to-end apply path
(including the `budgets_changed` branch of the conditional event list) without reproducing a
full budget+forecast+schedule scenario -- `forecasts_changed`/`tasks_changed` not appearing for
a BUDGET-only change is itself a meaningful assertion about the conditional logic. The FORECAST
and SCHEDULE branches of that same conditional (and the schedule-impact path through the real,
fully-wired `TaskService`) are already covered end-to-end by the existing
`test_project_finance_change_orders.py` suite (run as part of this task's regression pass); this
file does not duplicate that scenario building.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpactType,
    FinancialChangeStatus,
)
from src.core.modules.project_management.application.financials.invalidation import (
    invalidation_scope,
)
from src.core.modules.project_management.infrastructure.approval.financial_change_apply_participant import (
    FinancialChangeApprovalParticipant,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.models.approval.contracts import ApprovalPostCommitEvent
from src.infra.composition.approval_apply_dependencies.financial_change import (
    build_financial_change_approval_deps,
)
from src.infra.persistence.orm.base import Base


def _login(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


def _seed_approved_budget(services):
    project = services["project_service"].create_project(
        "FC Approval Test Project", financial_currency_code="USD"
    )
    code = services["financial_configuration_service"].create_cost_code(
        code="FC-APPROVAL-TEST", name="FC approval test cost code"
    )
    budgets = services["budget_service"]
    budget = budgets.create_budget(project.id, "Approved control budget")
    budget_line = budgets.add_line(
        budget.id,
        cost_code_id=code.id,
        description="Approved scope",
        amount=Decimal("100"),
        expected_budget_version=budget.row_version,
    )
    budget = budgets.get_budget(budget.id)
    budget = budgets.submit_budget(
        budget.id, "admin", expected_version=budget.row_version
    )
    result = budgets.approve_budget(
        budget.id, approved_by="admin", expected_version=budget.row_version
    )
    budget = budgets.get_budget(result.budget_id)
    return project, code, budget, budget_line


def _submitted_change(services, session):
    project, code, budget, budget_line = _seed_approved_budget(services)
    changes = services["financial_change_service"]
    principal = services["user_session"].principal
    change = changes.create_change(
        project.id,
        title="Approved scope adjustment",
        reason="Customer-approved engineering change",
        effective_date=date(2026, 8, 11),
        created_by=principal.user_id,
    )
    changes.add_impact(
        change.id,
        impact_type=FinancialChangeImpactType.BUDGET,
        description="Increase approved scope",
        amount=Decimal("25"),
        cost_code_id=code.id,
        target_line_id=budget_line.id,
        expected_change_version=change.row_version,
    )
    change = changes.get_change(change.id)
    change = changes.submit_change(
        change.id,
        submitted_by=principal.user_id,
        expected_version=change.row_version,
    )
    session.expire_all()
    request = services["approval_service"].list_pending(project_id=project.id)[0]
    return project, change, request


def _deps(services, session):
    return build_financial_change_approval_deps(
        session,
        user_session=services["user_session"],
        tenant_context_service=services["tenant_context_service"],
        work_calendar_engine=services["work_calendar_engine"],
    )


def test_participant_apply_applies_change_on_the_supplied_session_with_budget_only_events(
    services, session
):
    _login(services, "admin", "ChangeMe123!")
    project, change, request = _submitted_change(services, session)
    deps = _deps(services, session)

    result = FinancialChangeApprovalParticipant().apply(request, deps)

    applied = deps.financial_change_service._change_repo.get(change.id)
    assert applied.status is FinancialChangeStatus.APPLIED
    assert applied.applied_budget_id
    assert applied.applied_forecast_id is None
    assert not applied.applied_schedule_count
    assert result.post_commit_events == (
        ApprovalPostCommitEvent("financial_changes_changed", invalidation_scope(applied)),
        ApprovalPostCommitEvent("budgets_changed", project.id),
    )


def test_participant_reject_rejects_change_on_the_supplied_session(services, session):
    _login(services, "admin", "ChangeMe123!")
    _, change, request = _submitted_change(services, session)
    deps = _deps(services, session)

    result = FinancialChangeApprovalParticipant().reject(request, deps)

    rejected = deps.financial_change_service._change_repo.get(change.id)
    assert rejected.status is FinancialChangeStatus.REJECTED
    assert result.post_commit_events == (
        ApprovalPostCommitEvent("financial_changes_changed", invalidation_scope(rejected)),
    )


def test_participant_never_calls_commit_or_rollback(services, session, monkeypatch):
    """The participant stages only -- the caller (today: ApprovalService on the shared Session;
    from Step 2 onward: its own PlatformUnitOfWork) owns transaction completion."""
    _login(services, "admin", "ChangeMe123!")
    _, _, request = _submitted_change(services, session)
    deps = _deps(services, session)

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("the participant must never commit or roll back its own Session")

    monkeypatch.setattr(type(session), "commit", _forbidden)
    monkeypatch.setattr(type(session), "rollback", _forbidden)

    FinancialChangeApprovalParticipant().apply(request, deps)


def test_participant_apply_requires_authenticated_actor(services, session):
    _login(services, "admin", "ChangeMe123!")
    _, _, request = _submitted_change(services, session)
    deps = build_financial_change_approval_deps(
        session,
        user_session=_BlankUserSession(),
        tenant_context_service=services["tenant_context_service"],
        work_calendar_engine=services["work_calendar_engine"],
    )

    with pytest.raises(BusinessRuleError, match="authenticated principal"):
        FinancialChangeApprovalParticipant().apply(request, deps)


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

        change_service_a = deps_a.financial_change_service
        change_service_b = deps_b.financial_change_service

        assert change_service_a._session is session_a
        assert change_service_b._session is session_b
        assert change_service_a._change_repo.session is session_a
        assert change_service_b._change_repo.session is session_b
        assert change_service_a is not change_service_b
        assert change_service_a._enterprise_audit_service is not (
            change_service_b._enterprise_audit_service
        )
        assert change_service_a._enterprise_audit_service._session is session_a
        assert change_service_b._enterprise_audit_service._session is session_b
        assert change_service_a._approval_service is None, (
            "the apply path must never reach back into ApprovalService"
        )

        task_service_a = change_service_a._task_service
        task_service_b = change_service_b._task_service
        assert task_service_a is not task_service_b
        assert task_service_a._session is session_a
        assert task_service_b._session is session_b
        assert task_service_a._task_repo.session is session_a
        assert task_service_b._task_repo.session is session_b
        assert task_service_a._approval_service is None, (
            "the fresh TaskService must never reach back into ApprovalService either"
        )
        assert task_service_a._scheduling_engine is not task_service_b._scheduling_engine
        assert task_service_a._scheduling_engine._session is session_a
        assert task_service_b._scheduling_engine._session is session_b
        assert task_service_a._activity_service is not task_service_b._activity_service
        assert task_service_a._activity_service._session is session_a
        assert task_service_b._activity_service._session is session_b
    finally:
        session_a.close()
        session_b.close()


def test_dependencies_factory_never_opens_its_own_session(services, session):
    deps = _deps(services, session)
    assert deps.financial_change_service._session is session, (
        "the factory must use the supplied Session, never a fresh one"
    )
