from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_scheduling_baselines_view_model,
    serialize_scheduling_calendar_view_model,
    serialize_scheduling_collection_view_model,
)

from .row_builders import (
    build_baseline_compare_rows,
    build_baseline_register_rows,
    build_calendar_summary_rows,
    build_constraint_rows,
    build_delayed_rows,
    build_dependency_rows,
    build_diagnostics_rows,
    build_holiday_rows,
    build_resource_rows,
    build_schedule_rows,
    build_violation_rows,
)


def serialize_workspace_panels(workspace_state) -> dict[str, dict[str, object]]:
    return {
        "calendar": serialize_scheduling_calendar_view_model(workspace_state.calendar),
        "baselines": serialize_scheduling_baselines_view_model(workspace_state.baselines),
        "schedule": serialize_scheduling_collection_view_model(workspace_state.schedule),
        "timeline": serialize_scheduling_collection_view_model(workspace_state.timeline),
        "critical_path": serialize_scheduling_collection_view_model(workspace_state.critical_path),
        "diagnostics": serialize_scheduling_collection_view_model(workspace_state.diagnostics),
        "delayed": serialize_scheduling_collection_view_model(workspace_state.delayed_activities),
        "resource_loading": serialize_scheduling_collection_view_model(workspace_state.resource_loading),
        "baseline_register": serialize_scheduling_collection_view_model(workspace_state.baseline_register),
        "dependencies": serialize_scheduling_collection_view_model(workspace_state.dependencies),
        "constraints": serialize_scheduling_collection_view_model(workspace_state.constraints),
        "constraint_violations": serialize_scheduling_collection_view_model(workspace_state.constraint_violations),
        "activity_feed": serialize_scheduling_collection_view_model(workspace_state.activity_feed),
    }


def hydrate_visible_panel_models(
    controller,
    panels: dict[str, dict[str, object]],
) -> None:
    detail_active = bool(controller._selected_activity_id)
    panel_id = controller._active_panel_id

    controller._set_calendar(panels["calendar"])
    controller._set_baselines(panels["baselines"])
    controller._set_schedule(panels["schedule"])
    controller._set_timeline(panels["timeline"])
    controller._set_critical_path(panels["critical_path"])
    controller._set_diagnostics(panels["diagnostics"])
    controller._set_delayed_activities(panels["delayed"])
    controller._set_resource_loading(panels["resource_loading"])
    controller._set_baseline_register(panels["baseline_register"])
    controller._set_dependencies(panels["dependencies"])
    controller._set_constraints(panels["constraints"])
    controller._set_constraint_violations(panels["constraint_violations"])
    controller._set_activity_feed(panels["activity_feed"])

    if panel_id == "activity_timeline":
        controller._set_schedule_rows(build_schedule_rows(panels["schedule"]))

    if panel_id == "diagnostics":
        controller._set_diagnostics_rows(build_diagnostics_rows(panels["diagnostics"]))
        controller._set_violation_rows(build_violation_rows(panels["constraint_violations"]))

    if panel_id == "delays":
        controller._set_delayed_activity_rows(build_delayed_rows(panels["delayed"]))

    if panel_id == "resources" or detail_active:
        controller._set_resource_loading_rows(build_resource_rows(panels["resource_loading"]))

    if panel_id == "baselines" or detail_active:
        controller._set_baseline_compare_rows(build_baseline_compare_rows(panels["baselines"]))
        controller._set_baseline_register_rows(
            build_baseline_register_rows(panels["baseline_register"])
        )

    if panel_id == "calendars" or detail_active:
        controller._set_calendar_summary_rows(build_calendar_summary_rows(panels["calendar"]))
        controller._set_holiday_rows(build_holiday_rows(panels["calendar"]))

    if detail_active:
        controller._set_dependency_rows(build_dependency_rows(panels["dependencies"]))
        controller._set_constraint_rows(build_constraint_rows(panels["constraints"]))


__all__ = ["hydrate_visible_panel_models", "serialize_workspace_panels"]
