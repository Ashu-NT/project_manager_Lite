from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.shared.events.domain_events import domain_events


def _login(services, username: str, password: str):
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


def _submitted_cost_entry(services, name: str):
    organization = services["organization_service"].get_active_organization()
    project = services["project_service"].create_project(name)
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="MANUAL-ACTUAL",
        name="Manual actual",
    )
    service = services["cost_entry_service"]
    entry = service.create_manual_entry(
        project_id=project.id,
        command_id=f"{name}-command",
        description="Travel",
        amount=Decimal("100"),
        currency_code=organization.base_currency,
        transaction_date=date(2026, 1, 10),
        cost_code_id=cost_code.id,
    )
    entry = service.submit(entry.id, expected_version=entry.row_version)
    return project, entry


def test_cost_entry_requester_can_lack_approve_and_admin_can_approve(services, monkeypatch):
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
    monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "project_cost.approve")
    _login(services, "admin", "ChangeMe123!")

    auth = services["auth_service"]
    cost_entries = services["cost_entry_service"]
    approvals = services["approval_service"]

    project, item = _submitted_cost_entry(services, "Governed Cost Project")
    auth.register_user("planner-req", "StrongPass123", role_names=["planner"])
    _login(services, "planner-req", "StrongPass123")

    result = cost_entries.approve(item.id, expected_version=item.row_version)
    assert result.outcome.value == "pending_approval"

    pending = approvals.list_pending(project_id=project.id)
    assert len(pending) == 1
    req = pending[0]
    assert req.request_type == "project_cost.approve"
    assert req.requested_by_username == "planner-req"
    assert req.payload["entry_id"] == item.id

    _login(services, "admin", "ChangeMe123!")
    approvals.approve_and_apply(req.id, note="Approved")

    updated = cost_entries.get_entry(item.id)
    assert updated.status.value == "approved"


def test_dependency_add_requires_and_applies_approval(services, monkeypatch):
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
    monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "dependency.add")
    _login(services, "admin", "ChangeMe123!")

    auth = services["auth_service"]
    ps = services["project_service"]
    ts = services["task_service"]
    approvals = services["approval_service"]

    project = ps.create_project("Governed Dependency Project")
    a = ts.create_task(project.id, "Task Alpha", start_date=date(2026, 2, 24), duration_days=1)
    b = ts.create_task(project.id, "Task Beta", start_date=date(2026, 2, 25), duration_days=1)
    auth.register_user("planner-dep", "StrongPass123", role_names=["planner"])
    _login(services, "planner-dep", "StrongPass123")

    with pytest.raises(BusinessRuleError, match="Approval required"):
        ts.add_dependency(a.id, b.id)

    req = approvals.list_pending(project_id=project.id)[0]
    assert req.request_type == "dependency.add"
    assert req.requested_by_username == "planner-dep"
    _login(services, "admin", "ChangeMe123!")
    approvals.approve_and_apply(req.id)

    deps = ts.list_dependencies_for_task(b.id)
    assert len(deps) == 1
    assert deps[0].predecessor_task_id == a.id


def test_admin_does_not_bypass_governance_requests_for_governed_actions(services, monkeypatch):
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
    monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "project_cost.approve")
    _login(services, "admin", "ChangeMe123!")

    cost_entries = services["cost_entry_service"]
    approvals = services["approval_service"]

    project, item = _submitted_cost_entry(services, "Admin bypass")
    result = cost_entries.approve(item.id, expected_version=item.row_version)
    assert result.outcome.value == "pending_approval"

    unchanged = cost_entries.get_entry(item.id)
    assert unchanged.status.value == "submitted"
    assert len(approvals.list_pending(project_id=project.id)) == 1


