from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Property, Q_ARG, QObject, QMetaObject
from PySide6.QtGui import QGuiApplication

from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml


class _FakeProjectsWorkspaceController(QObject):
    """Minimal stand-in for the real controller's constant currency options,
    matching what `ProjectEditorDialog.qml`'s currency dropdown now reads."""

    @Property(bool, constant=True)
    def isBusy(self) -> bool:
        return False

    @Property("QVariantList", constant=True)
    def currencyOptions(self) -> list:
        return [
            {"value": "EUR", "label": "EUR"},
            {"value": "USD", "label": "USD"},
            {"value": "XAF", "label": "XAF"},
        ]

    @Property(str, constant=True)
    def defaultCurrencyCode(self) -> str:
        return "XAF"


class _FakeTasksWorkspaceController(QObject):
    """Minimal stand-in exposing just what TaskEditorDialog's Advanced
    scheduling section reads -- constraintOptions must mirror the real
    EDITABLE_CONSTRAINT_OPTIONS shape (value/code/label/description/
    requiresDate/category) since the dialog binds those exact keys."""

    @Property(bool, constant=True)
    def isBusy(self) -> bool:
        return False

    @Property("QVariantList", constant=True)
    def constraintOptions(self) -> list:
        return [
            {
                "value": "", "code": "ASAP", "label": "As Soon As Possible (ASAP)",
                "description": "Task is scheduled from dependencies, duration and project calendar.",
                "requiresDate": False, "category": "flexible",
            },
            {
                "value": "start_no_earlier_than", "code": "SNET", "label": "Start No Earlier Than (SNET)",
                "description": "Task cannot start before the specified date.",
                "requiresDate": True, "category": "date_boundary",
            },
            {
                "value": "must_start_on", "code": "MSO", "label": "Must Start On (MSO)",
                "description": "Fixes the task to the specified start date.",
                "requiresDate": True, "category": "fixed_date",
            },
        ]


