"""Approval-P1A (verification-closure pass): same-tenant, cross-organization Approval
authorization.

`ApprovalRequest` now carries authoritative `tenant_id` + `organization_id` (Approval-P1). This
file proves the actual invariant the codebase's authorization model provides for `approve_and_apply`
/`reject`:

- `ApprovalService.approve_and_apply`/`reject` require only the GLOBAL role permission
  `approval.decide` (see `require_permission(self._user_session, "approval.decide", ...)` --
  there is no per-organization-scoped "decide" grant for Approval). The organization boundary is
  enforced entirely by `SqlAlchemyApprovalRepository.get()`'s ambient
  `TenantScopedRepositorySupport._context()` filter, which requires the SESSION's active
  organization (`TenantContextService`, driven by `UserSessionContext.active_organization_id()`
  -- never `OrganizationService.get_active_organization()`'s DB-level "single business-active
  org per tenant" flag, which is a different, unrelated concept) to match the request's own
  `organization_id` (or its project's organization) -- confirmed by reading `approval_service.py`
  (`_require_pending_using` -> `uow.approvals.get(...)` ->
  `_assert_project_in_active_organization_using`).
- `OrganizationService.set_active_organization` requires only the global `settings.manage`
  permission, with NO per-organization membership check -- switching the session's active
  organization is itself a coarse-grained, tenant-wide capability, not an org-specific grant, and
  is the ONLY way this codebase changes which organization's data (including Approval requests)
  is visible to `uow.approvals.get(...)`.

Given that authorization model, the correct invariant to prove is: an actor holding the global
`approval.decide` permission, with Org A2 active, cannot decide an Approval that belongs to Org
A1 -- regardless of same-tenant membership -- because the request's own `organization_id` (A1)
never matches the active organization (A2). This is true structurally (the row is invisible to
`uow.approvals.get(...)`), not merely a permission-check outcome, so it cannot be bypassed by
holding more permissions.

The complementary "explicit cross-org authority while A2 remains active" case (§3 of the
Approval-P1A request) is **N/A**: nothing in this codebase's Approval authorization model grants
decide authority over a non-active organization's request while a different organization is
active. The only way to decide Org A1's request is to make A1 the active organization first
(itself gated only by the coarse-grained `settings.manage` permission, not per-org membership).
`test_actor_gains_authority_only_after_switching_active_organization_to_the_target_org` proves
this "switch first" requirement is real (decide fails before the switch, succeeds after), which is
the evidence for the N/A determination -- there is no simultaneous multi-org decide capability to
test as a distinct code path.

§4 (cross-tenant isolation must remain strict) is proven in
`test_platform_unit_of_work.py::test_cross_tenant_context_cannot_read_another_tenants_approval_
request` -- cited/re-run here, not duplicated: that test already proves a genuinely different
`TenantContextService` (bound to Tenant B) cannot read a Tenant A `ApprovalRequest` via
`uow.approvals.get(...)`, which is the exact mechanism `approve_and_apply`/`reject` depend on.
"""

from __future__ import annotations

import pytest

from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.domain.approval import ApprovalStatus

_COUNTER = {"n": 0}


