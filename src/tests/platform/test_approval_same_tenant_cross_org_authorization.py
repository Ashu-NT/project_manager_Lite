"""Same-tenant, cross-organization Approval authorization.

`ApprovalService.approve_and_apply`/`reject` require only the GLOBAL permission
`approval.decide` -- there is no per-organization "decide" grant. The organization boundary is
enforced entirely by the repository's ambient tenant-scoping filter, which requires the SESSION's
active organization (`TenantContextService`, not `OrganizationService.get_active_organization()`'s
separate "business-active org" flag) to match the request's own `organization_id`. Switching the
active organization itself requires only the global `settings.manage` permission, not per-org
membership.

So an actor holding `approval.decide`, with Org A2 active, cannot decide an Approval belonging to
Org A1 -- the request is structurally invisible via the repository, not merely permission-denied.
There is no code path granting decide authority over a non-active organization's request, so
`test_actor_gains_authority_only_after_switching_active_organization_to_the_target_org` covers the
complementary case directly: decide fails before switching to A1, succeeds after.

Cross-tenant isolation is covered separately in
`test_platform_unit_of_work.py::test_cross_tenant_context_cannot_read_another_tenants_approval_request`.
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
    """The session-scoped active organization used for Approval scoping -- distinct from
    `OrganizationService.get_active_organization()`'s separate "business-active org" DB flag."""
    return services["tenant_context_service"].get_active_organization_id()


def _create_second_org_in_same_tenant(services):
    """Org A2, created disabled so it never touches the DB "business-active org" flag -- the
    session's real active organization (Org A1) must stay untouched by mere creation."""
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
    time, never re-derived afterward."""
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
    """Tenant A / Org A1 holds Approval P; Org A2 is active; the deciding actor holds the global
    `approval.decide` permission but is NOT operating in Org A1. `approve_and_apply`/`reject`
    must fail and P must remain PENDING and undecided."""
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
    # With multiple organizations enabled, a fresh login's active-org auto-select is ambiguous --
    # pin it to A2 explicitly.
    services["user_session"].set_active_organization_id(org_a2.id)
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
    """The same actor, holding the same global `approval.decide` permission, fails against Org
    A1's request while Org A2 is active, then succeeds against the identical request once Org A1
    becomes active -- decide authority tracks the active organization, not "same tenant" or
    "holds the permission somewhere"."""
    _login(services, "admin", "ChangeMe123!")
    org_a1, org_a2 = _create_second_org_in_same_tenant(services)
    request = _submitted_budget_in_org_a1(services, org_a1_id=org_a1.id)

    approver_username = _unique("xorg2-approver")
    services["auth_service"].register_user(approver_username, "StrongPass123", role_names=["approver"])
    services["organization_service"].enable_organization(org_a2.id)
    services["tenant_context_service"].set_active_organization(org_a2.id)

    _login(services, approver_username, "StrongPass123")
    # Pin the fresh login's ambiguous auto-select the same way as the sibling test above.
    services["user_session"].set_active_organization_id(org_a2.id)
    approvals = services["approval_service"]
    with pytest.raises(NotFoundError, match="Approval request not found"):
        approvals.approve_and_apply(request.id)

    _login(services, "admin", "ChangeMe123!")
    services["organization_service"].enable_organization(org_a1.id)
    services["tenant_context_service"].set_active_organization(org_a1.id)
    _login(services, approver_username, "StrongPass123")
    services["user_session"].set_active_organization_id(org_a1.id)

    decided = approvals.approve_and_apply(request.id, note="Approved from the matching org")
    assert decided.status == ApprovalStatus.APPROVED
    assert decided.decided_by_username == approver_username
