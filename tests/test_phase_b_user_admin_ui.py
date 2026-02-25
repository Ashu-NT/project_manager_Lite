from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_main_window_exposes_users_tab_for_auth_manage():
    text = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8", errors="ignore")
    assert "from ui.admin.users_tab import UserAdminTab" in text
    assert 'self.tabs.addTab(users_tab, "Users")' in text


def test_login_dialog_has_show_hide_password_toggle():
    text = (ROOT / "ui" / "auth" / "login_dialog.py").read_text(encoding="utf-8", errors="ignore")
    assert "self.btn_toggle_password = QPushButton(\"Show\")" in text
    assert "def _toggle_password_visibility" in text
