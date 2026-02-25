from __future__ import annotations

from datetime import date

import pytest

from core.exceptions import BusinessRuleError, ValidationError


def _login_admin(services):
    auth = services["auth_service"]
    user_session = services["user_session"]
    admin = auth.authenticate("admin", "ChangeMe123!")
    user_session.set_principal(auth.build_principal(admin))


def test_audit_log_records_project_task_and_cost_changes(services):
    _login_admin(services)
    ps = services["project_service"]
    ts = services["task_service"]
    cs = services["cost_service"]
    audit = services["audit_service"]

    project = ps.create_project("Audit Project")
    task = ts.create_task(
        project_id=project.id,
        name="Audit Task",
        start_date=date(2026, 2, 25),
        duration_days=2,
    )
    cs.add_cost_item(
        project_id=project.id,
        description="Audit Cost",
        planned_amount=100.0,
        task_id=task.id,
    )

    entries = audit.list_recent(limit=20, project_id=project.id)
    actions = {entry.action for entry in entries}
    assert "project.create" in actions
    assert "task.create" in actions
    assert "cost.add" in actions
    assert any(entry.actor_username == "admin" for entry in entries)


def test_audit_service_is_append_only_contract(services):
    audit = services["audit_service"]
    assert not hasattr(audit, "update")
    assert not hasattr(audit, "delete")


def test_governance_request_and_approve_are_audited(services, monkeypatch):
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
    monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "cost.update")
    auth = services["auth_service"]
    user_session = services["user_session"]
    ps = services["project_service"]
    cs = services["cost_service"]
    approvals = services["approval_service"]
    audit = services["audit_service"]

    admin = auth.authenticate("admin", "ChangeMe123!")
    user_session.set_principal(auth.build_principal(admin))
    project = ps.create_project("Governance Audit")
    item = cs.add_cost_item(
        project_id=project.id,
        description="Audit governed cost",
        planned_amount=120.0,
        actual_amount=20.0,
    )
    auth.register_user("planner-audit", "StrongPass123", role_names=["planner"])
    planner = auth.authenticate("planner-audit", "StrongPass123")
    user_session.set_principal(auth.build_principal(planner))
    with pytest.raises(BusinessRuleError, match="Approval required"):
        cs.update_cost_item(item.id, actual_amount=30.0)

    request = approvals.list_pending(project_id=project.id)[0]
    user_session.set_principal(auth.build_principal(admin))
    approvals.approve_and_apply(request.id, note="Approved by admin")

    entries = audit.list_recent(limit=30, project_id=project.id)
    actions = {entry.action for entry in entries}
    assert "governance.request" in actions
    assert "governance.approve" in actions


def test_dependency_audit_details_use_task_names(services):
    _login_admin(services)
    ps = services["project_service"]
    ts = services["task_service"]
    audit = services["audit_service"]

    project = ps.create_project("Dependency Audit Names")
    predecessor = ts.create_task(project.id, "Design", start_date=date(2026, 2, 1), duration_days=1)
    successor = ts.create_task(project.id, "Build", start_date=date(2026, 2, 2), duration_days=1)
    ts.add_dependency(predecessor.id, successor.id)

    entries = audit.list_recent(limit=40, project_id=project.id)
    dep_add = next(e for e in entries if e.action == "dependency.add")
    assert dep_add.details.get("predecessor_name") == "Design"
    assert dep_add.details.get("successor_name") == "Build"


def test_assignment_and_project_resource_audit_use_business_labels(services):
    _login_admin(services)
    ps = services["project_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]
    ts = services["task_service"]
    audit = services["audit_service"]

    project = ps.create_project("Audit Assignment Labels")
    resource = rs.create_resource("Backend Dev", hourly_rate=130.0)
    project_resource = prs.add_to_project(
        project_id=project.id,
        resource_id=resource.id,
        planned_hours=24.0,
    )
    prs.update(
        pr_id=project_resource.id,
        hourly_rate=140.0,
        currency_code="EUR",
        planned_hours=32.0,
        is_active=True,
    )
    task = ts.create_task(
        project_id=project.id,
        name="Implement API",
        start_date=date(2026, 2, 1),
        duration_days=2,
    )
    assignment = ts.assign_project_resource(task.id, project_resource.id, 60.0)
    ts.set_assignment_allocation(assignment.id, 75.0)
    ts.set_assignment_hours(assignment.id, 6.5)
    ts.unassign_resource(assignment.id)
    prs.set_active(project_resource.id, False)
    prs.delete(project_resource.id)

    entries = audit.list_recent(limit=200, project_id=project.id)
    actions = {entry.action for entry in entries}
    assert "project_resource.add" in actions
    assert "project_resource.update" in actions
    assert "project_resource.set_active" in actions
    assert "project_resource.delete" in actions
    assert "assignment.add" in actions
    assert "assignment.set_allocation" in actions
    assert "assignment.log_hours" in actions
    assert "assignment.remove" in actions

    assignment_add = next(e for e in entries if e.action == "assignment.add")
    assert assignment_add.details.get("task_name") == "Implement API"
    assert assignment_add.details.get("resource_name") == "Backend Dev"

    project_resource_add = next(e for e in entries if e.action == "project_resource.add")
    assert project_resource_add.details.get("resource_name") == "Backend Dev"


def test_auth_login_attempts_are_audited(services):
    auth = services["auth_service"]
    audit = services["audit_service"]

    admin = auth.authenticate("admin", "ChangeMe123!")
    assert admin.username == "admin"

    with pytest.raises(ValidationError, match="Invalid credentials"):
        auth.authenticate("admin", "WrongPassword123")

    entries = audit.list_recent(limit=50, entity_type="auth_session")
    actions = [entry.action for entry in entries]
    assert "auth.login.success" in actions
    assert "auth.login.failed" in actions
