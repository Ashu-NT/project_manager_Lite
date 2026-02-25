from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_governance_tab_exposes_mode_switch_controls():
    text = (ROOT / "ui" / "governance" / "tab.py").read_text(
        encoding="utf-8",
        errors="ignore",
    )
    assert "self.mode_combo = QComboBox()" in text
    assert 'self.mode_combo.addItem("Off", userData="off")' in text
    assert 'self.mode_combo.addItem("On (Approval Required)", userData="required")' in text
    assert 'self.status_combo.addItem("Approved", userData=ApprovalStatus.APPROVED)' in text
    assert 'self.status_combo.addItem("Rejected", userData=ApprovalStatus.REJECTED)' in text
    assert "def _on_mode_changed" in text
    assert 'os.environ["PM_GOVERNANCE_MODE"] = mode' in text
    assert "def _entity_display_label" in text
    assert 'f"{request.entity_type}:{request.entity_id}"' not in text
    assert "domain_events.approvals_changed.connect(self._on_approvals_changed)" in text


def test_main_window_exposes_governance_tab_for_request_or_decide_permissions():
    text = (ROOT / "ui" / "main_window.py").read_text(
        encoding="utf-8",
        errors="ignore",
    )
    assert 'if self._has_permission("approval.request") or self._has_permission("approval.decide")' in text
