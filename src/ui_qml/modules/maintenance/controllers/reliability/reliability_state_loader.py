from __future__ import annotations

from src.ui_qml.modules.maintenance.controllers.common import (
    serialize_reliability_workspace_state,
    serialize_workspace_view_model,
)

from .reliability_helpers import int_filter, normalized_filter
from .reliability_property_updates import (
    set_asset_options,
    set_days_options,
    set_failure_symptom_options,
    set_limit_options,
    set_location_options,
    set_overview,
    set_recurring_rows,
    set_root_cause_rows,
    set_selected_asset_filter,
    set_selected_days_filter,
    set_selected_failure_code_filter,
    set_selected_limit_filter,
    set_selected_location_filter,
    set_selected_site_filter,
    set_selected_system_filter,
    set_selected_threshold_filter,
    set_site_options,
    set_suggestion_rows,
    set_system_options,
    set_threshold_options,
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
        state = serialize_reliability_workspace_state(
            controller._reliability_workspace_presenter.build_workspace_state(
                site_id=normalized_filter(controller._selected_site_filter),
                asset_id=normalized_filter(controller._selected_asset_filter),
                system_id=normalized_filter(controller._selected_system_filter),
                location_id=normalized_filter(controller._selected_location_filter),
                failure_code=normalized_filter(controller._selected_failure_code_filter),
                days=int_filter(controller._selected_days_filter, 90),
                limit=int_filter(controller._selected_limit_filter, 20),
                threshold=int_filter(controller._selected_threshold_filter, 2),
            )
        )
        set_overview(controller, state["overview"])
        set_site_options(controller, state["siteOptions"])
        set_asset_options(controller, state["assetOptions"])
        set_system_options(controller, state["systemOptions"])
        set_location_options(controller, state["locationOptions"])
        set_failure_symptom_options(controller, state["failureSymptomOptions"])
        set_days_options(controller, state["daysOptions"])
        set_limit_options(controller, state["limitOptions"])
        set_threshold_options(controller, state["thresholdOptions"])
        set_selected_site_filter(controller, str(state["selectedSiteFilter"]))
        set_selected_asset_filter(controller, str(state["selectedAssetFilter"]))
        set_selected_system_filter(controller, str(state["selectedSystemFilter"]))
        set_selected_location_filter(controller, str(state["selectedLocationFilter"]))
        set_selected_failure_code_filter(
            controller, str(state["selectedFailureCodeFilter"])
        )
        set_selected_days_filter(controller, str(state["selectedDaysFilter"]))
        set_selected_limit_filter(controller, str(state["selectedLimitFilter"]))
        set_selected_threshold_filter(controller, str(state["selectedThresholdFilter"]))
        set_suggestion_rows(controller, state["suggestionRows"])
        set_root_cause_rows(controller, state["rootCauseRows"])
        set_recurring_rows(controller, state["recurringRows"])
        controller._set_empty_state(str(state["emptyState"]))
    except Exception as exc:  # pragma: no cover - defensive fallback
        controller._set_error_message(str(exc))
    finally:
        controller._set_is_loading(False)
