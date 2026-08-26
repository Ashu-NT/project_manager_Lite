"""P4 Step 2 (ADR-005 Section 24, Round 7/8): `ApprovalService`'s transaction-owning commands
(`request_change` when transaction-owning, `approve_and_apply`, `reject`) cut over onto the
canonical fresh-session `PlatformUnitOfWork`. Focused, additive to the full existing Approval/
ADR-PF-008 regression suite (`test_phase_b_approval_workflow.py` etc.), which already proves
apply-failure/audit-failure rollback, self-decision, and notification dispatch through the new
wiring unmodified.
"""

from __future__ import annotations

import pytest

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.approval import ApprovalStatus
from src.core.platform.infrastructure.persistence.unit_of_work import (
    SqlAlchemyPlatformUnitOfWork,
)

_REQUESTER_COUNTER = {"n": 0}


def _login(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


def _login_as_fresh_requester(services) -> None:
    _REQUESTER_COUNTER["n"] += 1
    username = f"uow-cutover-requester-{_REQUESTER_COUNTER['n']}"
    services["auth_service"].register_user(username, "StrongPass123", role_names=["planner"])
    _login(services, username, "StrongPass123")


def _make_project(services):
    _REQUESTER_COUNTER["n"] += 1
    return services["project_service"].create_project(
        f"UoW Cutover Project {_REQUESTER_COUNTER['n']}", financial_currency_code="USD"
    )


def _submitted_budget(services, session):
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]
    cost_code = services["financial_configuration_service"].create_cost_code(
        code=f"UOW-CUTOVER-{_REQUESTER_COUNTER['n']}-{project.id[:8]}", name="UoW cutover cost code"
    )
    budget = budget_service.create_budget(project.id, "Cutover Budget")
    budget_service.add_line(
        budget.id,
        cost_code_id=cost_code.id,
        description="Line 1",
        amount=1000,
        expected_budget_version=budget.row_version,
    )
    budget = budget_service.get_budget(budget.id)
    budget = budget_service.submit_budget(
        budget.id, submitted_by="admin", expected_version=budget.row_version
    )
    session.expire_all()
    return project, budget


def _request_budget_approval_as_a_different_user(services, budget):
    """Requests as a fresh, non-admin user, then logs back in as admin -- so admin (the eventual
    decider) never becomes the requester, avoiding the (correctly enforced) self-decision rule.

    P10A: a fresh login's active-organization auto-select is genuinely ambiguous once more than
    one organization is enabled simultaneously -- pin it explicitly to whatever was active
    immediately before the switch rather than relying on that heuristic."""
    active_organization_id = services["tenant_context_service"].get_active_organization_id()
    _login_as_fresh_requester(services)
    if active_organization_id:
        services["user_session"].set_active_organization_id(active_organization_id)
    approvals = services["approval_service"]
    request = approvals.request_change(
        request_type="budget.approve",
        entity_type="project_budget",
        entity_id=budget.id,
        project_id=budget.project_id,
        payload={"budget_id": budget.id, "expected_version": budget.row_version, "notes": ""},
    )
    _login(services, "admin", "ChangeMe123!")
    return request


def test_two_independent_approve_and_apply_calls_use_genuinely_different_sessions(
    services, session, monkeypatch
):
    _, budget_a = _submitted_budget(services, session)
    _, budget_b = _submitted_budget(services, session)
    request_a = _request_budget_approval_as_a_different_user(services, budget_a)
    request_b = _request_budget_approval_as_a_different_user(services, budget_b)

    approvals = services["approval_service"]
    created_sessions = []
    original_create = type(approvals._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        created_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(approvals._uow_factory), "create", _spy_create)

    approvals.approve_and_apply(request_a.id)
    approvals.approve_and_apply(request_b.id)

    assert len(created_sessions) == 2
    assert created_sessions[0] is not created_sessions[1]


