from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QDialog, QLineEdit

from core.models import Task, TaskStatus
from tests.ui_runtime_helpers import make_settings_store
from ui.admin.audit_tab import AuditLogTab
from ui.admin.user_dialog import PasswordResetDialog, UserEditDialog
from ui.admin.users_tab import UserAdminTab
from ui.auth.login_dialog import LoginDialog
from ui.main_window import MainWindow
from ui.task.task_progress_dialog import TaskProgressDialog


def test_main_window_exposes_admin_tabs_for_auth_manage_runtime(qapp, services, repo_workspace, monkeypatch):
    store = make_settings_store(repo_workspace, prefix="main-window-admin")
    monkeypatch.setattr("ui.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(services)
    labels = [window.tabs.tabText(i) for i in range(window.tabs.count())]

    assert "Projects" in labels
    assert "Register" in labels
    assert "Tasks" in labels
    assert "Users" in labels
    assert "Audit" in labels
    assert "Support" in labels


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
        "ui.admin.user_dialog.QMessageBox.warning",
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
        "ui.admin.user_dialog.QMessageBox.warning",
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
