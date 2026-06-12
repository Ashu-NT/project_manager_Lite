from __future__ import annotations

import logging
from time import perf_counter

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_scheduling_detail_view_model,
    serialize_scheduling_overview_view_model,
    serialize_selector_options,
    serialize_workspace_view_model,
)

from .panel_hydrator import hydrate_visible_panel_models, serialize_workspace_panels
from .scheduling_property_updates import (
    set_activity_page,
    set_activity_page_size,
    set_activity_total_count,
    set_baseline_options,
    set_calendar_options,
    set_dependency_task_options,
    set_dependency_type_options,
    set_overview,
    set_project_options,
    set_search_text,
    set_selected_activity,
    set_selected_activity_id,
    set_selected_baseline_id,
    set_selected_calendar_id,
    set_selected_project_id,
    set_selected_status_filter,
    set_show_critical_only,
    set_show_delayed_only,
    set_status_options,
)

logger = logging.getLogger(__name__)


def load_workspace_state(controller) -> None:
    started = perf_counter()
    logger.info(
        "PM scheduling refresh begin project=%s calendar=%s baseline=%s panel=%s "
        "status_filter=%s search=%s page=%s page_size=%s critical_only=%s delayed_only=%s",
        controller._selected_project_id, controller._selected_calendar_id,
        controller._selected_baseline_id, controller._active_panel_id,
        controller._selected_status_filter, controller._search_text,
        controller._activity_page, controller._activity_page_size,
        controller._show_critical_only, controller._show_delayed_only,
    )
    controller._set_is_loading(True)
    success = False
    try:
        controller._set_error_message("")
        controller._set_feedback_message("")
        controller._set_workspace(
            serialize_workspace_view_model(controller._workspace_presenter.build_view_model())
        )
        ws = controller._scheduling_workspace_presenter.build_workspace_state(
            project_id=controller._selected_project_id or None,
            selected_calendar_id=controller._selected_calendar_id or None,
            selected_baseline_id=controller._selected_baseline_id or None,
            selected_baseline_a_id=controller._baselines.get("selectedBaselineAId") or None,
            selected_baseline_b_id=controller._baselines.get("selectedBaselineBId") or None,
            selected_status_filter=controller._selected_status_filter,
            search_text=controller._search_text,
            show_critical_only=controller._show_critical_only,
            show_delayed_only=controller._show_delayed_only,
            page=controller._activity_page,
            page_size=controller._activity_page_size,
            selected_activity_id=controller._selected_activity_id or None,
            include_unchanged=bool(controller._baselines.get("includeUnchanged", False)),
            activity_log=tuple(controller._activity_log_svc.log),
        )
        set_overview(controller, serialize_scheduling_overview_view_model(ws.overview))
        set_project_options(controller, serialize_selector_options(ws.project_options))
        set_calendar_options(controller, serialize_selector_options(ws.calendar_options))
        set_baseline_options(controller, serialize_selector_options(ws.baseline_options))
        set_dependency_type_options(
            controller, serialize_selector_options(ws.dependency_type_options)
        )
        set_dependency_task_options(
            controller, serialize_selector_options(ws.dependency_task_options)
        )
        set_status_options(controller, serialize_selector_options(ws.status_options))
        set_selected_project_id(controller, ws.selected_project_id)
        set_selected_calendar_id(controller, ws.selected_calendar_id)
        set_selected_baseline_id(controller, ws.selected_baseline_id)
        set_selected_status_filter(controller, ws.selected_status_filter)
        set_search_text(controller, ws.search_text)
        set_show_critical_only(controller, ws.show_critical_only)
        set_show_delayed_only(controller, ws.show_delayed_only)
        set_activity_page(controller, ws.page)
        set_activity_page_size(controller, ws.page_size)
        set_activity_total_count(controller, ws.total_count)
        set_selected_activity_id(controller, ws.selected_activity_id)
        panels = serialize_workspace_panels(ws)
        hydrate_visible_panel_models(controller, panels)
        set_selected_activity(
            controller,
            serialize_scheduling_detail_view_model(ws.selected_activity_detail),
        )
        controller._set_empty_state(
            ws.schedule.empty_state or ws.selected_activity_detail.empty_state
        )
        success = True
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.exception("PM scheduling refresh failed")
        controller._set_error_message(str(exc))
    finally:
        duration_ms = (perf_counter() - started) * 1000
        log_method = logger.warning if duration_ms > 500 else logger.info
        log_method(
            "PM scheduling refresh complete success=%s duration_ms=%.1f project=%s panel=%s "
            "schedule_rows=%s total_count=%s diagnostics_rows=%s delayed_rows=%s resource_rows=%s",
            success, duration_ms, controller._selected_project_id, controller._active_panel_id,
            len(controller._schedule.get("items", []) or []),
            controller._activity_total_count,
            len(controller._diagnostics.get("items", []) or []),
            len(controller._delayed_activities.get("items", []) or []),
            len(controller._resource_loading.get("items", []) or []),
        )
        controller._set_is_loading(False)


__all__ = ["load_workspace_state"]
