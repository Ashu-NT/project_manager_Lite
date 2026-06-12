from __future__ import annotations

from .forecast_mapper import forecast_record
from .plan_detail_builder import build_plan_detail
from .queue_mapper import queue_record


def build_queue_empty_state(
    *,
    queue_rows_all,
    filtered_queue_rows,
    queue_search_text: str,
    queue_site_filter: str,
    queue_due_state_filter: str,
) -> str:
    if filtered_queue_rows:
        return ""
    if not queue_rows_all:
        return "No preventive plans are currently queued for review."
    if queue_search_text or queue_site_filter != "all" or queue_due_state_filter != "all":
        return "No queued preventive plans match the current filters."
    return "No preventive plans are currently queued for review."


def build_queue_state(
    *,
    site_filter_options,
    due_state_options,
    normalized_queue_site_filter: str,
    normalized_queue_due_state_filter: str,
    normalized_queue_search: str,
    queue_rows_all,
    filtered_queue_rows,
    resolved_queue_plan_id: str,
    selected_queue_plan_detail,
    selected_queue_plan,
    forecast_rows,
    generation_result_rows,
) -> dict[str, object]:
    return {
        "siteOptions": site_filter_options,
        "dueStateOptions": due_state_options,
        "selectedSiteFilter": normalized_queue_site_filter,
        "selectedDueStateFilter": normalized_queue_due_state_filter,
        "searchText": normalized_queue_search,
        "plans": {
            "title": "Generation Queue",
            "subtitle": "Due, due-soon, blocked, and inactive preventive plans ready for review and work generation.",
            "emptyState": build_queue_empty_state(
                queue_rows_all=queue_rows_all,
                filtered_queue_rows=filtered_queue_rows,
                queue_search_text=normalized_queue_search,
                queue_site_filter=normalized_queue_site_filter,
                queue_due_state_filter=normalized_queue_due_state_filter,
            ),
            "items": [queue_record(row) for row in filtered_queue_rows],
        },
        "selectedPlanId": resolved_queue_plan_id,
        "selectedPlan": build_plan_detail(
            selected_queue_plan_detail,
            empty_state="Select a preventive plan to preview upcoming due instances and work-generation readiness.",
            queue_row=selected_queue_plan,
        ),
        "forecastRows": {
            "title": "Forecast",
            "subtitle": "Preview generation windows, planner state, and instance outcomes for the selected plan.",
            "emptyState": "Select a preventive plan to preview the generated schedule horizon.",
            "items": [forecast_record(row) for row in forecast_rows],
        },
        "generationResults": {
            "title": "Latest generation results",
            "subtitle": "Review work requests or work orders created by the most recent generation run.",
            "emptyState": "Generate due work to review the created records here.",
            "items": list(generation_result_rows),
        },
    }
