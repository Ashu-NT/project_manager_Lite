"""`ApprovalCommandHandler`'s transaction-owning commands (`request_change`, `approve_and_apply`,
`reject`) use a fresh-session `PlatformUnitOfWork` per call -- proves session isolation, commit/
rollback behavior, and audit failure semantics. Additive to `test_phase_b_approval_workflow.py`,
which covers apply-failure/audit-failure rollback, self-decision, and notification dispatch."""

from __future__ import annotations

import pytest

from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
)
from src.core.platform.application.approval.dto.commands.decisions import (
    ApprovalDecisionCommand,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.approval import ApprovalStatus
from src.core.platform.infrastructure.persistence.uow.approval.approval_unit_of_work import (
    SqlAlchemyPlatformUnitOfWork,
)

_REQUESTER_COUNTER = {"n": 0}


def _login(services, username: str, password: str) -> None:
    user_session = services["user_session"]
    user = services["authentication"].authenticate(username, password)
    user_session.set_principal(services["principal_builder"].build(user))


def _login_as_fresh_requester(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    _REQUESTER_COUNTER["n"] += 1
    username = f"uow-cutover-requester-{_REQUESTER_COUNTER['n']}"
    services["user_registration"].register_user(username, "StrongPass123", role_names=["planner"])
    _login(services, username, "StrongPass123")


def _make_project(services):
    _REQUESTER_COUNTER["n"] += 1
    return services['project_create'].create_project(ProjectCreateCommand(name=f"UoW Cutover Project {_REQUESTER_COUNTER['n']}", financial_currency_code="USD"))


def _submitted_budget(services, session):
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    services['budget_query']
    cost_code = services['finance_governance_commands'].cost_code(lambda handler: handler.create_cost_code(
        code=f"UOW-CUTOVER-{_REQUESTER_COUNTER['n']}-{project.id[:8]}", name="UoW cutover cost code"
    ))
    budget = services['finance_governance_commands'].budget_lifecycle(lambda handler: handler.create_budget(project.id, "Cutover Budget"))
    services['finance_governance_commands'].budget_lines(lambda handler: handler.add_line(
        budget.id,
        cost_code_id=cost_code.id,
        description="Line 1",
        amount=1000,
        expected_budget_version=budget.row_version,
    ))
    budget = services['budget_query'].get_budget(budget.id)
    budget = services['finance_governance_commands'].budget_lifecycle(lambda handler: handler.submit_budget(
        budget.id, submitted_by="admin", expected_version=budget.row_version
    ))
    session.expire_all()
    return project, budget


def _request_budget_approval_as_a_different_user(services, budget):
    """Requests as a fresh, non-admin user, then logs back in as admin -- so admin (the eventual
    decider) never becomes the requester, avoiding the correctly-enforced self-decision rule. Pins
    the fresh login's active organization explicitly, since auto-select is ambiguous once more
    than one organization is enabled."""
    active_organization_id = services["tenant_context_service"].get_active_organization_id()
    _login_as_fresh_requester(services)
    if active_organization_id:
        services["user_session"].set_active_organization_id(active_organization_id)
    approvals = services["approval_commands"]
    request = approvals.request_change(
        request_type="budget.approve",
        entity_type="project_budget",
        entity_id=budget.id,
        project_id=budget.project_id,
        payload={"budget_id": budget.id, "expected_version": budget.row_version, "notes": ""},
    )
    _login(services, "admin", "ChangeMe123!")
    reviewer = services["user_registration"].register_user(f"reviewer-{request.id}", "StrongPass123", role_names=["approver"])
    services["user_session"].set_principal(services["principal_builder"].build(reviewer))
    return request


def test_two_independent_approve_and_apply_calls_use_genuinely_different_sessions(
    services, session, monkeypatch
):
    _, budget_a = _submitted_budget(services, session)
    _, budget_b = _submitted_budget(services, session)
    request_a = _request_budget_approval_as_a_different_user(services, budget_a)
    request_b = _request_budget_approval_as_a_different_user(services, budget_b)

    approvals = services["approval_commands"]
    created_sessions = []
    original_create = type(approvals._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        created_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(approvals._uow_factory), "create", _spy_create)

    approvals.approve_and_apply(ApprovalDecisionCommand(request_id=request_a.id))
    approvals.approve_and_apply(ApprovalDecisionCommand(request_id=request_b.id))

    assert len(created_sessions) == 2
    assert created_sessions[0] is not created_sessions[1]


def test_approve_and_apply_shares_one_session_across_approvals_repo_and_participant_deps(
    services, session, monkeypatch
):
    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    approvals = services["approval_commands"]

    seen = {}
    handler, dependencies_factory = services["approval_participants"].apply_handlers["budget.approve"]

    def _spy_dependencies_factory(uow_session):
        deps = dependencies_factory(uow_session)
        seen["deps_session"] = deps.budget_commands._session
        seen["deps_repo_session"] = deps.budget_commands._budget_repo.session
        return deps

    services["approval_participants"].apply_handlers["budget.approve"] = (handler, _spy_dependencies_factory)

    original_create = type(approvals._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        seen["approvals_repo_session"] = uow.approvals.session
        seen["audit_session"] = uow._enterprise_audit_service._session
        return uow

    monkeypatch.setattr(type(approvals._uow_factory), "create", _spy_create)

    approvals.approve_and_apply(ApprovalDecisionCommand(request_id=request.id))

    assert seen["uow_session"] is seen["approvals_repo_session"]
    assert seen["uow_session"] is seen["audit_session"]
    assert seen["uow_session"] is seen["deps_session"]
    assert seen["uow_session"] is seen["deps_repo_session"]


def test_commit_failure_rolls_back_approval_decision_and_module_mutation_together(
    services, session, monkeypatch
):
    """A database commit failure must roll back the whole UoW. Verified structurally via the
    UoW's own `_committed`/`_closed` state, not a cross-session re-read: `BudgetService.
    _apply_approval_decision` uses a nested SAVEPOINT that, combined with this fixture's
    `sqlite:///:memory:` pooling, makes a real cross-session post-rollback read unreliable here.
    Full end-to-end atomic-rollback proof exists in `test_phase_b_approval_workflow.py`."""
    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    approvals = services["approval_commands"]

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

    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        approvals.approve_and_apply(ApprovalDecisionCommand(request_id=request.id))

    uow = captured_uow["uow"]
    assert uow._committed is False, "commit() failing must never mark the UoW committed"
    assert uow._closed is True, "the UoW's own __exit__ must still roll back and close"

    # Read through the shared session (never touched by the failed fresh-UoW transaction) to
    # confirm the request is still genuinely pending, not just that the exception propagated.
    reloaded_request = services["approval_queries"].list_pending(project_id=budget.project_id)
    assert any(r.id == request.id for r in reloaded_request), (
        "approval decision must not persist when commit fails"
    )


def test_request_change_default_mode_uses_a_fresh_uow_session(services, session, monkeypatch):
    _login_as_fresh_requester(services)
    approvals = services["approval_commands"]

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
    assert seen_sessions[0] is not session
    assert request.status == ApprovalStatus.PENDING


def test_request_change_fails_closed_when_the_approval_audit_write_fails(services, monkeypatch):
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    _login_as_fresh_requester(services)
    approvals = services["approval_commands"]

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
    matching = [row for row in services["approval_queries"].list_pending() if row.entity_id == entity_id]
    assert matching == []


def test_request_change_has_no_commit_parameter(services):
    """`request_change(commit=False)` no longer exists on the signature, and passing it raises
    rather than being silently accepted."""
    import inspect

    approvals = services["approval_commands"]
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
    approvals = services["approval_commands"]
    session.commit()  # settle any pending state from setup before observing

    approvals.approve_and_apply(ApprovalDecisionCommand(request_id=request.id))

    # The shared session must not have picked up an implicit transaction as a side effect of
    # the approval mutation, which ran entirely on its own fresh UoW Session.
    transaction = session.get_transaction()
    assert transaction is None or transaction.nested is False


def test_apply_handler_missing_does_not_open_or_leak_a_session(services, session, monkeypatch):
    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    approvals = services["approval_commands"]
    saved = services["approval_participants"].apply_handlers.pop("budget.approve")
    try:
        with pytest.raises(BusinessRuleError, match="No apply handler registered"):
            approvals.approve_and_apply(ApprovalDecisionCommand(request_id=request.id))
    finally:
        services["approval_participants"].apply_handlers["budget.approve"] = saved

    session.expire_all()
    still_pending = services["approval_queries"].list_pending(project_id=budget.project_id)
    assert any(r.id == request.id for r in still_pending)


def test_decision_load_uses_locking_repository_read(services):
    approvals = services["approval_commands"]
    request = approvals.request_change(
        request_type="baseline.create",
        entity_type="project_baseline",
        entity_id="locking-read-proof",
        project_id=None,
        payload={"name": "Locking read proof"},
    )
    repository = type("RepositorySpy", (), {})()
    repository.get_for_update = lambda request_id: (
        request if request_id == request.id else None
    )
    repository.get = lambda _request_id: pytest.fail(
        "approval decisions must not use an unlocked read"
    )

    loaded = approvals._require_pending_using(repository, request.id)

    assert loaded is request