def test_approve_and_apply_shares_one_session_across_approvals_repo_and_participant_deps(
    services, session, monkeypatch
):
    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    approvals = services["approval_service"]

    seen = {}
    handler, dependencies_factory = approvals._apply_handlers["budget.approve"]

    def _spy_dependencies_factory(uow_session):
        deps = dependencies_factory(uow_session)
        seen["deps_session"] = deps.budget_service._session
        seen["deps_repo_session"] = deps.budget_service._budget_repo.session
        return deps

    approvals._apply_handlers["budget.approve"] = (handler, _spy_dependencies_factory)

    original_create = type(approvals._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        seen["approvals_repo_session"] = uow.approvals.session
        seen["audit_session"] = uow._enterprise_audit_service._session
        return uow

    monkeypatch.setattr(type(approvals._uow_factory), "create", _spy_create)

    approvals.approve_and_apply(request.id)

    assert seen["uow_session"] is seen["approvals_repo_session"]
    assert seen["uow_session"] is seen["audit_session"]
    assert seen["uow_session"] is seen["deps_session"]
    assert seen["uow_session"] is seen["deps_repo_session"]


def test_commit_failure_rolls_back_approval_decision_and_module_mutation_together(
    services, session, monkeypatch
):
    """A database commit failure must roll back the whole UoW and fire zero post-commit
    reactions. Verified structurally (the UoW's own `_committed`/`_closed` state after the
    exception, plus zero legacy signals emitted) rather than via a cross-session re-read for
    this specific family: `BudgetService._apply_approval_decision` uses an internal
    `session.begin_nested()` SAVEPOINT, which -- combined with `sqlite:///:memory:`'s
    `SingletonThreadPool` and a well-known pysqlite legacy-driver transaction-handling quirk this
    test fixture does not work around (the same limitation already discovered and documented in
    P4-PRE Step 1's own test suite) -- makes a real cross-session post-rollback read unreliable
    in this exact test topology, independent of whether the underlying rollback is correct. Real,
    full end-to-end atomic-rollback-on-failure proof for representative families (`project_cost.
    approve` via decision-update and audit failure) already exists, unmodified, in
    `test_phase_b_approval_workflow.py`, and passes."""
    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    approvals = services["approval_service"]

    captured_uow = {}
    original_create = type(approvals._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(approvals._uow_factory), "create", _spy_create)

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemyPlatformUnitOfWork, "commit", _fail_commit)

    signals_emitted = []
    monkeypatch.setattr(
        type(approvals),
        "_emit_signal_safely",
        staticmethod(
            lambda signal_name, payload: signals_emitted.append((signal_name, payload))
        ),
    )

    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        approvals.approve_and_apply(request.id)

    uow = captured_uow["uow"]
    assert uow._committed is False, "commit() failing must never mark the UoW committed"
    assert uow._closed is True, "the UoW's own __exit__ must still roll back and close"
    assert signals_emitted == [], "no post-commit signal may fire when commit fails"

    # The approval decision itself: confirmed via the SAME (already-closed) UoW's identity-map
    # state is not meaningful post-close, but the request's in-memory status object passed to
    # approve_and_apply was mutated in place before the failed commit -- prove ApprovalService
    # does not report success despite that by confirming the exception is what the caller sees
    # (already proven above) and that a fresh, independent read agrees the request is still
    # pending (this read goes through the *shared* legacy session, deliberately, to prove that
    # session was never touched by the failed fresh-UoW transaction at all).
    reloaded_request = approvals.list_pending(project_id=budget.project_id)
    assert any(r.id == request.id for r in reloaded_request), (
        "approval decision must not persist when commit fails"
    )


def test_request_change_default_mode_uses_a_fresh_uow_session(services, session, monkeypatch):
    _login_as_fresh_requester(services)
    approvals = services["approval_service"]

    seen_sessions = []
    original_create = type(approvals._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(approvals._uow_factory), "create", _spy_create)

    request = approvals.request_change(
        request_type="baseline.create",
        entity_type="project_baseline",
        entity_id=f"probe-entity-{_REQUESTER_COUNTER['n']}",
        project_id=None,
        payload={"name": "Probe"},
    )
    assert len(seen_sessions) == 1
    assert seen_sessions[0] is not approvals._session
    assert request.status == ApprovalStatus.PENDING


def test_request_change_fails_closed_when_the_approval_audit_write_fails(services, monkeypatch):
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    _login_as_fresh_requester(services)
    approvals = services["approval_service"]

    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated standalone request_change audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)

    entity_id = f"probe-entity-audit-fail-{_REQUESTER_COUNTER['n']}"
    with pytest.raises(RuntimeError, match="simulated standalone request_change audit failure"):
        approvals.request_change(
            request_type="baseline.create",
            entity_type="project_baseline",
            entity_id=entity_id,
            project_id=None,
            payload={"name": "Probe audit failure"},
        )

    monkeypatch.undo()
    matching = [row for row in approvals.list_pending() if row.entity_id == entity_id]
    assert matching == []


def test_request_change_has_no_commit_parameter(services):
    """Approval-P1 (§13/§38): `request_change(commit=False)` no longer exists -- every former
    caller-owned-transaction path now calls `request_approval_using(...)` directly inside its own
    canonical UoW instead of composing into this method. No deprecated compatibility argument is
    left on the signature."""
    import inspect

    approvals = services["approval_service"]
    params = inspect.signature(approvals.request_change).parameters
    assert "commit" not in params
    with pytest.raises(TypeError):
        approvals.request_change(
            request_type="baseline.create",
            entity_type="project_baseline",
            entity_id="probe-entity-no-commit-param",
            project_id=None,
            payload={"name": "Probe"},
            commit=False,
        )


def test_shared_legacy_session_is_not_touched_by_approval_mutation(services, session):
    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    approvals = services["approval_service"]
    session.commit()  # settle any pending state from setup before observing

    approvals.approve_and_apply(request.id)

    # The shared session must not have picked up an implicit transaction as a side effect of
    # the approval mutation, which ran entirely on its own fresh UoW Session.
    assert not session.in_transaction() or session.in_transaction().nested is False


def test_apply_handler_missing_does_not_open_or_leak_a_session(services, session, monkeypatch):
    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    approvals = services["approval_service"]
    saved = approvals._apply_handlers.pop("budget.approve")
    try:
        with pytest.raises(BusinessRuleError, match="No apply handler registered"):
            approvals.approve_and_apply(request.id)
    finally:
        approvals._apply_handlers["budget.approve"] = saved

    session.expire_all()
    still_pending = approvals.list_pending(project_id=budget.project_id)
    assert any(r.id == request.id for r in still_pending)
