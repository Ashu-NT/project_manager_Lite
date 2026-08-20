from __future__ import annotations

import logging
from time import perf_counter

from src.core.modules.project_management.api.desktop import (
    ProjectManagementSchedulingDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.scheduling import (
    SchedulingBaselineCompareViewModel,
    SchedulingCollectionViewModel,
    SchedulingSelectorOptionViewModel,
    SchedulingWorkspaceViewModel,
)

from .activity_feed_builder import build_activity_feed_collection
from .calendar_builder import build_calendar_view_model
from .diagnostics_builder import build_diagnostics_collection
from .formatters import (
    label_for_option,
)
from .option_resolver import (
    build_status_options,
    resolve_baseline_ids,
    resolve_project_id,
    resolve_selected_activity_id,
    resolve_selected_option,
)
from .overview_builder import build_overview
from .record_mappers import (
    to_baseline_compare_record,
    to_baseline_register_record,
    to_constraint_violation_record,
    to_delayed_activity_record,
    to_resource_load_record,
)
from .schedule_filter import matches_schedule_filters
from .schedule_sort import normalize_schedule_sort

logger = logging.getLogger(__name__)


def build_workspace_state(
    desktop_api: ProjectManagementSchedulingDesktopApi,
    *,
    project_id: str | None = None,
    selected_calendar_id: str | None = None,
    selected_baseline_id: str | None = None,
    selected_baseline_a_id: str | None = None,
    selected_baseline_b_id: str | None = None,
    selected_status_filter: str = "all",
    search_text: str = "",
    show_critical_only: bool = False,
    show_delayed_only: bool = False,
    sort_key: str = "schedule",
    sort_direction: str = "asc",
    selected_activity_id: str | None = None,
    include_unchanged: bool = False,
    activity_log: tuple[dict[str, str], ...] = (),
) -> SchedulingWorkspaceViewModel:
    started = perf_counter()

    project_options = tuple(
        SchedulingSelectorOptionViewModel(value=option.value, label=option.label)
        for option in desktop_api.list_projects()
    )
    resolved_project_id = resolve_project_id(project_id, project_options)

    calendar_options = tuple(
        SchedulingSelectorOptionViewModel(
            value=option.value,
            label=option.label,
            supporting_text=option.summary_label,
        )
        for option in desktop_api.list_calendars()
    )
    resolved_calendar_id = resolve_selected_option(
        selected_calendar_id,
        calendar_options,
        default_value="default",
    )
    calendar_snapshot = desktop_api.get_calendar_snapshot(resolved_calendar_id)

    baseline_options = (
        tuple(
            SchedulingSelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_baselines(resolved_project_id)
        )
        if resolved_project_id
        else ()
    )
    baseline_rows = (
        desktop_api.list_baseline_rows(resolved_project_id)
        if resolved_project_id
        else ()
    )
    requested_baseline_id = str(selected_baseline_id or "").strip()
    baseline_ids = {option.value for option in baseline_options}
    resolved_baseline_id = (
        requested_baseline_id if requested_baseline_id in baseline_ids else ""
    )
    gantt_projection = (
        desktop_api.build_gantt_projection(resolved_project_id)
        if resolved_project_id
        else None
    )
    schedule_items = (
        tuple(row for row in gantt_projection.rows if not row.is_summary)
        if gantt_projection is not None
        else ()
    )
    dependency_rows = (
        gantt_projection.dependency_edges
        if gantt_projection is not None
        else ()
    )
    resolved_baseline_a_id, resolved_baseline_b_id = resolve_baseline_ids(
        baseline_options=baseline_options,
        selected_baseline_a_id=selected_baseline_a_id,
        selected_baseline_b_id=selected_baseline_b_id,
    )

    normalized_search = (search_text or "").strip()
    status_options = build_status_options(schedule_items)
    resolved_status_filter = resolve_selected_option(
        selected_status_filter,
        status_options,
        default_value="all",
    )
    filtered_schedule = tuple(
        item
        for item in schedule_items
        if matches_schedule_filters(
            item,
            status_filter=resolved_status_filter,
            search_text=normalized_search,
            show_critical_only=show_critical_only,
            show_delayed_only=show_delayed_only,
        )
    )
    schedule_sort = normalize_schedule_sort(key=sort_key, direction=sort_direction)
    total_count = len(filtered_schedule)

    resolved_selected_activity_id = resolve_selected_activity_id(
        selected_activity_id,
        filtered_schedule=filtered_schedule,
    )
    comparison_rows = ()
    comparison_summary = ""
    comparison_empty_state = ""
    if (
        resolved_project_id
        and resolved_baseline_a_id
        and resolved_baseline_b_id
        and resolved_baseline_a_id != resolved_baseline_b_id
    ):
        comparison_rows = desktop_api.compare_baselines(
            project_id=resolved_project_id,
            baseline_a_id=resolved_baseline_a_id,
            baseline_b_id=resolved_baseline_b_id,
            include_unchanged=include_unchanged,
        )
        comparison_summary = (
            f"{label_for_option(resolved_baseline_a_id, baseline_options)} "
            f"vs {label_for_option(resolved_baseline_b_id, baseline_options)}"
        )
    if not baseline_options:
        comparison_empty_state = (
            "Create at least two baselines to compare schedule drift."
            if resolved_project_id
            else "Select a project to review baseline comparisons."
        )
    elif resolved_baseline_a_id == resolved_baseline_b_id:
        comparison_empty_state = "Choose two different baselines to compare."
    elif not comparison_rows:
        comparison_empty_state = "No baseline variance matches the current comparison."

    resource_load = (
        desktop_api.list_resource_load(resolved_project_id) if resolved_project_id else ()
    )
    constraint_violations = (
        desktop_api.list_constraint_violations(resolved_project_id)
        if resolved_project_id
        else ()
    )

    critical_items = tuple(item for item in filtered_schedule if item.is_critical)
    delayed_items = tuple(item for item in filtered_schedule if (item.late_by_days or 0) > 0)
    duration_ms = (perf_counter() - started) * 1000
    log_method = logger.warning if duration_ms > 500 else logger.info
    log_method(
        "PM scheduling presenter build complete duration_ms=%.1f project=%s "
        "schedule_count=%s filtered_count=%s dependency_count=%s baseline_count=%s "
        "resource_load_count=%s violation_count=%s search=%s status_filter=%s "
        "critical_only=%s delayed_only=%s",
        duration_ms,
        resolved_project_id,
        len(schedule_items),
        total_count,
        len(dependency_rows),
        len(baseline_options),
        len(resource_load),
        len(constraint_violations),
        normalized_search,
        resolved_status_filter,
        show_critical_only,
        show_delayed_only,
    )

    return SchedulingWorkspaceViewModel(
        overview=build_overview(
            resolved_project_id=resolved_project_id,
            schedule_items=schedule_items,
            filtered_schedule=filtered_schedule,
            critical_items=critical_items,
            delayed_items=delayed_items,
            dependency_rows=dependency_rows,
            baseline_rows=baseline_rows,
            calendar_snapshot=calendar_snapshot,
            resource_load=resource_load,
        ),
        project_options=project_options,
        calendar_options=calendar_options,
        baseline_options=baseline_options,
        status_options=status_options,
        selected_project_id=resolved_project_id,
        selected_calendar_id=resolved_calendar_id,
        selected_baseline_id=resolved_baseline_id,
        selected_status_filter=resolved_status_filter,
        search_text=normalized_search,
        show_critical_only=show_critical_only,
        show_delayed_only=show_delayed_only,
        sort_key=schedule_sort.key,
        sort_direction=schedule_sort.direction.value,
        selected_activity_id=resolved_selected_activity_id,
        gantt_projection=gantt_projection,
        calendar=build_calendar_view_model(calendar_snapshot),
        baselines=SchedulingBaselineCompareViewModel(
            options=baseline_options,
            selected_baseline_a_id=resolved_baseline_a_id,
            selected_baseline_b_id=resolved_baseline_b_id,
            include_unchanged=include_unchanged,
            summary_text=comparison_summary,
            rows=tuple(to_baseline_compare_record(row) for row in comparison_rows),
            empty_state=comparison_empty_state,
        ),
        diagnostics=build_diagnostics_collection(
            schedule_items=schedule_items,
            filtered_schedule=filtered_schedule,
            dependency_rows=dependency_rows,
            resource_load=resource_load,
        ),
        delayed_activities=SchedulingCollectionViewModel(
            title="Delayed Activities",
            subtitle="Activities already late against their current deadline logic.",
            items=tuple(to_delayed_activity_record(item) for item in delayed_items[:12]),
            empty_state=(
                "No delayed activities are visible for the current planning filter."
                if resolved_project_id
                else "Select a project to review delayed activities."
            ),
        ),
        resource_loading=SchedulingCollectionViewModel(
            title="Resource Loading",
            subtitle="Peak allocation pressure and overload risk.",
            items=tuple(to_resource_load_record(item) for item in resource_load[:12]),
            empty_state=(
                "No resource loading records are available for the selected project."
                if resolved_project_id
                else "Select a project to review resource loading."
            ),
        ),
        baseline_register=SchedulingCollectionViewModel(
            title="Baseline Register",
            subtitle="Stored schedule freezes available for comparison and governance.",
            items=tuple(to_baseline_register_record(row) for row in baseline_rows),
            empty_state=(
                "No baselines are stored for the selected project."
                if resolved_project_id
                else "Select a project to review baselines."
            ),
        ),
        constraint_violations=SchedulingCollectionViewModel(
            title="Constraint Violations",
            subtitle="Hard and soft date-constraint violations detected by the schedule validator.",
            items=tuple(
                to_constraint_violation_record(v) for v in constraint_violations
            ),
            empty_state=(
                "No constraint violations are detected for the current schedule."
                if resolved_project_id
                else "Select a project to run constraint validation."
            ),
        ),
        activity_feed=build_activity_feed_collection(
            schedule_items=schedule_items,
            delayed_items=delayed_items,
            resource_load=resource_load,
            activity_log=activity_log,
        ),
    )


__all__ = ["build_workspace_state"]
