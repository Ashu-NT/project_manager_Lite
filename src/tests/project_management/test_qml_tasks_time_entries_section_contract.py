from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtGui import QGuiApplication

from src.tests.path_rewrites import REPO_ROOT
from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml


SECTION_ROOT = (
    REPO_ROOT
    / "src/ui_qml/modules/project_management/qml/workspaces/tasks/sections"
)
ROOT_COMPONENT = SECTION_ROOT / "TasksTimeEntriesSection.qml"
PRIVATE_COMPONENTS = (
    "TaskTimeSummary.qml",
    "TaskTimeEntryEditor.qml",
    "TaskTimeEntriesTable.qml",
    "TaskTimeEntryDetail.qml",
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
    # other tasks' assignments too -- so it now lives exclusively in the
    # Timesheets workspace (My Time / Review Queue). This section only
    # keeps what's genuinely task-scoped: assignment/period selection,
    # quick entry capture, and this task's own logged entries.
    assert not (SECTION_ROOT / "TaskTimePeriodWorkflow.qml").exists()


def test_task_time_root_public_contract_is_stable() -> None:
    source = ROOT_COMPONENT.read_text(encoding="utf-8")

    for declaration in (
        "property var assignmentSummary",
        "property var assignmentOptions",
        "property var periodOptions",
        "property string selectedPeriodStart",
        "property var entriesModel",
        "property var entriesTableModel",
        "property var selectedEntryDetail",
        "property string selectedEntryId",
        "property bool isBusy",
        "property string errorText",
        "signal periodChanged(string periodStart)",
        "signal assignmentChanged(string assignmentId)",
        "signal entrySelected(string entryId)",
        "signal addRequested(var payload)",
        "signal updateRequested(var payload)",
        "signal deleteRequested(string entryId)",
        "signal openTimesheetsRequested()",
    ):
        assert declaration in source

    for removed_signal in ("submitRequested(", "lockRequested(", "unlockRequested("):
        assert removed_signal not in source

    assert "property alias" not in source


def test_task_time_interactions_and_payload_contract_are_preserved() -> None:
    source = _implementation_source()

    for interaction in (
        "assignmentChanged(",
        "periodChanged(",
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


def test_task_time_summary_and_state_presentation_are_preserved() -> None:
    source = _implementation_source()

    for text in (
        '"Assignment"',
        '"Capture"',
        '"Ledger"',
        '"Resource"',
        '"Hours"',
        'text: "Add Entry"',
        'text: "Update"',
        'text: "Delete"',
        "root.errorText",
        "root.isBusy",
        "root.selectedEntryId",
    ):
        assert text in source

    assert "onSelectedEntryDetailChanged" in source
    assert "_syncEditorFields" in source


def test_task_detail_panel_forwards_the_complete_task_time_contract() -> None:
    source = DETAIL_PANEL.read_text(encoding="utf-8")

    for forwarding_handler in (
        "onAssignmentChanged",
        "onPeriodChanged",
        "onEntrySelected",
        "onAddRequested",
        "onUpdateRequested",
        "onDeleteRequested",
        "onOpenTimesheetsRequested",
    ):
        assert forwarding_handler in source

    for removed_handler in ("onSubmitRequested", "onLockRequested", "onUnlockRequested"):
        assert removed_handler not in source


def test_task_time_section_and_private_children_load_offscreen() -> None:
    _ensure_qgui_application()
    assert all((SECTION_ROOT / name).exists() for name in PRIVATE_COMPONENTS)

    engine = create_qml_engine()
    load_qml(engine, ROOT_COMPONENT.resolve())
    root = engine.rootObjects()[0]
    meta_object = root.metaObject()

    for property_name in (
        "assignmentSummary",
        "assignmentOptions",
        "periodOptions",
        "selectedPeriodStart",
        "entriesModel",
        "entriesTableModel",
        "selectedEntryDetail",
        "selectedEntryId",
        "isBusy",
        "errorText",
    ):
        assert meta_object.indexOfProperty(property_name) >= 0

    for signal_signature in (
        "periodChanged(QString)",
        "assignmentChanged(QString)",
        "entrySelected(QString)",
        "addRequested(QVariant)",
        "updateRequested(QVariant)",
        "deleteRequested(QString)",
        "openTimesheetsRequested()",
    ):
        assert meta_object.indexOfSignal(signal_signature) >= 0
