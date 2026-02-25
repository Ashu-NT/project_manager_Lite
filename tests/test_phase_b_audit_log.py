from __future__ import annotations

from datetime import date


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

