from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Q_ARG, QObject, QMetaObject
from PySide6.QtGui import QGuiApplication

from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml


PROJECT_EDITOR_DIALOG = Path(
    "src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/ProjectEditorDialog.qml"
)
PROJECT_STATUS_DIALOG = Path(
    "src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/ProjectStatusDialog.qml"
)
TASK_EDITOR_DIALOG = Path(
    "src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/TaskEditorDialog.qml"
)
TASK_PROGRESS_DIALOG = Path(
    "src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/TaskProgressDialog.qml"
)
TASK_ASSIGNMENT_EDITOR_DIALOG = Path(
    "src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/TaskAssignmentEditorDialog.qml"
)
TASKS_DIALOG_HOST = Path(
    "src/ui_qml/modules/project_management/qml/workspaces/tasks/TasksDialogHost.qml"
)


def _ensure_qgui_application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["pm-dialog-test"])


def _load_dialog(qml_path: Path, initial_properties: dict) -> tuple[object, QObject]:
    _ensure_qgui_application()
    engine = create_qml_engine()
    load_qml(engine, qml_path.resolve(), initial_properties=initial_properties)
    root = engine.rootObjects()[0]
    return engine, root


def _find_child(root: QObject, name: str) -> QObject:
    child = root.findChild(QObject, name)
    assert child is not None, f"Expected child object {name!r}"
    return child


def _variant(value):
    return value.toVariant() if hasattr(value, "toVariant") else value


def test_project_editor_dialog_submit_button_emits_payload() -> None:
    _, root = _load_dialog(
        PROJECT_EDITOR_DIALOG,
        {
            "modeTitle": "Edit Project",
            "statusOptions": [{"value": "IN_PROGRESS", "label": "In Progress"}],
            "projectData": {
                "state": {
                    "name": "Refinery Upgrade",
                    "clientName": "North Plant",
                    "clientContact": "ops@example.com",
                    "plannedBudget": "125000",
                    "currency": "EUR",
                    "startDate": "2026-05-01",
                    "endDate": "2026-07-31",
                    "description": "Shutdown coordination",
                    "status": "IN_PROGRESS",
                }
            },
        },
    )
    captured: list[dict] = []
    root.submitted.connect(lambda payload: captured.append(_variant(payload)))

    _find_child(root, "dialogCancelButton")
    submit_button = _find_child(root, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(root, "populateFromProject")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert len(captured) == 1
    assert captured[0]["name"] == "Refinery Upgrade"
    assert captured[0]["currency"] == "EUR"
    assert captured[0]["status"] == "IN_PROGRESS"


def test_project_status_dialog_submit_button_emits_status() -> None:
    _, root = _load_dialog(
        PROJECT_STATUS_DIALOG,
        {
            "statusOptions": [{"value": "PLANNED", "label": "Planned"}],
            "projectData": {"title": "Refinery Upgrade", "state": {"status": "PLANNED"}},
        },
    )
    captured: list[str] = []
    root.submitted.connect(lambda status_value: captured.append(str(status_value)))

    _find_child(root, "dialogCancelButton")
    submit_button = _find_child(root, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert captured == ["PLANNED"]


def test_task_editor_dialog_submit_button_emits_payload() -> None:
    _, root = _load_dialog(
        TASK_EDITOR_DIALOG,
        {
            "modeTitle": "Edit Task",
            "statusOptions": [{"value": "IN_PROGRESS", "label": "In Progress"}],
            "taskData": {
                "state": {
                    "name": "Cable Pull",
                    "startDate": "2026-05-10",
                    "durationDays": "5",
                    "deadline": "2026-05-20",
                    "priority": "80",
                    "description": "Route and terminate feeder cables",
                    "status": "IN_PROGRESS",
                }
            },
        },
    )
    captured: list[dict] = []
    root.submitted.connect(lambda payload: captured.append(_variant(payload)))

    _find_child(root, "dialogCancelButton")
    submit_button = _find_child(root, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(root, "populateFromTask")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert len(captured) == 1
    assert captured[0]["name"] == "Cable Pull"
    assert captured[0]["durationDays"] == "5"
    assert captured[0]["status"] == "IN_PROGRESS"


def test_task_progress_dialog_submit_button_emits_payload() -> None:
    _, root = _load_dialog(
        TASK_PROGRESS_DIALOG,
        {
            "statusOptions": [{"value": "DONE", "label": "Done"}],
            "taskData": {
                "title": "Cable Pull",
                "state": {
                    "taskId": "task-1",
                    "version": 3,
                    "percentComplete": "72.5",
                    "actualStart": "2026-05-10",
                    "actualEnd": "2026-05-18",
                    "status": "DONE",
                },
            },
        },
    )
    captured: list[dict] = []
    root.submitted.connect(lambda payload: captured.append(_variant(payload)))

    _find_child(root, "dialogCancelButton")
    submit_button = _find_child(root, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(root, "populateFromTask")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert len(captured) == 1
    assert captured[0]["taskId"] == "task-1"
    assert captured[0]["percentComplete"] == "72.5"
    assert captured[0]["status"] == "DONE"


def test_task_assignment_editor_dialog_submit_button_emits_payload() -> None:
    _, root = _load_dialog(
        TASK_ASSIGNMENT_EDITOR_DIALOG,
        {
            "mode": "create",
            "resourceOptions": [{"value": "res-1", "label": "Alex Taylor"}],
            "taskData": {"title": "Cable Pull", "state": {"taskId": "task-1", "name": "Cable Pull"}},
        },
    )
    captured: list[dict] = []
    root.submitted.connect(lambda payload: captured.append(_variant(payload)))

    _find_child(root, "dialogCancelButton")
    submit_button = _find_child(root, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(root, "populateForm")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert len(captured) == 1
    assert captured[0]["taskId"] == "task-1"
    assert captured[0]["projectResourceId"] == "res-1"
    assert captured[0]["allocationPercent"] == "100.0"


def test_tasks_dialog_host_open_create_dialog_prepares_editor() -> None:
    _, root = _load_dialog(
        TASKS_DIALOG_HOST,
        {
            "statusOptions": [{"value": "TODO", "label": "To Do"}],
            "selectedProjectId": "proj-1",
        },
    )

    editor_dialog = _find_child(root, "taskEditorDialog")

    assert QMetaObject.invokeMethod(root, "openCreateDialog")

    assert str(editor_dialog.property("modeTitle")) == "Create Task"
    task_data = _variant(editor_dialog.property("taskData"))
    assert task_data["state"]["status"] == "TODO"

