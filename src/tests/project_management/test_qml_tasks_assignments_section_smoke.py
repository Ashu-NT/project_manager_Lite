"""Offscreen QML load smoke test for the redesigned Task Detail Assignment
section (docs §44 QML follow-up): the DataTable-based list plus the
Inspector panel must both instantiate without errors, including with a row
selected (which exercises the Task Planning / Execution / Project Resource
Context rendering paths)."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtGui import QGuiApplication

from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml

TASKS_ASSIGNMENTS_SECTION = Path(
    "src/ui_qml/modules/project_management/qml/workspaces/tasks/sections/TasksAssignmentsSection.qml"
)


def _ensure_qgui_application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["pm-tasks-assignments-section-test"])


def _load(initial_properties: dict) -> tuple[object, object]:
    _ensure_qgui_application()
    engine = create_qml_engine()
    load_qml(engine, TASKS_ASSIGNMENTS_SECTION.resolve(), initial_properties=initial_properties)
    root = engine.rootObjects()[0]
    return engine, root


def test_assignments_section_loads_with_no_selection() -> None:
    engine, root = _load({})
    assert root is not None
    engine.deleteLater()


def test_assignments_section_loads_with_a_selected_over_capacity_row() -> None:
    assignment_state = {
        "assignmentId": "assign-1",
        "taskId": "task-1",
        "resourceId": "resource-1",
        "resourceName": "Alice Brown",
        "allocationPercent": "50.0",
        "hoursLogged": "18",
        "plannedHours": "32",
        "remainingHours": "14",
        "projectResourceId": "pr-1",
        "responseStatus": "accepted",
        "responseStatusLabel": "Accepted",
        "canManage": True,
        "canAccept": False,
        "canDecline": False,
        "version": 2,
        "projectResourceVersion": 3,
        "capacityKnown": True,
        "capacityStatus": "OVER_CAPACITY",
        "capacityStatusLabel": "Over capacity",
        "availableCapacityLabel": "40.0 h",
        "committedCapacityLabel": "48.0 h",
        "capacityHeadroomLabel": "-8.0 h",
        "peakUtilizationPercent": 120.0,
        "remainingPlannedLabel": "14.0 h",
    }
    assignments_model = {
        "title": "Assignments",
        "subtitle": "1 resource",
        "emptyState": "",
        "items": [
            {
                "id": "assign-1",
                "title": "Alice Brown",
                "statusLabel": "Accepted",
                "subtitle": "Resource assignment",
                "supportingText": "18 h logged of 32 h planned (14 h remaining)",
                "metaText": "50.0%",
                "state": assignment_state,
            }
        ],
    }
    task_detail = {
        "fields": [
            {"label": "Start", "value": "01 Sep 2026"},
            {"label": "Finish", "value": "12 Sep 2026"},
        ]
    }
    project_resource_usage = {
        "projectResourceId": "pr-1",
        "plannedHoursLabel": "120.0 h",
        "allocatedToTasksHoursLabel": "100.0 h",
        "unallocatedPlannedHoursLabel": "20.0 h",
        "actualHoursLabel": "72.0 h",
        "remainingProjectHoursLabel": "48.0 h",
    }

    engine, root = _load(
        {
            "assignmentsModel": assignments_model,
            "selectedAssignmentId": "assign-1",
            "taskDetail": task_detail,
            "projectResourceUsage": project_resource_usage,
            "canCreate": True,
        }
    )
    assert root is not None
    engine.deleteLater()
