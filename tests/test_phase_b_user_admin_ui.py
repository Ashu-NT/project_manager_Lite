from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QDialog, QLineEdit

from core.platform.common.models import Task, TaskStatus
from tests.ui_runtime_helpers import make_settings_store
from ui.platform.admin.modules.tab import ModuleLicensingTab
from ui.platform.admin.organizations.dialogs import OrganizationEditDialog
from ui.platform.admin.organizations.tab import OrganizationAdminTab
from ui.platform.admin.users.dialogs import PasswordResetDialog, UserEditDialog
from ui.platform.admin.users.tab import UserAdminTab
from ui.platform.control.audit.tab import AuditLogTab
from ui.platform.shared.auth.login_dialog import LoginDialog
from ui.platform.shell.main_window import MainWindow
from ui.modules.project_management.task.task_progress_dialog import TaskProgressDialog


def test_main_window_exposes_admin_tabs_for_auth_manage_runtime(qapp, services, repo_workspace, monkeypatch):
    store = make_settings_store(repo_workspace, prefix="main-window-admin")
    monkeypatch.setattr("ui.platform.shell.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(services)
    labels = [window.tabs.tabText(i) for i in range(window.tabs.count())]

    assert "Projects" in labels
    assert "Register" in labels
    assert "Tasks" in labels
    assert "Collaboration" in labels
    assert "Portfolio" in labels
    assert "Users" in labels
    assert "Employees" in labels
    assert "Organizations" in labels
    assert "Access" in labels
    assert "Audit" in labels
    assert "Support" in labels
    assert "Modules" in labels


def test_user_admin_tab_runtime_enables_edit_and_reset_actions_after_selection(qapp, services):
    tab = UserAdminTab(
        auth_service=services["auth_service"],
        user_session=services["user_session"],
    )

    assert tab.table.rowCount() >= 1
    assert tab.user_scope_badge.text() == "Account Directory"
    assert tab.user_count_badge.text().endswith("users")
    assert tab.user_active_badge.text().endswith("active")
    assert tab.user_access_badge.text() == "Manage Enabled"
    assert tab.btn_new_user.isEnabled() is True
    assert tab.btn_edit_user.isEnabled() is False
    assert tab.btn_reset_password.isEnabled() is False

    tab.table.selectRow(0)
    tab._sync_actions()

    assert tab.btn_edit_user.isEnabled() is True
    assert tab.btn_reset_password.isEnabled() is True
    assert tab.btn_toggle_active.isEnabled() is True


def test_audit_log_tab_runtime_uses_compact_header_and_updates_badges(qapp, services):
    project = services["project_service"].create_project("Audit Header Project")
    tab = AuditLogTab(
        audit_service=services["audit_service"],
        project_service=services["project_service"],
        task_service=services["task_service"],
        resource_service=services["resource_service"],
        cost_service=services["cost_service"],
        baseline_service=services["baseline_service"],
    )

    assert tab.table.rowCount() >= 1
    assert tab.audit_scope_badge.text() == "Append-only"
    assert tab.audit_project_badge.text() == "All"
    assert tab.audit_count_badge.text().endswith("rows")
    assert tab.audit_date_badge.text() == "All Dates"
    assert tab.btn_refresh.isEnabled() is True


def test_audit_log_tab_refreshes_when_module_entitlements_change(qapp, services):
    services["project_service"].create_project("Audit Module Toggle Project")
    tab = AuditLogTab(
        audit_service=services["audit_service"],
        project_service=services["project_service"],
        task_service=services["task_service"],
        resource_service=services["resource_service"],
        cost_service=services["cost_service"],
        baseline_service=services["baseline_service"],
    )
    starting_rows = tab.table.rowCount()

    services["module_catalog_service"].set_module_state("project_management", enabled=False)
    qapp.processEvents()

    assert tab.table.rowCount() >= starting_rows
    assert any(
        tab.table.item(row, 2).text() == "module.entitlement.update"
        for row in range(tab.table.rowCount())
    )


def test_module_licensing_tab_runtime_toggles_project_management_enablement(qapp, services):
    tab = ModuleLicensingTab(
        platform_runtime_application_service=services["platform_runtime_application_service"],
        user_session=services["user_session"],
    )

    assert tab.table.rowCount() == 4
    assert tab.context_badge.text() == "Context: Default Organization"
    assert tab.licensed_badge.text() == "1 licensed"
    assert tab.runtime_badge.text() == "1 runtime"
    assert tab.lifecycle_badge.text() == "0 alerts"

    tab.table.selectRow(0)
    tab._sync_actions()
    assert tab.btn_toggle_license.isEnabled() is True
    assert tab.btn_toggle_enabled.isEnabled() is True
    assert tab.btn_change_status.isEnabled() is True

    tab.toggle_enabled()
    qapp.processEvents()

    assert services["module_catalog_service"].is_enabled("project_management") is False
    assert tab.table.item(0, 4).text() == "No"
    assert tab.table.item(0, 5).text() == "No"

    tab.table.selectRow(0)
    tab.toggle_enabled()
    qapp.processEvents()
    assert services["module_catalog_service"].is_enabled("project_management") is True


def test_module_licensing_tab_runtime_changes_lifecycle_status(qapp, services, monkeypatch):
    tab = ModuleLicensingTab(
        platform_runtime_application_service=services["platform_runtime_application_service"],
        user_session=services["user_session"],
    )
    tab.table.selectRow(0)
    tab._sync_actions()
    monkeypatch.setattr(
        "ui.platform.admin.modules.tab.QInputDialog.getItem",
        lambda *_args, **_kwargs: ("Suspended", True),
    )

    tab.change_status()
    qapp.processEvents()

    assert tab.table.item(0, 2).text() == "Suspended"
    assert tab.table.item(0, 4).text() == "No"
    assert tab.table.item(0, 5).text() == "No"
    assert tab.lifecycle_badge.text() == "1 alerts"


def test_organization_admin_tab_runtime_bootstraps_default_profile(qapp, services):
    tab = OrganizationAdminTab(
        platform_runtime_application_service=services["platform_runtime_application_service"],
        organization_service=services["organization_service"],
        user_session=services["user_session"],
    )

    assert tab.table.rowCount() >= 1
    assert tab.organization_scope_badge.text() == "Install Profile"
    assert tab.organization_count_badge.text().endswith("organizations")
    assert tab.organization_active_badge.text() == "Default Organization"
    assert tab.organization_access_badge.text() == "Manage Enabled"
    assert tab.btn_new_organization.isEnabled() is True
    assert tab.btn_edit_organization.isEnabled() is False
    assert tab.btn_set_active.isEnabled() is False


def test_organization_edit_dialog_defaults_initial_module_selection(qapp, services):
    dialog = OrganizationEditDialog(
        available_modules=services["platform_runtime_application_service"].list_modules(),
    )

    assert dialog.initial_module_codes == ["project_management"]


def test_organization_admin_tab_creates_organization_with_initial_module_mix(qapp, services, monkeypatch):
    class _FakeDialog:
        organization_code = "OPS"
        display_name = "Operations Hub"
        timezone_name = "Africa/Lagos"
        base_currency = "USD"
        is_active = False
        initial_module_codes: list[str] = []

        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            return QDialog.Accepted

    monkeypatch.setattr("ui.platform.admin.organizations.tab.OrganizationEditDialog", _FakeDialog)
    tab = OrganizationAdminTab(
        platform_runtime_application_service=services["platform_runtime_application_service"],
        organization_service=services["organization_service"],
        user_session=services["user_session"],
    )

    tab.create_organization()

    created = next(
        row for row in services["organization_service"].list_organizations() if row.organization_code == "OPS"
    )
    services["organization_service"].set_active_organization(created.id)

    assert services["module_catalog_service"].current_context_label() == "Operations Hub"
    assert services["module_catalog_service"].is_enabled("project_management") is False


def test_login_dialog_runtime_toggles_password_and_signs_in(qapp, anonymous_services):
    auth_service = anonymous_services["auth_service"]
    user_session = anonymous_services["user_session"]
    dialog = LoginDialog(auth_service=auth_service, user_session=user_session)

    assert dialog.password_input.echoMode() == QLineEdit.Password
    dialog.btn_toggle_password.setChecked(True)
    assert dialog.password_input.echoMode() == QLineEdit.Normal
    assert dialog.btn_toggle_password.text() == "Hide"

    dialog.username_input.setText("admin")
    dialog.password_input.setText("ChangeMe123!")
    dialog._try_sign_in()

    assert dialog.result() == QDialog.Accepted
    assert dialog.principal is not None
    assert dialog.principal.username == "admin"


def test_password_reset_dialog_runtime_validates_match_and_accepts(qapp, monkeypatch):
    warnings: list[str] = []
    monkeypatch.setattr(
        "ui.platform.admin.users.dialogs.QMessageBox.warning",
        lambda _parent, _title, message: warnings.append(message),
    )
    dialog = PasswordResetDialog(username="alice")

    dialog.btn_toggle_password.setChecked(True)
    assert dialog.password_input.echoMode() == QLineEdit.Normal
    assert dialog.confirm_password_input.echoMode() == QLineEdit.Normal

    dialog.password_input.setText("StrongPass123")
    dialog.confirm_password_input.setText("Mismatch123")
    dialog._validate_and_accept()
    assert warnings[-1] == "Password and confirm password must match."
    assert dialog.result() != QDialog.Accepted

    dialog.confirm_password_input.setText("StrongPass123")
    dialog._validate_and_accept()
    assert dialog.result() == QDialog.Accepted


def test_user_edit_dialog_runtime_validates_email(qapp, monkeypatch):
    warnings: list[str] = []
    monkeypatch.setattr(
        "ui.platform.admin.users.dialogs.QMessageBox.warning",
        lambda _parent, _title, message: warnings.append(message),
    )
    dialog = UserEditDialog(username="alice", display_name="Alice", email="alice@example.com")

    dialog.email_input.setText("not-an-email")
    dialog._validate_and_accept()
    assert warnings[-1] == "Invalid email format."
    assert dialog.result() != QDialog.Accepted

    dialog.email_input.setText("updated@example.com")
    dialog._validate_and_accept()
    assert dialog.result() == QDialog.Accepted


def test_task_progress_dialog_runtime_supports_status_checkbox_update(qapp, monkeypatch):
    task = Task.create(
        project_id="project-1",
        name="Progress Task",
        start_date=date(2026, 3, 1),
        duration_days=2,
        status=TaskStatus.TODO,
    )
    dialog = TaskProgressDialog(task=task)
    monkeypatch.setattr(dialog, "_prompt_iso_date", lambda *_args, **_kwargs: date(2026, 3, 2))

    dialog.status_check.setChecked(True)
    dialog.status_combo.setCurrentIndex(dialog.status_combo.findData(TaskStatus.IN_PROGRESS))
    payload = dialog.build_payload()

    assert dialog.status_set is True
    assert payload is not None
    assert payload["status"] == TaskStatus.IN_PROGRESS
    assert payload["actual_start"] == date(2026, 3, 2)
