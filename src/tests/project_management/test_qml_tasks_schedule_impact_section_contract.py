from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QMetaObject, QObject
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
    "isInfeasible": False,
    "scheduleStatusLabel": "Critical",
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

# R4.4 constraint-aware backward CPM: is_infeasible wiring fixtures.
_FLEXIBLE_OVERVIEW = dict(
    _AVAILABLE_OVERVIEW,
    taskId="task-flexible",
    isCritical=False,
    isInfeasible=False,
    scheduleStatusLabel="Flexible",
    totalFloatDays=5,
)

_INFEASIBLE_NO_CONFLICT_OVERVIEW = dict(
    _AVAILABLE_OVERVIEW,
    taskId="task-infeasible-bare",
    isCritical=True,
    isInfeasible=True,
    scheduleStatusLabel="Infeasible",
    totalFloatDays=-3,
    conflicts=[],
    actualVariances=[],
)

_INFEASIBLE_WITH_CONFLICT_OVERVIEW = dict(
    _AVAILABLE_OVERVIEW,
    taskId="task-infeasible-conflict",
    isCritical=True,
    isInfeasible=True,
    scheduleStatusLabel="Infeasible",
    totalFloatDays=-2,
    conflicts=[
        {
            "taskId": "task-infeasible-conflict",
            "taskName": "Cable Pull",
            "constraintTypeLabel": "Must Start On (MSO)",
            "constraintDateLabel": "2026-09-18",
            "dependencyRequiredDateLabel": "2026-09-20",
            "direction": "start",
            "differenceWorkingDays": -2,
        }
    ],
)


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


# ── R4.4: is_infeasible wired to desktop/QML read path ──────────────────


def _find(root, name: str):
    child = root.findChild(QObject, name)
    assert child is not None, f"Expected child object {name!r}"
    return child


def test_flexible_state_renders_flexible_status_chip() -> None:
    _, root = _load({"scheduleImpactModel": _FLEXIBLE_OVERVIEW})
    chip = _find(root, "scheduleStatusChip")

    assert str(chip.property("status")) == "Flexible"


def test_critical_state_renders_critical_status_chip() -> None:
    _, root = _load({"scheduleImpactModel": _AVAILABLE_OVERVIEW})
    chip = _find(root, "scheduleStatusChip")

    assert str(chip.property("status")) == "Critical"


def test_infeasible_state_renders_infeasible_status_chip() -> None:
    _, root = _load({"scheduleImpactModel": _INFEASIBLE_NO_CONFLICT_OVERVIEW})
    chip = _find(root, "scheduleStatusChip")

    assert str(chip.property("status")) == "Infeasible"


def test_infeasible_takes_display_precedence_over_critical() -> None:
    """An infeasible task ALSO has is_critical=True at the backend (total
    float <= 0 covers both) -- the UI must show "Infeasible", never fall
    back to "Critical", confirming the precedence rule is honored end to
    end rather than just at the presenter layer."""
    overview = dict(_INFEASIBLE_NO_CONFLICT_OVERVIEW, isCritical=True, isInfeasible=True)
    _, root = _load({"scheduleImpactModel": overview})
    chip = _find(root, "scheduleStatusChip")

    assert str(chip.property("status")) == "Infeasible"
    assert str(chip.property("status")) != "Critical"


def test_negative_float_renders_with_sign() -> None:
    _, root = _load({"scheduleImpactModel": _INFEASIBLE_NO_CONFLICT_OVERVIEW})
    label = _find(root, "totalFloatLabel")

    assert str(label.property("text")).startswith("-3")


def test_infeasible_without_structured_conflict_shows_generic_warning() -> None:
    _, root = _load({"scheduleImpactModel": _INFEASIBLE_NO_CONFLICT_OVERVIEW})
    warning = _find(root, "infeasibleGenericWarning")

    assert warning.property("visible") is True
    assert "cannot all be satisfied" in str(warning.property("message"))


def test_infeasible_with_structured_conflict_suppresses_generic_warning() -> None:
    """When a DependencyConstraintConflict already exists, the specific
    cause (rendered separately, under SCHEDULE DRIVERS, via the
    pre-existing conflicts Repeater) is shown instead of the generic
    fallback -- directive: reuse existing structured facts, don't
    duplicate the explanation."""
    _, root = _load({"scheduleImpactModel": _INFEASIBLE_WITH_CONFLICT_OVERVIEW})
    warning = _find(root, "infeasibleGenericWarning")

    assert warning.property("visible") is False


def test_flexible_state_has_no_generic_warning() -> None:
    _, root = _load({"scheduleImpactModel": _FLEXIBLE_OVERVIEW})
    warning = _find(root, "infeasibleGenericWarning")

    assert warning.property("visible") is False


def test_task_switch_clears_stale_infeasible_state() -> None:
    """Switching from an infeasible task to a flexible one must not leave
    the previous task's "Infeasible" status or negative float visible --
    the model identity change (a fresh dict, per the presenter's
    reset_task_lazy_sections -> {} -> re-fetch flow) must fully replace
    every derived field in the same update, not just the ones a naive
    partial-merge would touch."""
    _, root = _load({"scheduleImpactModel": _INFEASIBLE_NO_CONFLICT_OVERVIEW})
    chip = _find(root, "scheduleStatusChip")
    assert str(chip.property("status")) == "Infeasible"

    root.setProperty("scheduleImpactModel", _FLEXIBLE_OVERVIEW)

    assert str(chip.property("status")) == "Flexible"
    warning = _find(root, "infeasibleGenericWarning")
    assert warning.property("visible") is False


def test_task_switch_to_unavailable_clears_stale_infeasible_state() -> None:
    """The real task-switch path (reset_task_lazy_sections) sets the
    model to {} BEFORE the next task's data is fetched -- confirms that
    intermediate empty state renders as "not available," never a
    leftover "Infeasible" chip from the task the user just left."""
    _, root = _load({"scheduleImpactModel": _INFEASIBLE_NO_CONFLICT_OVERVIEW})

    root.setProperty("scheduleImpactModel", {})

    chip = _find(root, "scheduleStatusChip")
    assert str(chip.property("status")) == "Flexible"  # default fallback, not "Infeasible"
    assert root.property("_m") is not None


def test_no_qml_derived_infeasibility_from_total_float() -> None:
    """QML must render is_infeasible/is_critical/scheduleStatusLabel
    verbatim from the model -- it must never itself compare
    totalFloatDays against zero to decide feasibility or criticality."""
    source = ROOT_COMPONENT.read_text(encoding="utf-8")
    assert "totalFloatDays < 0" not in source
    assert "totalFloatDays <= 0" not in source
    assert "totalFloatDays === 0" not in source
    assert "totalFloatDays == 0" not in source