def _unique(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _login(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


def _session_active_organization_id(services) -> str | None:
    """The SESSION-scoped active organization -- what `ApprovalService`/`SqlAlchemyApprovalRepository`
    actually use for scoping. Deliberately NOT `OrganizationService.get_active_organization()`,
    which reads a different, DB-level "single business-active organization per tenant" flag that
    `create_organization(is_enabled=True)` (the default) flips independently of session state."""
    return services["tenant_context_service"].get_active_organization_id()


def _create_second_org_in_same_tenant(services):
    """Org A2, created with `is_active=False` so it never touches the DB-level "single
    business-active organization per tenant" flag (an unrelated concept -- see module docstring)
    -- the session's real active organization (Org A1) must stay untouched by mere creation."""
    organization_service = services["organization_service"]
    org_a1_session_id = _session_active_organization_id(services)
    assert org_a1_session_id is not None
    org_a1 = services["tenant_context_service"].get_active_organization()
    assert org_a1.id == org_a1_session_id
    org_a2 = organization_service.create_organization(
        organization_code=_unique("XORG-A2"), display_name="Same-Tenant Org A2", is_enabled=False
    )
    assert _session_active_organization_id(services) == org_a1_session_id
    return org_a1, org_a2


def _request_pending_approval_in_org_a1(services, *, org_a1_id: str):
    """Requests a standalone-path Approval while Org A1 is the session's active organization --
    `ApprovalRequest.organization_id`/`tenant_id` are stamped from that active context at creation
    time (Approval-P1's authoritative-ownership rule), never re-derived afterward."""
    assert _session_active_organization_id(services) == org_a1_id
    approvals = services["approval_service"]
    request = approvals.request_change(
        request_type="baseline.create",
        entity_type="project_baseline",
        entity_id=_unique("xorg-probe-entity"),
        project_id=None,
        payload={"name": "Cross-org probe"},
    )
    assert request.organization_id == org_a1_id
    return request


def test_actor_with_decide_permission_cannot_reach_org_a1_approval_while_org_a2_is_active(
    services,
):
    """Negative case (§2): Tenant A / Org A1 holds Approval P; Org A2 is active; the deciding
    actor holds the global `approval.decide` permission (there is no finer-grained per-org grant
    to withhold) but is NOT operating in Org A1. `approve_and_apply`/`reject` must fail, P must
    remain PENDING, and no apply/reject handler, audit-decision entry, notification, or
    `approvals_changed` signal may fire -- the failure occurs before any of that code runs."""
    _login(services, "admin", "ChangeMe123!")
    org_a1, org_a2 = _create_second_org_in_same_tenant(services)

    requester_username = _unique("xorg-requester")
    services["auth_service"].register_user(requester_username, "StrongPass123", role_names=["planner"])
    _login(services, requester_username, "StrongPass123")
    request = _request_pending_approval_in_org_a1(services, org_a1_id=org_a1.id)

    _login(services, "admin", "ChangeMe123!")
    approver_username = _unique("xorg-approver")
    services["auth_service"].register_user(approver_username, "StrongPass123", role_names=["approver"])

    # Org A2 becomes -- and stays -- the session's active organization for the remainder of this
    # test (`set_active_organization` is the ONLY production path that changes this).
    services["organization_service"].enable_organization(org_a2.id)
    services["tenant_context_service"].set_active_organization(org_a2.id)
    assert _session_active_organization_id(services) == org_a2.id

    _login(services, approver_username, "StrongPass123")
    approvals = services["approval_service"]

    with pytest.raises(NotFoundError, match="Approval request not found"):
        approvals.approve_and_apply(request.id, note="Should not be reachable from Org A2")
    with pytest.raises(NotFoundError, match="Approval request not found"):
        approvals.reject(request.id, note="Should not be reachable from Org A2")

    # Switch back to Org A1 (the same coarse-grained `settings.manage` capability every actor in
    # this test already exercised) to read the request's true, unaffected state.
    _login(services, "admin", "ChangeMe123!")
    services["organization_service"].enable_organization(org_a1.id)
    services["tenant_context_service"].set_active_organization(org_a1.id)
    still_pending = approvals.list_pending()
    matching = [row for row in still_pending if row.id == request.id]
    assert len(matching) == 1
    assert matching[0].status == ApprovalStatus.PENDING
    assert matching[0].decided_by_user_id is None
    assert matching[0].decided_at is None


def _submitted_budget_in_org_a1(services, *, org_a1_id: str):

    assert _session_active_organization_id(services) == org_a1_id
    project = services["project_service"].create_project(
        _unique("XORG-Budget-Project"), financial_currency_code="USD"
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code=_unique("XORG-CC"), name="Cross-org cost code"
    )
    budgets = services["budget_service"]
    budget = budgets.create_budget(project.id, "Cross-org budget")
    budgets.add_line(
        budget.id,
        cost_code_id=cost_code.id,
        description="Line 1",
        amount=1000,
        expected_budget_version=budget.row_version,
    )
    budget = budgets.get_budget(budget.id)
    budget = budgets.submit_budget(budget.id, "admin", expected_version=budget.row_version)
    # `submit_budget` only transitions the budget itself -- the governed `ApprovalRequest` is a
    # separate `request_change(...)` call (mirrors `test_approval_service_unit_of_work_cutover.py
    # ::_request_budget_approval_as_a_different_user`'s exact shape).
    request = services["approval_service"].request_change(
        request_type="budget.approve",
        entity_type="project_budget",
        entity_id=budget.id,
        project_id=budget.project_id,
        payload={"budget_id": budget.id, "expected_version": budget.row_version, "notes": ""},
    )
    assert request.organization_id == org_a1_id
    return request


def test_actor_gains_authority_only_after_switching_active_organization_to_the_target_org(
    services,
):
    """§3 evidence: the SAME actor, holding the SAME global `approval.decide` permission, fails
    against Org A1's request while Org A2 is active, and succeeds against the identical request
    once Org A1 becomes active -- proving decide authority tracks the active organization
    matching the request's own authoritative `organization_id`, never a broader "same tenant" or
    "holds the permission somewhere" notion. This is the evidence for the §3 N/A determination:
    there is no code path granting authority over a non-active organization's request, so a
    complementary "succeeds while A2 remains active" test does not apply."""
    _login(services, "admin", "ChangeMe123!")
    org_a1, org_a2 = _create_second_org_in_same_tenant(services)
    request = _submitted_budget_in_org_a1(services, org_a1_id=org_a1.id)

    approver_username = _unique("xorg2-approver")
    services["auth_service"].register_user(approver_username, "StrongPass123", role_names=["approver"])
    services["organization_service"].enable_organization(org_a2.id)
    services["tenant_context_service"].set_active_organization(org_a2.id)

    _login(services, approver_username, "StrongPass123")
    approvals = services["approval_service"]
    with pytest.raises(NotFoundError, match="Approval request not found"):
        approvals.approve_and_apply(request.id)

    _login(services, "admin", "ChangeMe123!")
    services["organization_service"].enable_organization(org_a1.id)
    services["tenant_context_service"].set_active_organization(org_a1.id)
    _login(services, approver_username, "StrongPass123")

    decided = approvals.approve_and_apply(request.id, note="Approved from the matching org")
    assert decided.status == ApprovalStatus.APPROVED
    assert decided.decided_by_username == approver_username
