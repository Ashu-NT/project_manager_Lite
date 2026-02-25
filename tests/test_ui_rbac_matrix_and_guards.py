from __future__ import annotations

from pathlib import Path

from ui.shared.guards import can_execute_governed_action, has_permission


ROOT = Path(__file__).resolve().parents[1]


class _FakeSession:
    def __init__(self, permissions: set[str]):
        self._permissions = permissions

    def has_permission(self, permission_code: str) -> bool:
        return permission_code in self._permissions


def test_guard_permission_helpers_resolve_manage_vs_governed_modes(monkeypatch):
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
    monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "cost.update")

    admin_like = _FakeSession({"cost.manage"})
    requester = _FakeSession({"approval.request"})
    viewer = _FakeSession(set())

    assert has_permission(None, "cost.manage") is True
    assert has_permission(admin_like, "cost.manage") is True
    assert has_permission(viewer, "cost.manage") is False

    assert (
        can_execute_governed_action(
            user_session=admin_like,
            manage_permission="cost.manage",
            governance_action="cost.update",
        )
        is True
    )
    assert (
        can_execute_governed_action(
            user_session=requester,
            manage_permission="cost.manage",
            governance_action="cost.update",
        )
        is True
    )
    assert (
        can_execute_governed_action(
            user_session=requester,
            manage_permission="cost.manage",
            governance_action="cost.delete",
        )
        is False
    )
    assert (
        can_execute_governed_action(
            user_session=viewer,
            manage_permission="cost.manage",
            governance_action="cost.update",
        )
        is False
    )


def test_main_window_passes_user_session_to_action_tabs():
    text = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8", errors="ignore")
    assert "dashboard_tab = DashboardTab(" in text
    assert "calendar_tab = CalendarTab(" in text
    assert "resource_tab = ResourceTab(" in text
    assert "project_tab = ProjectTab(" in text
    assert "task_tab = TaskTab(" in text
    assert "cost_tab = CostTab(" in text
    assert "user_session=self._user_session" in text


def test_tabs_apply_rbac_hints_and_guarded_slots():
    root = ROOT / "ui"
    task_text = (root / "task" / "tab.py").read_text(encoding="utf-8", errors="ignore")
    project_text = (root / "project" / "tab.py").read_text(encoding="utf-8", errors="ignore")
    resource_text = (root / "resource" / "tab.py").read_text(encoding="utf-8", errors="ignore")
    cost_text = (root / "cost" / "tab.py").read_text(encoding="utf-8", errors="ignore")
    calendar_text = (root / "calendar" / "tab.py").read_text(encoding="utf-8", errors="ignore")
    users_text = (root / "admin" / "users_tab.py").read_text(encoding="utf-8", errors="ignore")
    dashboard_text = (root / "dashboard" / "tab.py").read_text(encoding="utf-8", errors="ignore")
    dashboard_access_text = (root / "dashboard" / "access.py").read_text(
        encoding="utf-8",
        errors="ignore",
    )
    governance_text = (root / "governance" / "tab.py").read_text(encoding="utf-8", errors="ignore")

    assert "can_execute_governed_action(" in task_text
    assert "apply_permission_hint(" in task_text
    assert "make_guarded_slot(" in task_text
    assert "apply_permission_hint(" in project_text
    assert "make_guarded_slot(" in project_text
    assert "apply_permission_hint(" in resource_text
    assert "make_guarded_slot(" in resource_text
    assert "can_execute_governed_action(" in cost_text
    assert "apply_permission_hint(" in cost_text
    assert "apply_permission_hint(" in calendar_text
    assert "make_guarded_slot(" in calendar_text
    assert "apply_permission_hint(" in users_text
    assert "make_guarded_slot(" in users_text
    assert "can_execute_governed_action(" in dashboard_access_text
    assert "apply_permission_hint(" in dashboard_access_text
    assert "wire_dashboard_access(" in dashboard_text
    assert "make_guarded_slot(" in governance_text


def test_assignment_and_project_resource_panels_respect_manage_permissions():
    task_panel_text = (ROOT / "ui" / "task" / "assignment_panel.py").read_text(
        encoding="utf-8",
        errors="ignore",
    )
    project_panel_text = (ROOT / "ui" / "project" / "resource_panel.py").read_text(
        encoding="utf-8",
        errors="ignore",
    )

    assert "can_manage_assignments" in task_panel_text
    assert "can_add_dependencies" in task_panel_text
    assert "can_remove_dependencies" in task_panel_text
    assert "can_manage = bool(getattr(self, \"_can_manage_project_resources\", True))" in project_panel_text
