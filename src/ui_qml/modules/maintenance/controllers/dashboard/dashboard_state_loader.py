from __future__ import annotations

from src.ui_qml.modules.maintenance.controllers.common import (
    serialize_dashboard_workspace_state,
    serialize_workspace_view_model,
)

from .dashboard_helpers import int_filter, normalized_filter
from .dashboard_property_updates import (
    set_asset_options,
    set_backlog_rows,
    set_location_options,
    set_overview,
    set_recurring_rows,
    set_root_cause_rows,
    set_selected_asset_filter,
    set_selected_days_filter,
    set_selected_location_filter,
    set_selected_site_filter,
    set_selected_system_filter,
    set_site_options,
    set_system_options,
    set_window_options,
)


def load_workspace_state(controller) -> None:
    controller._set_is_loading(True)
    try:
        controller._set_error_message("")
        controller._set_feedback_message("")
        controller._set_workspace(
            serialize_workspace_view_model(
                controller._workspace_presenter.build_view_model()
            )
        )
        state = serialize_dashboard_workspace_state(
            controller._dashboard_workspace_presenter.build_workspace_state(
                site_id=normalized_filter(controller._selected_site_filter),
                asset_id=normalized_filter(controller._selected_asset_filter),
                system_id=normalized_filter(controller._selected_system_filter),
                location_id=normalized_filter(controller._selected_location_filter),
                days=int_filter(controller._selected_days_filter, 90),
            )
        )
        set_overview(controller, state["overview"])
        set_site_options(controller, state["siteOptions"])
        set_asset_options(controller, state["assetOptions"])
        set_system_options(controller, state["systemOptions"])
        set_location_options(controller, state["locationOptions"])
        set_window_options(controller, state["windowOptions"])
        set_selected_site_filter(controller, str(state["selectedSiteFilter"]))
        set_selected_asset_filter(controller, str(state["selectedAssetFilter"]))
        set_selected_system_filter(controller, str(state["selectedSystemFilter"]))
        set_selected_location_filter(controller, str(state["selectedLocationFilter"]))
        set_selected_days_filter(controller, str(state["selectedDaysFilter"]))
        set_backlog_rows(controller, state["backlogRows"])
        set_root_cause_rows(controller, state["rootCauseRows"])
        set_recurring_rows(controller, state["recurringRows"])
        controller._set_empty_state(str(state["emptyState"]))
    except Exception as exc:  # pragma: no cover - defensive fallback
        controller._set_error_message(str(exc))
    finally:
        controller._set_is_loading(False)
