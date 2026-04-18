from __future__ import annotations

from datetime import date

from tests.ui_runtime_helpers import make_settings_store, register_and_login
from src.ui.shell.main_window import MainWindow
from ui.modules.project_management.project.tab import ProjectTab
from ui.modules.project_management.resource.tab import ResourceTab
from src.ui.shared.widgets import guards as guards_mod
from src.ui.shared.widgets.guards import can_execute_governed_action, has_permission
from ui.modules.project_management.task.tab import TaskTab


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

    assert has_permission(None, "cost.manage") is False
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
    assert (
        can_execute_governed_action(
            user_session=None,
            manage_permission="cost.manage",
            governance_action="cost.update",
        )
        is False
    )


def test_main_window_runtime_hides_admin_tabs_for_viewer(qapp, services, repo_workspace, monkeypatch):
    register_and_login(services, username_prefix="viewer-main-window", role_names=("viewer",))
    store = make_settings_store(repo_workspace, prefix="main-window-viewer")
    monkeypatch.setattr("src.ui.shell.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(services)
    labels = [window.tabs.tabText(i) for i in range(window.tabs.count())]

    assert "Projects" in labels
    assert "Tasks" in labels
    assert "Collaboration" in labels
    assert "Costs" in labels
    assert "Portfolio" not in labels
    assert "Users" not in labels
    assert "Access" not in labels
    assert "Audit" not in labels
    assert "Support" not in labels


def test_main_window_runtime_hides_business_tabs_for_anonymous_session(
    qapp,
    anonymous_services,
    repo_workspace,
    monkeypatch,
):
    store = make_settings_store(repo_workspace, prefix="main-window-anonymous")
    monkeypatch.setattr("src.ui.shell.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(anonymous_services)

    assert window.tabs.count() == 0


def test_tabs_apply_permission_hints_and_disable_manage_actions_for_viewer(qapp, services, repo_workspace):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]

    project = ps.create_project("Viewer Project")
    task = ts.create_task(project.id, "Viewer Task", start_date=date(2026, 4, 1), duration_days=2)
    rs.create_resource("Viewer Resource", hourly_rate=100.0)
    register_and_login(services, username_prefix="viewer-tabs", role_names=("viewer",))

    resource_tab = ResourceTab(
        resource_service=rs,
        user_session=services["user_session"],
    )
    project_tab = ProjectTab(
        project_service=ps,
        task_service=ts,
        reporting_service=services["reporting_service"],
        project_resource_service=prs,
        resource_service=rs,
        data_import_service=services["data_import_service"],
        user_session=services["user_session"],
    )
    task_tab = TaskTab(
        project_service=ps,
        task_service=ts,
        resource_service=rs,
        project_resource_service=prs,
        collaboration_store=services["task_collaboration_store"],
        settings_store=make_settings_store(repo_workspace, prefix="task-viewer"),
        user_session=services["user_session"],
    )

    project_tab.table.selectRow(0)
    project_tab._sync_actions()
    task_tab._select_task_by_id(task.id)
    task_tab._set_assignment_panel_actions_state(
        task_selected=True,
        assignment_selected=False,
        dependency_selected=False,
    )

    assert resource_tab.btn_new.isEnabled() is False
    assert "resource.manage" in resource_tab.btn_new.toolTip()
    assert project_tab.btn_new.isEnabled() is False
    assert project_tab.btn_import_csv.isEnabled() is False
    assert "project.manage" in project_tab.btn_import_csv.toolTip()
    assert project_tab._btn_project_resource_add.isEnabled() is False
    assert task_tab.btn_new.isEnabled() is False
    assert task_tab.btn_assignment_add.isEnabled() is False
    assert task_tab.btn_assignment_log_hours.isEnabled() is False
    task_tab._mentions_refresh_timer.stop()


def test_guarded_errors_include_incident_context_and_business_event_mappings():
    assert guards_mod._CALLBACK_ERROR_EVENT_MAP["create_task"] == "business.task.add.error"
    assert guards_mod._CALLBACK_ERROR_EVENT_MAP["edit_task"] == "business.task.update.error"
    assert (
        guards_mod._CALLBACK_ERROR_EVENT_MAP["recalc_project_schedule"]
        == "business.schedule.recalculate.error"
    )
    assert guards_mod._CALLBACK_ERROR_EVENT_MAP["_generate_baseline"] == "business.baseline.create.error"
    assert callable(guards_mod.message_with_incident)
    assert callable(guards_mod.emit_error_event)
