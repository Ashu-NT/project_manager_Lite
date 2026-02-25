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
    assert "def _on_mode_changed" in text
    assert 'os.environ["PM_GOVERNANCE_MODE"] = mode' in text
