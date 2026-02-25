from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_main_window_exposes_users_tab_for_auth_manage():
    text = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8", errors="ignore")
    assert "from ui.admin.users_tab import UserAdminTab" in text
    assert 'self.tabs.addTab(users_tab, "Users")' in text


def test_main_window_exposes_audit_tab_for_auth_manage():
    text = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8", errors="ignore")
    assert "from ui.admin.audit_tab import AuditLogTab" in text
    assert 'self.tabs.addTab(audit_tab, "Audit")' in text


def test_audit_tab_resolves_reference_ids_to_display_names():
    text = (ROOT / "ui" / "admin" / "audit_tab.py").read_text(encoding="utf-8", errors="ignore")
    assert "def _resolve_detail_value" in text
    assert "self._task_name_by_id.get(raw, raw)" in text
    assert "self._resource_name_by_id.get(raw, raw)" in text
    assert "self._cost_label_by_id.get(raw, raw)" in text


def test_audit_tab_supports_date_and_date_range_filters():
    text = (ROOT / "ui" / "admin" / "audit_tab.py").read_text(encoding="utf-8", errors="ignore")
    assert "self.date_mode_filter = QComboBox()" in text
    assert 'self.date_mode_filter.addItem("All Dates", userData="all")' in text
    assert 'self.date_mode_filter.addItem("On Date", userData="on")' in text
    assert 'self.date_mode_filter.addItem("Date Range", userData="range")' in text
    assert "self.date_from_filter = QDateEdit()" in text
    assert "self.date_to_filter = QDateEdit()" in text
    assert "def _date_matches" in text


def test_user_admin_tab_exposes_reset_password_action():
    text = (ROOT / "ui" / "admin" / "users_tab.py").read_text(encoding="utf-8", errors="ignore")
    assert 'self.btn_reset_password = QPushButton("Reset Password")' in text
    assert "def reset_password(self) -> None:" in text
    assert "PasswordResetDialog(username=user.username, parent=self)" in text
    assert "self._auth_service.reset_user_password(user.id, new_password)" in text


def test_user_admin_tab_exposes_edit_user_action():
    tab_text = (ROOT / "ui" / "admin" / "users_tab.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    dialog_text = (ROOT / "ui" / "admin" / "user_dialog.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert 'self.btn_edit_user = QPushButton("Edit User")' in tab_text
    assert "def edit_user(self) -> None:" in tab_text
    assert "UserEditDialog(" in tab_text
    assert "self._auth_service.update_user_profile(" in tab_text
    assert "class UserEditDialog(QDialog):" in dialog_text


def test_project_tab_exposes_update_status_action():
    tab_text = (ROOT / "ui" / "project" / "tab.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    actions_text = (ROOT / "ui" / "project" / "actions.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "self.btn_update_status = QPushButton(CFG.UPDATE_PROJECT_STATUS_LABEL)" in tab_text
    assert "callback=self.update_project_status" in tab_text
    assert "def update_project_status(self) -> None:" in actions_text
    assert "self._project_service.set_status(proj.id, selected_status)" in actions_text


def test_login_dialog_has_show_hide_password_toggle():
    text = (ROOT / "ui" / "auth" / "login_dialog.py").read_text(encoding="utf-8", errors="ignore")
    assert "self.btn_toggle_password = QPushButton(\"Show\")" in text
    assert "def _toggle_password_visibility" in text


def test_password_reset_dialog_has_strength_toggle_and_confirm_logic():
    text = (ROOT / "ui" / "admin" / "user_dialog.py").read_text(encoding="utf-8", errors="ignore")
    assert "class PasswordResetDialog(QDialog):" in text
    assert "self.btn_toggle_password = QPushButton(\"Show\")" in text
    assert "self.password_input.textChanged.connect(self._update_password_strength)" in text
    assert "Password and confirm password must match." in text


def test_task_progress_dialog_supports_status_checkbox_update():
    text = (ROOT / "ui" / "task" / "task_progress_dialog.py").read_text(
        encoding="utf-8",
        errors="ignore",
    )
    assert "self.status_check = QCheckBox()" in text
    assert "self.status_combo = QComboBox()" in text
    assert "form.addRow(\"Status:\", self._with_checkbox(self.status_combo, self.status_check))" in text
    assert "def status_set(self) -> bool:" in text
    assert "def status(self) -> TaskStatus | None:" in text
