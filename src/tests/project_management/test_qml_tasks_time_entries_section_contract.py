from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtGui import QGuiApplication

from src.tests.path_rewrites import REPO_ROOT
from src.ui_qml.modules.project_management.presenters.tasks.selection import (
    resolve_time_entry_id,
)
from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml


SECTION_ROOT = (
    REPO_ROOT
    / "src/ui_qml/modules/project_management/qml/workspaces/tasks/sections"
)
ROOT_COMPONENT = SECTION_ROOT / "TasksTimeEntriesSection.qml"
PRIVATE_COMPONENTS = (
    "TaskTimeOverview.qml",
    "TaskTimeEntryEditor.qml",
    "TaskTimeEntriesTable.qml",
)
DETAIL_PANEL = (
    REPO_ROOT
    / "src/ui_qml/modules/project_management/qml/workspaces/tasks/panels/TasksDetailPanel.qml"
)


def _implementation_source() -> str:
    sources = [ROOT_COMPONENT.read_text(encoding="utf-8")]
    sources.extend(
        path.read_text(encoding="utf-8")
        for name in PRIVATE_COMPONENTS
        if (path := SECTION_ROOT / name).exists()
    )
    return "\n".join(sources)


def _ensure_qgui_application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["pm-task-time-contract-test"])


def test_task_time_period_workflow_component_was_removed() -> None:
    # Period submit/lock/unlock is not task-scoped -- a period can span
    # other tasks' assignments too -- so it lives exclusively in the
    # canonical Timesheets or Review Queue workspace. This section only
    # keeps what's genuinely task-scoped: the task-level summary, quick
    # entry capture, and this task's own logged entries.
    assert not (SECTION_ROOT / "TaskTimePeriodWorkflow.qml").exists()


def test_old_assignment_tab_terminology_was_removed() -> None:
    """docs §44 Time redesign: "Assignment" must not appear as a Time tab
    label (it duplicates Task Detail -> Assignment), "Capture" is renamed
    to "Log Time", "Ledger" is renamed to "Time Entries", and the old
    period selector (a Timesheets-workspace concept) is gone entirely."""
    source = _implementation_source()

    assert '"label": "Assignment"' not in source
    assert '"label": "Capture"' not in source
    assert '"label": "Ledger"' not in source
    assert "selectTimePeriod" not in source
    assert "periodOptions" not in source
    assert "selectedPeriodStart" not in source
    assert "TaskTimeSummary {" not in source
    assert "TaskTimeEntryDetail {" not in source
    assert not (SECTION_ROOT / "TaskTimeSummary.qml").exists()
    assert not (SECTION_ROOT / "TaskTimeEntryDetail.qml").exists()


def test_task_time_root_public_contract_uses_the_redesigned_tabs() -> None:
    source = ROOT_COMPONENT.read_text(encoding="utf-8")

    for declaration in (
        "property var taskTimeSummary",
        "property var assignmentOptions",
        "property var taskTimeEntriesPage",
        "property var entriesTableModel",
        "property string timeResourceFilter",
        "property var selectedEntryDetail",
        "property string selectedEntryId",
        "property bool isBusy",
        "property string errorText",
        "signal addRequested(var payload)",
        "signal updateRequested(var payload)",
        "signal deleteRequested(string entryId)",
        "signal entrySelected(string entryId)",
        "signal resourceFilterRequested(string resourceId)",
        "signal pageRequested(int page)",
        "signal openTimesheetsRequested()",
        "signal goToAssignmentRequested(string assignmentId)",
    ):
        assert declaration in source

    for removed_signal in (
        "submitRequested(", "lockRequested(", "unlockRequested(",
        "periodChanged(", "assignmentChanged(",
    ):
        assert removed_signal not in source

    for tab_id in ('"overview"', '"logTime"', '"timeEntries"'):
        assert tab_id in source
    for tab_label in ('"Overview"', '"Log Time"', '"Time Entries"'):
        assert tab_label in source


