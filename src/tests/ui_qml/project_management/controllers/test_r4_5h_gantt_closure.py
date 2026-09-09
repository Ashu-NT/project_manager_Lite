from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PM_UI = ROOT / "ui_qml" / "modules" / "project_management"
SCHEDULING_QML = PM_UI / "qml" / "workspaces" / "scheduling"
GANTT_QML = SCHEDULING_QML / "components" / "gantt"
SCHEDULING_CONTROLLER = PM_UI / "controllers" / "scheduling"
SCHEDULING_PRESENTER = PM_UI / "presenters" / "scheduling"
TYPEINFO = PM_UI / "qml" / "ProjectManagement" / "Controllers" / "typeinfo"
GANTT_DTOS = (
    ROOT
    / "core"
    / "modules"
    / "project_management"
    / "api"
    / "desktop"
    / "scheduling"
    / "models"
    / "gantt.py"
)


def _source_files(path: Path, patterns: tuple[str, ...]) -> list[Path]:
    return [file for pattern in patterns for file in path.rglob(pattern)]


def _joined_source(files: list[Path]) -> str:
    return "\n".join(file.read_text(encoding="utf-8") for file in files)


def test_final_gantt_qmldir_has_only_the_live_component_tree() -> None:
    expected_components = {
        "SchedulingGanttSurface.qml",
        "SchedulingGanttHeader.qml",
        "SchedulingGanttRowsViewport.qml",
        "SchedulingGanttRow.qml",
        "SchedulingGanttBar.qml",
        "SchedulingGanttBaseline.qml",
        "SchedulingGanttDependencyLayer.qml",
    }
    actual_components = {file.name for file in GANTT_QML.glob("*.qml")}
    registrations = {
        line.split()[-1]
        for line in (GANTT_QML / "qmldir").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("module ")
    }

    assert actual_components == expected_components
    assert registrations == expected_components
    assert (GANTT_QML / "GanttGeometry.js").is_file()


def test_final_gantt_has_one_viewport_and_one_dependency_renderer() -> None:
    qml_files = list(GANTT_QML.glob("*.qml"))
    source = _joined_source(qml_files)

    assert source.count("ListView {") == 1
    assert source.count("Canvas {") == 1
    assert "Shape {" not in source
    assert "id: rowsList" in (GANTT_QML / "SchedulingGanttRowsViewport.qml").read_text(
        encoding="utf-8"
    )
    assert "id: dependencyCanvas" in (
        GANTT_QML / "SchedulingGanttDependencyLayer.qml"
    ).read_text(encoding="utf-8")


def test_legacy_gantt_and_duplicate_scheduling_surfaces_are_absent() -> None:
    production_files = _source_files(
        SCHEDULING_QML, ("*.qml", "*.js")
    ) + _source_files(SCHEDULING_CONTROLLER, ("*.py",)) + _source_files(
        SCHEDULING_PRESENTER, ("*.py",)
    )
    source = _joined_source(production_files)

    forbidden = (
        "SchedulingTimelinePanel",
        "gantt_legacy_adapter",
        "baselinePlaceholder",
        "selectedActivityDetail",
        "dependencyTypeOptions",
        "dependencyTaskOptions",
        "setActivityPage",
        "createDependency",
        "updateDependency",
        "deleteDependency",
    )
    for marker in forbidden:
        assert marker not in source

    assert not (SCHEDULING_PRESENTER / "detail_builder.py").exists()
    assert "Compatibility alias" not in GANTT_DTOS.read_text(encoding="utf-8")
    assert "activityPage" not in (TYPEINFO / "scheduling.fragment").read_text(
        encoding="utf-8"
    )


def test_gantt_selection_and_date_geometry_remain_centralized() -> None:
    model_source = (SCHEDULING_CONTROLLER / "gantt_list_model.py").read_text(
        encoding="utf-8"
    )
    controller_source = (
        SCHEDULING_CONTROLLER / "scheduling_workspace_controller.py"
    ).read_text(encoding="utf-8")
    geometry_source = (GANTT_QML / "GanttGeometry.js").read_text(encoding="utf-8")
    qml_source = _joined_source(list(GANTT_QML.glob("*.qml")))

    assert "self._selected_activity_id" in controller_source
    assert "selectedActivityId" in controller_source
    assert "def set_projection(" in model_source
    assert "function dayStartX(" in geometry_source
    assert "function taskWidth(" in geometry_source
    assert "function taskFinishX(" in geometry_source
    assert "(startDay - rangeStart" not in qml_source
    assert "startDay === finishDay" not in qml_source
