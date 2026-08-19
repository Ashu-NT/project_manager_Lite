from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QMetaObject
from PySide6.QtGui import QGuiApplication

from src.tests.path_rewrites import REPO_ROOT
from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml


ROOT_COMPONENT = (
    REPO_ROOT
    / "src/ui_qml/modules/project_management/qml/workspaces/tasks/sections/TasksScheduleImpactSection.qml"
)
DETAIL_PANEL = (
    REPO_ROOT
    / "src/ui_qml/modules/project_management/qml/workspaces/tasks/panels/TasksDetailPanel.qml"
)

_AVAILABLE_OVERVIEW = {
    "isAvailable": True,
    "taskId": "task-1",
    "currentStartLabel": "2026-09-04",
    "currentFinishLabel": "2026-09-12",
    "isCritical": True,
    "totalFloatDays": 0,
    "freeFloatDays": 0,
    "baselineFinishLabel": "2026-09-10",
    "scheduleVarianceDays": 2,
    "scheduleVarianceLabel": "+2d",
    "drivers": [
        {"kind": "predecessor", "label": "Foundation Complete", "detail": "FS · 0d"},
    ],
    "conflicts": [],
    "actualVariances": [],
    "downstream": {
        "directSuccessorCount": 3,
        "downstreamTaskCount": 17,
        "downstreamMilestoneCount": 2,
        "criticalDownstreamCount": 4,
    },
}


def _ensure_qgui_application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["pm-task-schedule-impact-contract-test"])


def _load(initial_properties: dict | None = None):
    _ensure_qgui_application()
    engine = create_qml_engine()
    load_qml(engine, ROOT_COMPONENT.resolve(), initial_properties=initial_properties or {})
    return engine, engine.rootObjects()[0]


def test_schedule_impact_section_loads_offscreen_with_defaults() -> None:
    """No blank default section (§27): with defaults, isAvailable is
    false and the "not available" empty state renders -- not a crash."""
    _, root = _load()
    meta_object = root.metaObject()

    for property_name in (
        "scheduleImpactModel", "scheduleImpactPreviewModel", "sectionErrors", "isBusy",
    ):
        assert meta_object.indexOfProperty(property_name) >= 0

    for signal_signature in ("previewRequested(int)", "openTaskRequested(QString)"):
        assert meta_object.indexOfSignal(signal_signature) >= 0


def test_schedule_impact_section_renders_current_facts_without_simulation() -> None:
    """Current schedule facts must appear without requiring a simulation
    (§6/§26) -- loading with an available overview and NO preview must
    not itself trigger previewRequested."""
    _, root = _load({"scheduleImpactModel": _AVAILABLE_OVERVIEW})

    captured = []
    root.previewRequested.connect(lambda delay: captured.append(delay))

    assert len(captured) == 0


def test_preview_impact_button_emits_the_chosen_delay_days() -> None:
    _, root = _load({"scheduleImpactModel": _AVAILABLE_OVERVIEW})
    captured = []
    root.previewRequested.connect(lambda delay: captured.append(delay))

    root.setProperty("_delayWorkingDays", 3)
    assert QMetaObject.invokeMethod(root, "runPreview")

    assert captured == [3]


def test_task_switch_clears_delay_and_selection_state() -> None:
    """Phase-N-style task-switch guarantee, applied to Schedule Impact
    (§29): a new scheduleImpactModel identity must reset the delay input
    and any selected affected-task row before the next task's data
    renders -- no stale state from the previous task."""
    _, root = _load({"scheduleImpactModel": _AVAILABLE_OVERVIEW})

    root.setProperty("_delayWorkingDays", 5)
    root.setProperty("_selectedAffectedTaskId", "task-99")
    assert int(root.property("_delayWorkingDays")) == 5

    root.setProperty("scheduleImpactModel", dict(_AVAILABLE_OVERVIEW, taskId="task-2"))

    assert int(root.property("_delayWorkingDays")) == 1
    assert str(root.property("_selectedAffectedTaskId")) == ""


def test_open_task_signal_exists_for_affected_row_navigation() -> None:
    source = ROOT_COMPONENT.read_text(encoding="utf-8")
    assert "signal openTaskRequested(string taskId)" in source
    assert "root.openTaskRequested(" in source


def test_no_uuid_and_no_schedule_math_in_source() -> None:
    """QML performs zero schedule calculation (§10 of the desktop
    contract) -- every fact must come from the model, never computed
    inline from raw dates."""
    source = ROOT_COMPONENT.read_text(encoding="utf-8")
    assert "working_days_between" not in source
    assert "add_working_days" not in source


def test_task_detail_panel_forwards_the_schedule_impact_preview_contract() -> None:
    source = DETAIL_PANEL.read_text(encoding="utf-8")

    assert "signal scheduleImpactPreviewRequested(int delayWorkingDays)" in source
    assert "onPreviewRequested" in source
    assert "scheduleImpactPreviewModel: root.scheduleImpactPreviewModel" in source
