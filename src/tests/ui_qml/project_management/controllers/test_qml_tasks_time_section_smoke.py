"""Offscreen QML load smoke test for the redesigned Task Detail -> Time
section (docs §44 Time redesign): Overview / Log Time / Time Entries, the
always-visible summary strip, and the no-assignments empty state must all
instantiate without errors."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtGui import QGuiApplication

from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml

TASKS_TIME_SECTION = Path(
    "src/ui_qml/modules/project_management/qml/workspaces/tasks/sections/TasksTimeEntriesSection.qml"
)


def _ensure_qgui_application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["pm-tasks-time-section-test"])


def _load(initial_properties: dict) -> tuple[object, object]:
    _ensure_qgui_application()
    engine = create_qml_engine()
    load_qml(engine, TASKS_TIME_SECTION.resolve(), initial_properties=initial_properties)
    root = engine.rootObjects()[0]
    return engine, root


def test_time_section_loads_with_no_assignments() -> None:
    engine, root = _load({"assignmentOptions": []})
    assert root is not None
    engine.deleteLater()


def test_time_section_loads_with_summary_and_entries_populated() -> None:
    task_time_summary = {
        "hasSummary": True,
        "plannedHoursLabel": "56.0 h",
        "actualHoursLabel": "38.0 h",
        "remainingHoursLabel": "18.0 h",
        "overrunHoursLabel": "0.0 h",
        "hasOverrun": False,
        "burnStatus": "WITHIN_PLAN",
        "burnStatusLabel": "Within Plan",
        "assignmentCount": 2,
        "resourceBreakdown": [
            {
                "assignmentId": "assign-1",
                "resourceId": "resource-1",
                "resourceName": "Alice Brown",
                "plannedHoursLabel": "32.0 h",
                "actualHoursLabel": "18.0 h",
                "remainingHoursLabel": "14.0 h",
                "overrunHoursLabel": "0.0 h",
                "hasOverrun": False,
                "burnStatus": "WITHIN_PLAN",
                "burnStatusLabel": "Within Plan",
            },
            {
                "assignmentId": "assign-2",
                "resourceId": "resource-2",
                "resourceName": "Bob Smith",
                "plannedHoursLabel": "24.0 h",
                "actualHoursLabel": "20.0 h",
                "remainingHoursLabel": "4.0 h",
                "overrunHoursLabel": "0.0 h",
                "hasOverrun": False,
                "burnStatus": "WITHIN_PLAN",
                "burnStatusLabel": "Within Plan",
            },
        ],
    }
    assignment_options = [
        {"value": "assign-1", "label": "Alice Brown — 32h planned"},
        {"value": "assign-2", "label": "Bob Smith — 24h planned"},
    ]
    task_time_entries_page = {
        "items": [
            {
                "entryId": "entry-1",
                "assignmentId": "assign-1",
                "resourceId": "resource-1",
                "resourceName": "Alice Brown",
                "entryDateLabel": "2026-08-17",
                "hours": 12.0,
                "hoursLabel": "12.00h",
                "note": "Wiring",
                "authorUsername": "alice",
            }
        ],
        "total": 1,
        "page": 1,
        "pageSize": 25,
    }

    engine, root = _load(
        {
            "taskTimeSummary": task_time_summary,
            "assignmentOptions": assignment_options,
            "taskTimeEntriesPage": task_time_entries_page,
        }
    )
    assert root is not None
    engine.deleteLater()


def test_time_section_loads_with_overrun_summary() -> None:
    task_time_summary = {
        "hasSummary": True,
        "plannedHoursLabel": "8.0 h",
        "actualHoursLabel": "12.0 h",
        "remainingHoursLabel": "0.0 h",
        "overrunHoursLabel": "4.0 h",
        "hasOverrun": True,
        "burnStatus": "OVERRUN",
        "burnStatusLabel": "Overrun",
        "assignmentCount": 1,
        "resourceBreakdown": [
            {
                "assignmentId": "assign-1",
                "resourceId": "resource-1",
                "resourceName": "Alice Brown",
                "plannedHoursLabel": "8.0 h",
                "actualHoursLabel": "12.0 h",
                "remainingHoursLabel": "0.0 h",
                "overrunHoursLabel": "4.0 h",
                "hasOverrun": True,
                "burnStatus": "OVERRUN",
                "burnStatusLabel": "Overrun",
            }
        ],
    }
    engine, root = _load(
        {
            "taskTimeSummary": task_time_summary,
            "assignmentOptions": [{"value": "assign-1", "label": "Alice Brown — 8h planned"}],
        }
    )
    assert root is not None
    engine.deleteLater()
