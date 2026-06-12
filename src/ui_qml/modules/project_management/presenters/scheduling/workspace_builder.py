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
from .detail_builder import build_constraints_collection, build_detail_view_model
from .diagnostics_builder import build_diagnostics_collection
from .formatters import (
    build_schedule_empty_state,
    calendar_label as get_calendar_label,
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
    to_critical_path_record,
    to_delayed_activity_record,
    to_dependency_record,
    to_resource_load_record,
    to_schedule_record,
    to_timeline_record,
)
from .schedule_filter import matches_schedule_filters

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
    page: int = 1,
    page_size: int = 25,
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
    calendar_snapshot = desktop_api.get_calendar_snapshot()

    schedule_items = (
        desktop_api.list_schedule(resolved_project_id) if resolved_project_id else ()
    )
    dependency_rows = (
        desktop_api.list_project_dependencies(resolved_project_id)
        if resolved_project_id
        else ()
    )
    dependency_type_options = tuple(
        SchedulingSelectorOptionViewModel(value=option.value, label=option.label)
        for option in desktop_api.list_dependency_types()
    )
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
    resolved_baseline_id = resolve_selected_option(
        selected_baseline_id,
        baseline_options,
        default_value="",
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
    total_count = len(filtered_schedule)
    resolved_page_size = max(10, int(page_size or 25))
    resolved_page = max(1, int(page or 1))
    total_pages = max(1, (total_count + resolved_page_size - 1) // resolved_page_size)
    if resolved_page > total_pages:
        resolved_page = total_pages
    page_start = (resolved_page - 1) * resolved_page_size
    page_end = page_start + resolved_page_size
    paged_schedule = filtered_schedule[page_start:page_end]

    resolved_selected_activity_id = resolve_selected_activity_id(
        selected_activity_id,
        filtered_schedule=filtered_schedule,
        paged_schedule=paged_schedule,
    )
    selected_activity = next(
        (item for item in filtered_schedule if item.id == resolved_selected_activity_id),
        None,
    )
    dependency_task_options = (
        tuple(
            SchedulingSelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_activity_options(
                resolved_project_id,
                exclude_task_id=resolved_selected_activity_id,
            )
        )
        if resolved_project_id and resolved_selected_activity_id
        else ()
    )
    activity_dependencies = (
        desktop_api.list_dependencies(resolved_selected_activity_id)
        if resolved_selected_activity_id
        else ()
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
        "schedule_count=%s filtered_count=%s paged_count=%s dependency_count=%s "
        "baseline_count=%s resource_load_count=%s violation_count=%s page=%s "
        "page_size=%s search=%s status_filter=%s critical_only=%s delayed_only=%s",
        duration_ms,
        resolved_project_id,
        len(schedule_items),
        total_count,
        len(paged_schedule),
        len(dependency_rows),
        len(baseline_options),
        len(resource_load),
        len(constraint_violations),
        resolved_page,
        resolved_page_size,
        normalized_search,
        resolved_status_filter,
        show_critical_only,
        show_delayed_only,
    )

    cal_label = get_calendar_label(calendar_options, resolved_calendar_id)
    empty_state = build_schedule_empty_state(
        resolved_project_id=resolved_project_id,
        schedule_items=filtered_schedule,
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
        dependency_type_options=dependency_type_options,
        dependency_task_options=dependency_task_options,
        status_options=status_options,
        selected_project_id=resolved_project_id,
        selected_calendar_id=resolved_calendar_id,
        selected_baseline_id=resolved_baseline_id,
        selected_status_filter=resolved_status_filter,
        search_text=normalized_search,
        show_critical_only=show_critical_only,
        show_delayed_only=show_delayed_only,
        page=resolved_page,
        page_size=resolved_page_size,
        total_count=total_count,
        selected_activity_id=resolved_selected_activity_id,
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
        schedule=SchedulingCollectionViewModel(
            title="Activities",
            subtitle="Current planning window with CPM, float, constraint, and progress context.",
            items=tuple(
                to_schedule_record(
                    item,
                    row_index=page_start + index,
                    calendar_label=cal_label,
                )
                for index, item in enumerate(paged_schedule, start=1)
            ),
            empty_state=empty_state,
        ),
        timeline=SchedulingCollectionViewModel(
            title="Timeline",
            subtitle="Current schedule bars, milestone markers, and baseline-ready planner lane.",
            items=tuple(
                to_timeline_record(item, timeline_items=paged_schedule)
                for item in paged_schedule
            ),
            empty_state=empty_state,
        ),
        critical_path=SchedulingCollectionViewModel(
            title="Critical Path",
            subtitle="Zero-float activities driving the current finish date.",
            items=tuple(to_critical_path_record(item) for item in critical_items[:12]),
            empty_state=(
                "No critical-path activities are available for the current filter."
                if resolved_project_id
                else "Select a project to review the critical path."
            ),
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
        dependencies=SchedulingCollectionViewModel(
            title="Dependencies",
            subtitle="Sequencing links for the selected activity.",
            items=tuple(to_dependency_record(row) for row in activity_dependencies),
            empty_state=(
                "No dependencies are linked to the selected activity."
                if resolved_selected_activity_id
                else "Select an activity to review dependency logic."
            ),
        ),
        constraints=build_constraints_collection(selected_activity),
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
        selected_activity_detail=build_detail_view_model(
            selected_activity=selected_activity,
            calendar_label=cal_label,
            dependency_rows=activity_dependencies,
            resource_load=resource_load,
            baseline_rows=baseline_rows,
        ),
    )


__all__ = ["build_workspace_state"]