def test_approval_apply_rolls_back_handler_when_decision_update_fails(
    services,
    monkeypatch,
):
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
    monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "project_cost.approve")
    _login(services, "admin", "ChangeMe123!")

    auth = services["auth_service"]
    project, item = _submitted_cost_entry(services, "Atomic approval")
    auth.register_user("atomic-requester", "StrongPass123", role_names=["planner"])
    _login(services, "atomic-requester", "StrongPass123")
    result = services["cost_entry_service"].approve(
        item.id, expected_version=item.row_version
    )
    assert result.outcome.value == "pending_approval"
    request = services["approval_service"].list_pending(project_id=project.id)[0]

    approvals = services["approval_service"]
    approval_repo_class = type(approvals._approval_repo)
    original_update = approval_repo_class.update

    # P4 Step 2 (ADR-005 Section 24, Round 7/8): approve_and_apply's actual decision-update now
    # runs against a fresh PlatformUnitOfWork's own `uow.approvals` -- an independently
    # constructed ApprovalRepository instance, distinct from `approvals._approval_repo` (kept on
    # ApprovalService only for read paths and the caller-owned-transaction request_change mode).
    # An instance-level monkeypatch on `approvals._approval_repo` would no longer reach the fresh
    # instance, so this patches the class method instead -- every instance shares it, preserving
    # this test's actual intent (proving decision-update failure rolls back atomically) without
    # depending on instance identity.
    def _fail_decision_update(self, candidate):
        if candidate.id == request.id:
            raise RuntimeError("simulated decision persistence failure")
        return original_update(self, candidate)

    monkeypatch.setattr(approval_repo_class, "update", _fail_decision_update)
    _login(services, "admin", "ChangeMe123!")

    emitted_cost_changes: list[str] = []

    def _on_costs_changed(project_id: str) -> None:
        emitted_cost_changes.append(project_id)

    domain_events.cost_entries_changed.connect(_on_costs_changed)
    try:
        with pytest.raises(RuntimeError, match="simulated decision persistence failure"):
            approvals.approve_and_apply(request.id, note="Should roll back")
    finally:
        domain_events.cost_entries_changed.disconnect(_on_costs_changed)

    services["cost_entry_service"]._session.expire_all()
    unchanged = services["cost_entry_service"].get_entry(item.id)
    assert unchanged.status.value == "submitted"
    assert emitted_cost_changes == []


def test_approval_apply_rolls_back_handler_when_required_audit_fails(
    services,
    monkeypatch,
):
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
    monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "project_cost.approve")
    _login(services, "admin", "ChangeMe123!")

    auth = services["auth_service"]
    project, item = _submitted_cost_entry(services, "Atomic approval audit")
    auth.register_user("audit-requester", "StrongPass123", role_names=["planner"])
    _login(services, "audit-requester", "StrongPass123")
    result = services["cost_entry_service"].approve(
        item.id, expected_version=item.row_version
    )
    assert result.outcome.value == "pending_approval"
    request = services["approval_service"].list_pending(project_id=project.id)[0]

    approvals = services["approval_service"]
    audit_service_class = type(approvals._enterprise_audit_service)
    original_record = audit_service_class.record

    # P4 Step 2 (ADR-005 Section 24, Round 7/8): approve_and_apply's same-transaction audit write
    # now runs against a fresh PlatformUnitOfWork's own `uow._enterprise_audit_service` --
    # distinct from `approvals._enterprise_audit_service` (kept on ApprovalService only for the
    # caller-owned-transaction request_change mode). Patch the class method so the fresh instance
    # is affected too.
    def _fail_approval_audit(self, **kwargs):
        if kwargs.get("entity_type") == "approval_request" and (
            kwargs.get("metadata") or {}
        ).get("action") == "governance.approve":
            raise RuntimeError("simulated audit failure")
        return original_record(self, **kwargs)

    monkeypatch.setattr(audit_service_class, "record", _fail_approval_audit)
    _login(services, "admin", "ChangeMe123!")

    with pytest.raises(RuntimeError, match="simulated audit failure"):
        approvals.approve_and_apply(request.id, note="Should roll back")

    services["cost_entry_service"]._session.expire_all()
    unchanged = services["cost_entry_service"].get_entry(item.id)
    assert unchanged.status.value == "submitted"


def test_same_user_cannot_approve_own_request(services, monkeypatch):
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "off")
    _login(services, "admin", "ChangeMe123!")

    approvals = services["approval_service"]
    request = approvals.request_change(
        request_type="project_cost.approve",
        entity_type="project_cost_entry",
        entity_id="entry-1",
        project_id="p-1",
        payload={"entry_id": "entry-1"},
    )
    with pytest.raises(BusinessRuleError, match="cannot approve or reject your own"):
        approvals.approve_and_apply(request.id)


def test_list_requests_accepts_string_status_value_from_ui(services, monkeypatch):
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "off")
    _login(services, "admin", "ChangeMe123!")
    approvals = services["approval_service"]
    req = approvals.request_change(
        request_type="project_cost.approve",
        entity_type="project_cost_entry",
        entity_id="entry-2",
        project_id="p-2",
        payload={"entry_id": "entry-2"},
    )
    pending = approvals.list_requests(status="PENDING", project_id="p-2")
    assert any(item.id == req.id for item in pending)


def test_duplicate_approval_requests_are_prevented(services, monkeypatch):
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "off")
    _login(services, "admin", "ChangeMe123!")
    approvals = services["approval_service"]
    req1 = approvals.request_change(
        request_type="baseline.create",
        entity_type="project_baseline",
        entity_id="p-1",
        project_id="p-1",
        payload={"project_id": "p-1", "name": "Baseline 1"},
    )
    with pytest.raises(BusinessRuleError, match="pending approval already exists"):
        approvals.request_change(
            request_type="baseline.create",
            entity_type="project_baseline",
            entity_id="p-1",
            project_id="p-1",
            payload={"project_id": "p-1", "name": "Baseline 2"},
        )

