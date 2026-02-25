from __future__ import annotations

from datetime import date

import pytest

from core.exceptions import BusinessRuleError


def _login(services, username: str, password: str):
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


def test_cost_update_requester_can_lack_cost_manage_and_admin_can_approve(services, monkeypatch):
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
    monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "cost.update")
    _login(services, "admin", "ChangeMe123!")

    auth = services["auth_service"]
    ps = services["project_service"]
    cs = services["cost_service"]
    approvals = services["approval_service"]

    project = ps.create_project("Governed Cost Project")
    item = cs.add_cost_item(project.id, "Travel", planned_amount=1000.0, actual_amount=100.0)
    auth.register_user("planner-req", "StrongPass123", role_names=["planner"])
    _login(services, "planner-req", "StrongPass123")

    with pytest.raises(BusinessRuleError, match="Approval required"):
        cs.update_cost_item(item.id, actual_amount=300.0)

    pending = approvals.list_pending(project_id=project.id)
    assert len(pending) == 1
    req = pending[0]
    assert req.request_type == "cost.update"
    assert req.requested_by_username == "planner-req"

    _login(services, "admin", "ChangeMe123!")
    approvals.approve_and_apply(req.id, note="Approved")

    updated = cs.list_cost_items_for_project(project.id)[0]
    assert updated.actual_amount == 300.0


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


def test_admin_bypasses_governance_requests_for_governed_actions(services, monkeypatch):
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
    monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "cost.update")
    _login(services, "admin", "ChangeMe123!")

    ps = services["project_service"]
    cs = services["cost_service"]
    approvals = services["approval_service"]

    project = ps.create_project("Admin bypass")
    item = cs.add_cost_item(project.id, "Travel", planned_amount=1000.0, actual_amount=100.0)
    updated = cs.update_cost_item(item.id, actual_amount=250.0)

    assert updated.actual_amount == 250.0
    assert approvals.list_pending(project_id=project.id) == []


def test_same_user_cannot_approve_own_request(services, monkeypatch):
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "off")
    _login(services, "admin", "ChangeMe123!")

    approvals = services["approval_service"]
    request = approvals.request_change(
        request_type="cost.update",
        entity_type="cost_item",
        entity_id="c-1",
        project_id="p-1",
        payload={"cost_id": "c-1"},
    )
    with pytest.raises(BusinessRuleError, match="cannot approve or reject your own"):
        approvals.approve_and_apply(request.id)


def test_list_requests_accepts_string_status_value_from_ui(services, monkeypatch):
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "off")
    _login(services, "admin", "ChangeMe123!")
    approvals = services["approval_service"]
    req = approvals.request_change(
        request_type="cost.update",
        entity_type="cost_item",
        entity_id="c-2",
        project_id="p-2",
        payload={"cost_id": "c-2"},
    )
    pending = approvals.list_requests(status="PENDING", project_id="p-2")
    assert any(item.id == req.id for item in pending)
