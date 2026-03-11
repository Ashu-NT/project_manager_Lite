from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QDialog

from core.domain.register import RegisterEntrySeverity, RegisterEntryStatus, RegisterEntryType
from core.events.domain_events import domain_events
from tests.ui_runtime_helpers import make_settings_store
from ui.main_window import MainWindow
from ui.project.import_wizard import ImportWizardDialog
from ui.register.tab import RegisterTab


def test_register_service_tracks_summary_audit_and_domain_event(services):
    project = services["project_service"].create_project("Register Summary Project")
    register_service = services["register_service"]
    audit_service = services["audit_service"]
    captured: list[str] = []

    def _on_changed(project_id: str) -> None:
        captured.append(project_id)

    domain_events.register_changed.connect(_on_changed)
    try:
        risk = register_service.create_entry(
            project.id,
            entry_type=RegisterEntryType.RISK,
            title="Vendor delivery risk",
            severity=RegisterEntrySeverity.CRITICAL,
            owner_name="PM Lead",
            due_date=date(2026, 3, 8),
        )
        issue = register_service.create_entry(
            project.id,
            entry_type=RegisterEntryType.ISSUE,
            title="Blocked environment",
            severity=RegisterEntrySeverity.HIGH,
            status=RegisterEntryStatus.IN_PROGRESS,
            owner_name="DevOps",
        )
        change = register_service.create_entry(
            project.id,
            entry_type=RegisterEntryType.CHANGE,
            title="Additional compliance scope",
            severity=RegisterEntrySeverity.MEDIUM,
        )
        register_service.update_entry(
            change.id,
            expected_version=change.version,
            status=RegisterEntryStatus.APPROVED,
        )
    finally:
        domain_events.register_changed.disconnect(_on_changed)

    summary = register_service.get_project_summary(project.id)
    assert summary.open_risks == 1
    assert summary.open_issues == 1
    assert summary.pending_changes == 0
    assert summary.overdue_items == 1
    assert summary.critical_items == 1
    assert summary.urgent_items[0].title == "Vendor delivery risk"
    assert captured.count(project.id) >= 4

    actions = [
        row.action
        for row in audit_service.list_recent(limit=20, project_id=project.id, entity_type="register_entry")
    ]
    assert "register.create" in actions
    assert "register.update" in actions
    assert risk.id in {entry.id for entry in register_service.list_entries(project_id=project.id)}
    assert issue.id in {entry.id for entry in register_service.list_entries(project_id=project.id)}


def test_register_tab_and_main_window_surface_register_runtime(qapp, services, repo_workspace, monkeypatch):
    project = services["project_service"].create_project("Register UI Project")
    services["register_service"].create_entry(
        project.id,
        entry_type=RegisterEntryType.RISK,
        title="Visible runtime risk",
        owner_name="Planner",
    )
    store = make_settings_store(repo_workspace, prefix="main-window-register")
    monkeypatch.setattr("ui.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(services)
    labels = [window.tabs.tabText(i) for i in range(window.tabs.count())]
    assert "Register" in labels

    tab = RegisterTab(
        register_service=services["register_service"],
        project_service=services["project_service"],
        user_session=services["user_session"],
    )
    assert tab.table.rowCount() >= 1
    assert tab.btn_new.isEnabled() is True
    assert "Visible runtime risk" in tab.summary_group.title()


def test_register_tab_create_entry_uses_qdialog_accepted_runtime(qapp, services, monkeypatch):
    project = services["project_service"].create_project("Register Create Runtime")

    class _AcceptedDialog:
        def __init__(self, *_args, **_kwargs):
            self.entry_type = RegisterEntryType.RISK
            self.title = "Created from runtime dialog"
            self.description = "Description"
            self.severity = RegisterEntrySeverity.HIGH
            self.status = RegisterEntryStatus.OPEN
            self.owner_name = "PM"
            self.due_date = date(2026, 3, 20)
            self.impact_summary = "Impact"
            self.response_plan = "Mitigate"

        def exec(self):
            return QDialog.Accepted

    monkeypatch.setattr("ui.register.tab.RegisterEntryDialog", _AcceptedDialog)
    tab = RegisterTab(
        register_service=services["register_service"],
        project_service=services["project_service"],
        user_session=services["user_session"],
    )
    tab.project_filter.setCurrentIndex(tab.project_filter.findData(project.id))

    tab.create_entry()

    entries = services["register_service"].list_entries(project_id=project.id)
    assert any(entry.title == "Created from runtime dialog" for entry in entries)


def test_import_wizard_runtime_supports_mapping_preview_and_commit(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    project = services["project_service"].create_project("Mapped Task Import")
    csv_path = repo_workspace / "mapped_tasks.csv"
    csv_path.write_text(
        "\n".join(
            [
                "project_lookup,task_title,length_days,progress_pct",
                "Mapped Task Import,Imported via wizard,3,50",
            ]
        ),
        encoding="utf-8",
    )
    info_messages: list[str] = []
    monkeypatch.setattr(
        "ui.project.import_wizard.QMessageBox.information",
        lambda _parent, _title, message: info_messages.append(message),
    )

    dialog = ImportWizardDialog(None, data_import_service=services["data_import_service"])
    dialog.type_combo.setCurrentIndex(dialog.type_combo.findData("tasks"))
    dialog.file_path_edit.setText(str(csv_path))
    dialog._load_columns_into_mapping()
    dialog._mapping_combos["project_name"].setCurrentIndex(
        dialog._mapping_combos["project_name"].findData("project_lookup")
    )
    dialog._mapping_combos["name"].setCurrentIndex(
        dialog._mapping_combos["name"].findData("task_title")
    )
    dialog._mapping_combos["duration_days"].setCurrentIndex(
        dialog._mapping_combos["duration_days"].findData("length_days")
    )
    dialog._mapping_combos["percent_complete"].setCurrentIndex(
        dialog._mapping_combos["percent_complete"].findData("progress_pct")
    )

    dialog._run_preview()

    assert "1 ready rows" in dialog.summary_label.text()
    assert dialog.preview_table.rowCount() == 1
    assert dialog.preview_table.item(0, 2).text() == "CREATE"
    assert dialog.btn_import.isEnabled() is True

    dialog._run_import()

    tasks = services["task_service"].list_tasks_for_project(project.id)
    assert any(task.name == "Imported via wizard" and task.percent_complete == 50.0 for task in tasks)
    assert info_messages
