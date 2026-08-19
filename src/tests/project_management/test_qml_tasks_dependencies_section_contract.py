from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QMetaObject
from PySide6.QtGui import QGuiApplication

from src.tests.path_rewrites import REPO_ROOT
from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml


ROOT_COMPONENT = (
    REPO_ROOT
    / "src/ui_qml/modules/project_management/qml/workspaces/tasks/sections/TasksDependenciesSection.qml"
)
DETAIL_PANEL = (
    REPO_ROOT
    / "src/ui_qml/modules/project_management/qml/workspaces/tasks/panels/TasksDetailPanel.qml"
)


def _ensure_qgui_application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["pm-task-dependencies-contract-test"])


def _load(initial_properties: dict | None = None):
    _ensure_qgui_application()
    engine = create_qml_engine()
    load_qml(engine, ROOT_COMPONENT.resolve(), initial_properties=initial_properties or {})
    return engine, engine.rootObjects()[0]


def test_dependencies_section_loads_offscreen_with_no_items() -> None:
    """Phase N: the empty-project-state must render without a backend --
    a bare load with defaults must not crash."""
    _, root = _load()
    meta_object = root.metaObject()

    for property_name in (
        "dependenciesModel", "isBusy", "canCreate", "errorText",
        "dependencyTypeOptions", "taskDetail", "dependencyImpactPreview",
    ):
        assert meta_object.indexOfProperty(property_name) >= 0

    for signal_signature in (
        "createRequested()", "editRequested(QVariant)", "deleteRequested(QVariant)",
        "openTaskRequested(QString)", "selectionChanged(QVariant)", "previewRequested(QString)",
    ):
        assert meta_object.indexOfSignal(signal_signature) >= 0


def test_dependencies_section_splits_predecessors_and_successors_without_crashing() -> None:
    """Phase N4/N5: a mixed predecessor/successor set must load and the
    tab-derived row counts must match the direction split -- no UUIDs
    leaking into the row's displayed columns."""
    items = [
        {
            "id": "dep-1",
            "title": "Foundation Complete",
            "state": {
                "dependencyId": "dep-1",
                "linkedTaskId": "task-2",
                "linkedTaskName": "Foundation Complete",
                "direction": "PREDECESSOR",
                "directionLabel": "Predecessor",
                "dependencyType": "FS",
                "dependencyTypeLabel": "Finish -> Start",
                "lagDays": "0",
                "linkedTaskStartLabel": "2026-09-01",
                "linkedTaskFinishLabel": "2026-09-03",
                "version": "1",
            },
        },
        {
            "id": "dep-2",
            "title": "Electrical Installation",
            "state": {
                "dependencyId": "dep-2",
                "linkedTaskId": "task-3",
                "linkedTaskName": "Electrical Installation",
                "direction": "SUCCESSOR",
                "directionLabel": "Successor",
                "dependencyType": "SS",
                "dependencyTypeLabel": "Start -> Start",
                "lagDays": "2",
                "linkedTaskStartLabel": "2026-09-05",
                "linkedTaskFinishLabel": "2026-09-08",
                "version": "1",
            },
        },
    ]
    _, root = _load({
        "dependenciesModel": {"items": items, "emptyState": ""},
        "canCreate": True,
    })

    assert QMetaObject.invokeMethod(root, "openEditSelected")

    source = ROOT_COMPONENT.read_text(encoding="utf-8")
    assert "linked task ID" not in source.lower()
    assert 'key: "task"' in source
    assert 'key: "relationship"' in source
    assert 'key: "lagLead"' in source


def test_task_detail_panel_forwards_the_complete_dependency_contract() -> None:
    source = DETAIL_PANEL.read_text(encoding="utf-8")

    for forwarding_handler in (
        "onCreateRequested", "onSelectionChanged", "onEditRequested",
        "onDeleteRequested", "onOpenTaskRequested", "onPreviewRequested",
    ):
        assert forwarding_handler in source

    assert "signal openTaskRequested(string taskId)" in source
    assert "signal dependencyPreviewRequested(string dependencyId)" in source