PROJECT_EDITOR_DIALOG = Path(
    "src/ui_qml/modules/project_management/qml/workspaces/projects/dialogs/ProjectEditorDialog.qml"
)
PROJECT_STATUS_DIALOG = Path(
    "src/ui_qml/modules/project_management/qml/workspaces/projects/dialogs/ProjectStatusDialog.qml"
)
TASK_EDITOR_DIALOG = Path(
    "src/ui_qml/modules/project_management/qml/workspaces/tasks/dialogs/TaskEditorDialog.qml"
)
TASK_PROGRESS_DIALOG = Path(
    "src/ui_qml/modules/project_management/qml/workspaces/tasks/dialogs/TaskProgressDialog.qml"
)
TASK_ASSIGNMENT_EDITOR_DIALOG = Path(
    "src/ui_qml/modules/project_management/qml/workspaces/tasks/dialogs/TaskAssignmentEditorDialog.qml"
)
TASK_DEPENDENCY_EDITOR_DIALOG = Path(
    "src/ui_qml/modules/project_management/qml/workspaces/tasks/dialogs/TaskDependencyEditorDialog.qml"
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
    controller = _FakeProjectsWorkspaceController()
    _, root = _load_dialog(
        PROJECT_EDITOR_DIALOG,
        {
            "modeTitle": "Edit Project",
            "workspaceController": controller,
            "statusOptions": [{"value": "IN_PROGRESS", "label": "In Progress"}],
            "projectData": {
                "state": {
                    "name": "Refinery Upgrade",
                    "clientName": "North Plant",
                    "clientContact": "ops@example.com",
                    "financialCurrencyCode": "EUR",
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
    assert captured[0]["financialCurrencyCode"] == "EUR"
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
                    "taskId": "task-99",
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


def test_task_editor_dialog_milestone_checkbox_zeroes_duration() -> None:
    _, root = _load_dialog(
        TASK_EDITOR_DIALOG,
        {
            "modeTitle": "Edit Task",
            "statusOptions": [{"value": "IN_PROGRESS", "label": "In Progress"}],
            "taskData": {
                "state": {
                    "taskId": "task-99",
                    "name": "Handover",
                    "startDate": "2026-05-10",
                    "durationDays": "5",
                    "status": "IN_PROGRESS",
                }
            },
        },
    )
    captured: list[dict] = []
    root.submitted.connect(lambda payload: captured.append(_variant(payload)))

    assert QMetaObject.invokeMethod(root, "populateFromTask")
    milestone_check = _find_child(root, "milestoneCheck")
    assert milestone_check.property("checked") is False

    milestone_check.setProperty("checked", True)
    submit_button = _find_child(root, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert len(captured) == 1
    assert captured[0]["isMilestone"] is True
    assert captured[0]["durationDays"] == "0"


def test_task_editor_dialog_populates_existing_milestone_flag() -> None:
    _, root = _load_dialog(
        TASK_EDITOR_DIALOG,
        {
            "modeTitle": "Edit Task",
            "statusOptions": [{"value": "IN_PROGRESS", "label": "In Progress"}],
            "taskData": {
                "state": {
                    "taskId": "task-99",
                    "name": "Handover",
                    "durationDays": "0",
                    "status": "IN_PROGRESS",
                    "isMilestone": True,
                }
            },
        },
    )

    assert QMetaObject.invokeMethod(root, "populateFromTask")
    milestone_check = _find_child(root, "milestoneCheck")
    assert milestone_check.property("checked") is True


def test_task_editor_dialog_defaults_to_asap_and_omits_constraint_date() -> None:
    """Phase N/O: a brand-new task with no prior constraint state must
    default the picker to ASAP and never report a changed constraint on
    create (constraintChanged only matters for the edit/update path)."""
    controller = _FakeTasksWorkspaceController()
    _, root = _load_dialog(
        TASK_EDITOR_DIALOG,
        {
            "modeTitle": "Create Task",
            "workspaceController": controller,
            "statusOptions": [{"value": "TODO", "label": "To Do"}],
            "projectOptions": [{"value": "proj-1", "label": "Refinery"}],
            "taskData": {"state": {"name": "Cable Pull"}},
        },
    )
    captured: list[dict] = []
    root.submitted.connect(lambda payload: captured.append(_variant(payload)))

    assert QMetaObject.invokeMethod(root, "populateFromTask")
    combo = _find_child(root, "constraintTypeCombo")
    assert combo.property("currentIndex") == 0

    submit_button = _find_child(root, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert len(captured) == 1
    assert captured[0]["constraintType"] == ""
    assert captured[0]["constraintDate"] == ""
    assert captured[0]["constraintChanged"] is False


def test_task_editor_dialog_dated_constraint_requires_date_before_submit() -> None:
    """Phase O: selecting a dated constraint type (SNET here) without a
    date must block submission with an inline error rather than send a
    half-filled constraint to the backend."""
    controller = _FakeTasksWorkspaceController()
    _, root = _load_dialog(
        TASK_EDITOR_DIALOG,
        {
            "modeTitle": "Create Task",
            "workspaceController": controller,
            "statusOptions": [{"value": "TODO", "label": "To Do"}],
            "projectOptions": [{"value": "proj-1", "label": "Refinery"}],
            "taskData": {"state": {"name": "Cable Pull"}},
        },
    )
    captured: list[dict] = []
    root.submitted.connect(lambda payload: captured.append(_variant(payload)))

    assert QMetaObject.invokeMethod(root, "populateFromTask")
    combo = _find_child(root, "constraintTypeCombo")
    combo.setProperty("currentIndex", 1)  # SNET, requires a date

    submit_button = _find_child(root, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(submit_button, "click")
    assert len(captured) == 0
    assert "SNET" in str(root.property("errorMessage")) or "Start No Earlier Than" in str(root.property("errorMessage"))

    date_field = _find_child(root, "constraintDateField")
    date_field.setProperty("text", "2026-09-18")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert len(captured) == 1
    assert captured[0]["constraintType"] == "start_no_earlier_than"
    assert captured[0]["constraintDate"] == "2026-09-18"
    assert captured[0]["constraintChanged"] is True


def test_task_editor_dialog_populates_existing_constraint_and_expands_section() -> None:
    """Phase N: an existing task that already carries a constraint must
    auto-expand the collapsed Advanced scheduling section so the current
    value is visible without an extra click, and must round-trip it back
    unchanged if the user does not touch the picker."""
    controller = _FakeTasksWorkspaceController()
    _, root = _load_dialog(
        TASK_EDITOR_DIALOG,
        {
            "modeTitle": "Edit Task",
            "workspaceController": controller,
            "statusOptions": [{"value": "IN_PROGRESS", "label": "In Progress"}],
            "taskData": {
                "state": {
                    "taskId": "task-99",
                    "name": "Cable Pull",
                    "status": "IN_PROGRESS",
                    "constraintType": "must_start_on",
                    "constraintDate": "2026-09-18",
                }
            },
        },
    )
    captured: list[dict] = []
    root.submitted.connect(lambda payload: captured.append(_variant(payload)))

    assert QMetaObject.invokeMethod(root, "populateFromTask")
    assert root.property("advancedSchedulingExpanded") is True
    combo = _find_child(root, "constraintTypeCombo")
    assert combo.property("currentIndex") == 2  # MSO

    submit_button = _find_child(root, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert len(captured) == 1
    assert captured[0]["constraintType"] == "must_start_on"
    assert captured[0]["constraintDate"] == "2026-09-18"
    assert captured[0]["constraintChanged"] is False


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


def test_task_dependency_editor_dialog_submit_button_emits_create_payload() -> None:
    """Phase N7: the shared dependency dialog in create mode must emit a
    payload the presenter's create_dependency() can consume unchanged."""
    _, root = _load_dialog(
        TASK_DEPENDENCY_EDITOR_DIALOG,
        {
            "mode": "create",
            "taskOptions": [{"value": "task-2", "label": "Foundation Complete"}],
            "dependencyTypeOptions": [
                {"value": "FS", "label": "Finish -> Start"},
                {"value": "SS", "label": "Start -> Start"},
            ],
            "taskData": {"title": "Current Task", "state": {"taskId": "task-1", "name": "Current Task"}},
        },
    )
    captured: list[dict] = []
    root.submitted.connect(lambda payload: captured.append(_variant(payload)))

    submit_button = _find_child(root, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(root, "populateForm")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert len(captured) == 1
    assert captured[0]["taskId"] == "task-1"
    assert captured[0]["linkedTaskId"] == "task-2"
    assert captured[0]["relationshipDirection"] == "PREDECESSOR"
    assert captured[0]["dependencyType"] == "FS"
    assert captured[0]["lagDays"] == "0"


def test_task_dependency_editor_dialog_submit_button_emits_edit_payload_with_version() -> None:
    """Phase N10: edit mode only touches relationship type/lag, and must
    thread the loaded version through so the backend can detect a stale
    write (the two endpoints can't be changed via edit -- remove/re-add)."""
    _, root = _load_dialog(
        TASK_DEPENDENCY_EDITOR_DIALOG,
        {
            "mode": "edit",
            "dependencyTypeOptions": [
                {"value": "FS", "label": "Finish -> Start"},
                {"value": "SS", "label": "Start -> Start"},
            ],
            "dependencyData": {
                "id": "dep-1",
                "state": {
                    "dependencyId": "dep-1",
                    "dependencyType": "FS",
                    "lagDays": "2",
                    "direction": "PREDECESSOR",
                    "linkedTaskName": "Foundation Complete",
                    "version": "3",
                },
            },
        },
    )
    captured: list[dict] = []
    root.submitted.connect(lambda payload: captured.append(_variant(payload)))

    submit_button = _find_child(root, "dialogSubmitButton")
    assert QMetaObject.invokeMethod(root, "populateForm")
    assert QMetaObject.invokeMethod(submit_button, "click")

    assert len(captured) == 1
    assert captured[0]["dependencyId"] == "dep-1"
    assert captured[0]["dependencyType"] == "FS"
    assert captured[0]["lagDays"] == "2"
    assert captured[0]["version"] == "3"


def test_tasks_dialog_host_open_edit_dependency_dialog_prepares_editor() -> None:
    _, root = _load_dialog(
        TASKS_DIALOG_HOST,
        {
            "dependencyTypeOptions": [{"value": "FS", "label": "Finish -> Start"}],
        },
    )

    dependency_dialog = _find_child(root, "taskDependencyEditorDialog")

    dependency_data = {
        "id": "dep-1",
        "state": {"dependencyId": "dep-1", "dependencyType": "FS", "lagDays": "1", "version": "2"},
    }
    assert QMetaObject.invokeMethod(
        root, "openEditDependencyDialog", Q_ARG("QVariant", dependency_data)
    )

    assert str(dependency_dialog.property("mode")) == "edit"
    loaded = _variant(dependency_dialog.property("dependencyData"))
    assert loaded["state"]["dependencyId"] == "dep-1"


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

