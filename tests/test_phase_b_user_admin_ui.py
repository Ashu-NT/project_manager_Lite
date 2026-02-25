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


def test_user_admin_tab_exposes_reset_password_action():
    text = (ROOT / "ui" / "admin" / "users_tab.py").read_text(encoding="utf-8", errors="ignore")
    assert 'self.btn_reset_password = QPushButton("Reset Password")' in text
    assert "def reset_password(self) -> None:" in text
    assert "self._auth_service.reset_user_password(user.id, new_password)" in text


def test_login_dialog_has_show_hide_password_toggle():
    text = (ROOT / "ui" / "auth" / "login_dialog.py").read_text(encoding="utf-8", errors="ignore")
    assert "self.btn_toggle_password = QPushButton(\"Show\")" in text
    assert "def _toggle_password_visibility" in text