def test_task_time_interactions_and_payload_contract_are_preserved() -> None:
    source = _implementation_source()

    for interaction in (
        "entrySelected(",
        "addRequested(",
        "updateRequested(",
        "deleteRequested(",
        "openTimesheetsRequested(",
    ):
        assert interaction in source

    for payload_key in (
        '"assignmentId"',
        '"entryId"',
        '"entryDate"',
        '"hours"',
        '"note"',
    ):
        assert payload_key in source


def test_time_entry_selection_is_explicit_and_never_defaults_to_first_row() -> None:
    class _Entry:
        def __init__(self, entry_id: str) -> None:
            self.entry_id = entry_id

    entries = (_Entry("entry-1"), _Entry("entry-2"))

    assert resolve_time_entry_id(None, entries) == ""
    assert resolve_time_entry_id("", entries) == ""
    assert resolve_time_entry_id("missing", entries) == ""
    assert resolve_time_entry_id("entry-2", entries) == "entry-2"


def test_time_entry_editor_has_success_reset_and_confirmed_delete_contract() -> None:
    editor_source = (SECTION_ROOT / "TaskTimeEntryEditor.qml").read_text(encoding="utf-8")
    section_source = ROOT_COMPONENT.read_text(encoding="utf-8")
    panel_source = DETAIL_PANEL.read_text(encoding="utf-8")

    assert "function resetForCreate()" in editor_source
    assert '_dateField.text = ""' in editor_source
    assert '_hoursField.text = ""' in editor_source
    assert '_noteArea.text = ""' in editor_source
    assert "AppControls.ConfirmationDialog" in editor_source
    assert "function resetTimeEntryEditor()" in section_source
    assert "function resetTimeEntryEditor()" in panel_source


def test_log_time_uses_description_label_not_labor_note() -> None:
    """docs §44 Time redesign §19: label the note field "Description," not
    the old implementation-flavored "Labor Note."""
    source = (SECTION_ROOT / "TaskTimeEntryEditor.qml").read_text(encoding="utf-8")
    assert 'text: "Description"' in source
    assert "Labor Note" not in source


def test_log_time_does_not_block_actual_exceeding_planned() -> None:
    """docs §44 Time redesign §16: actual work is historical truth --
    logging beyond planned hours must never be silently capped or
    rejected client-side."""
    source = (SECTION_ROOT / "TaskTimeEntryEditor.qml").read_text(encoding="utf-8")
    assert "overrun" in source.lower()
    assert "Math.min" not in source


def test_task_detail_panel_forwards_the_complete_task_time_contract() -> None:
    source = DETAIL_PANEL.read_text(encoding="utf-8")

    for forwarding_handler in (
        "onEntrySelected",
        "onAddRequested",
        "onUpdateRequested",
        "onDeleteRequested",
        "onOpenTimesheetsRequested",
        "onResourceFilterRequested",
        "onPageRequested",
        "onGoToAssignmentRequested",
    ):
        assert forwarding_handler in source

    for removed_handler in (
        "onSubmitRequested", "onLockRequested", "onUnlockRequested",
        "onPeriodChanged", "onAssignmentChanged",
    ):
        assert removed_handler not in source


def test_task_time_section_and_private_children_load_offscreen() -> None:
    _ensure_qgui_application()
    assert all((SECTION_ROOT / name).exists() for name in PRIVATE_COMPONENTS)

    engine = create_qml_engine()
    load_qml(engine, ROOT_COMPONENT.resolve())
    root = engine.rootObjects()[0]
    meta_object = root.metaObject()

    for property_name in (
        "taskTimeSummary",
        "assignmentOptions",
        "taskTimeEntriesPage",
        "entriesTableModel",
        "timeResourceFilter",
        "selectedEntryDetail",
        "selectedEntryId",
        "isBusy",
        "errorText",
    ):
        assert meta_object.indexOfProperty(property_name) >= 0

    for signal_signature in (
        "entrySelected(QString)",
        "addRequested(QVariant)",
        "updateRequested(QVariant)",
        "deleteRequested(QString)",
        "resourceFilterRequested(QString)",
        "pageRequested(int)",
        "openTimesheetsRequested()",
        "goToAssignmentRequested(QString)",
    ):
        assert meta_object.indexOfSignal(signal_signature) >= 0
