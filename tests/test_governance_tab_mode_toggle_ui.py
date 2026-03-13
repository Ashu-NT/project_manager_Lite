from __future__ import annotations

import os

from core.platform.common.models import ApprovalStatus
from tests.ui_runtime_helpers import make_settings_store, register_and_login
from ui.modules.project_management.governance.tab import GovernanceTab
from ui.platform.shell.main_window import MainWindow


def test_governance_tab_runtime_exposes_mode_switch_and_persists_changes(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    project = services["project_service"].create_project("Governance Project")
    request = services["approval_service"].request_change(
        request_type="baseline.create",
        entity_type="baseline",
        entity_id="baseline-1",
        project_id=project.id,
        payload={"name": "March Baseline"},
    )

    store = make_settings_store(repo_workspace, prefix="governance")
    info_messages: list[str] = []
    monkeypatch.setattr("ui.modules.project_management.governance.tab.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(
        "ui.modules.project_management.governance.tab.QMessageBox.information",
        lambda _parent, _title, message: info_messages.append(message),
    )
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "off")

    tab = GovernanceTab(
        approval_service=services["approval_service"],
        project_service=services["project_service"],
        task_service=services["task_service"],
        cost_service=services["cost_service"],
        user_session=services["user_session"],
    )

    assert [tab.mode_combo.itemData(i) for i in range(tab.mode_combo.count())] == ["off", "required"]
    assert tab.status_combo.findData(ApprovalStatus.APPROVED) >= 0
    assert tab.status_combo.findData(ApprovalStatus.REJECTED) >= 0
    assert tab.table.rowCount() == 1
    assert tab.governance_mode_badge.text() == "Off"
    assert tab.governance_status_badge.text() == "Pending"
    assert tab.governance_count_badge.text() == "1 requests"
    assert tab.governance_access_badge.text() == "Decision Enabled"

    label = tab._entity_display_label(
        request=request,
        project_name_by_id={project.id: project.name},
        task_name_by_id={},
        cost_desc_by_id={},
    )
    assert "March Baseline" in label
    assert project.name in label

    tab.mode_combo.setCurrentIndex(tab.mode_combo.findData("required"))

    assert os.environ["PM_GOVERNANCE_MODE"] == "required"
    assert store.load_governance_mode(default_mode="off") == "required"
    assert tab.governance_mode_badge.text() == "On"
    assert any("Governance mode is now ON" in message for message in info_messages)


def test_main_window_runtime_exposes_governance_tab_for_request_permissions(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    register_and_login(services, username_prefix="planner-governance", role_names=("planner",))
    store = make_settings_store(repo_workspace, prefix="governance-main-window")
    monkeypatch.setattr("ui.platform.shell.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(services)
    labels = [window.tabs.tabText(i) for i in range(window.tabs.count())]

    assert "Governance" in labels
    assert "Users" not in labels
    assert "Audit" not in labels
