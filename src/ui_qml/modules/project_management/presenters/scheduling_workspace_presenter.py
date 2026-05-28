from __future__ import annotations

from datetime import date
from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementSchedulingDesktopApi,
    SchedulingBaselineApproveCommand,
    SchedulingBaselineCreateCommand,
    SchedulingBaselineRejectCommand,
    SchedulingBaselineSubmitCommand,
    SchedulingCalendarUpdateCommand,
    SchedulingConstraintViolationDto,
    SchedulingDependencyCreateCommand,
    SchedulingDependencyUpdateCommand,
    SchedulingHolidayCreateCommand,
    SchedulingWorkingDayCalculationCommand,
    build_project_management_scheduling_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.scheduling import (
    SchedulingBaselineCompareViewModel,
    SchedulingCalendarViewModel,
    SchedulingCollectionViewModel,
    SchedulingDayOptionViewModel,
    SchedulingDetailFieldViewModel,
    SchedulingDetailViewModel,
    SchedulingMetricViewModel,
    SchedulingOverviewViewModel,
    SchedulingRecordViewModel,
    SchedulingSelectorOptionViewModel,
    SchedulingWorkspaceViewModel,
)


class ProjectSchedulingWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementSchedulingDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_scheduling_desktop_api()

    def build_workspace_state(
        self,
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
        project_options = tuple(
            SchedulingSelectorOptionViewModel(value=option.value, label=option.label)
            for option in self._desktop_api.list_projects()
        )
        resolved_project_id = self._resolve_project_id(project_id, project_options)

        calendar_options = tuple(
            SchedulingSelectorOptionViewModel(
                value=option.value,
                label=option.label,
                supporting_text=option.summary_label,
            )
            for option in self._desktop_api.list_calendars()
        )
        resolved_calendar_id = self._resolve_selected_option(
            selected_calendar_id,
            calendar_options,
            default_value="default",
        )
        calendar_snapshot = self._desktop_api.get_calendar_snapshot()

        schedule_items = (
            self._desktop_api.list_schedule(resolved_project_id)
            if resolved_project_id
            else ()
        )
        dependency_rows = (
            self._desktop_api.list_project_dependencies(resolved_project_id)
            if resolved_project_id
            else ()
        )
        dependency_type_options = tuple(
            SchedulingSelectorOptionViewModel(value=option.value, label=option.label)
            for option in self._desktop_api.list_dependency_types()
        )
        baseline_options = (
            tuple(
                SchedulingSelectorOptionViewModel(value=option.value, label=option.label)
                for option in self._desktop_api.list_baselines(resolved_project_id)
            )
            if resolved_project_id
            else ()
        )
        baseline_rows = (
            self._desktop_api.list_baseline_rows(resolved_project_id)
            if resolved_project_id
            else ()
        )
        resolved_baseline_id = self._resolve_selected_option(
            selected_baseline_id,
            baseline_options,
            default_value="",
        )
        resolved_baseline_a_id, resolved_baseline_b_id = self._resolve_baseline_ids(
            baseline_options=baseline_options,
            selected_baseline_a_id=selected_baseline_a_id,
            selected_baseline_b_id=selected_baseline_b_id,
        )

        normalized_search = (search_text or "").strip()
        status_options = self._build_status_options(schedule_items)
        resolved_status_filter = self._resolve_selected_option(
            selected_status_filter,
            status_options,
            default_value="all",
        )
        filtered_schedule = tuple(
            item
            for index, item in enumerate(schedule_items, start=1)
            if self._matches_schedule_filters(
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

        resolved_selected_activity_id = self._resolve_selected_activity_id(
            selected_activity_id,
            filtered_schedule=filtered_schedule,
            paged_schedule=paged_schedule,
        )
        selected_activity = next(
            (
                item
                for item in filtered_schedule
                if item.id == resolved_selected_activity_id
            ),
            None,
        )
        dependency_task_options = (
            tuple(
                SchedulingSelectorOptionViewModel(value=option.value, label=option.label)
                for option in self._desktop_api.list_activity_options(
                    resolved_project_id,
                    exclude_task_id=resolved_selected_activity_id,
                )
            )
            if resolved_project_id and resolved_selected_activity_id
            else ()
        )
        activity_dependencies = (
            self._desktop_api.list_dependencies(resolved_selected_activity_id)
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
            comparison_rows = self._desktop_api.compare_baselines(
                project_id=resolved_project_id,
                baseline_a_id=resolved_baseline_a_id,
                baseline_b_id=resolved_baseline_b_id,
                include_unchanged=include_unchanged,
            )
            comparison_summary = (
                f"{self._label_for_option(resolved_baseline_a_id, baseline_options)} "
                f"vs {self._label_for_option(resolved_baseline_b_id, baseline_options)}"
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
            self._desktop_api.list_resource_load(resolved_project_id)
            if resolved_project_id
            else ()
        )
        constraint_violations = (
            self._desktop_api.list_constraint_violations(resolved_project_id)
            if resolved_project_id
            else ()
        )

        critical_items = tuple(item for item in filtered_schedule if item.is_critical)
        delayed_items = tuple(item for item in filtered_schedule if (item.late_by_days or 0) > 0)

        return SchedulingWorkspaceViewModel(
            overview=self._build_overview(
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
            calendar=self._build_calendar_view_model(calendar_snapshot),
            baselines=SchedulingBaselineCompareViewModel(
                options=baseline_options,
                selected_baseline_a_id=resolved_baseline_a_id,
                selected_baseline_b_id=resolved_baseline_b_id,
                include_unchanged=include_unchanged,
                summary_text=comparison_summary,
                rows=tuple(
                    self._to_baseline_compare_record_view_model(row)
                    for row in comparison_rows
                ),
                empty_state=comparison_empty_state,
            ),
            schedule=SchedulingCollectionViewModel(
                title="Activities",
                subtitle="Current planning window with CPM, float, constraint, and progress context.",
                items=tuple(
                    self._to_schedule_record_view_model(
                        item,
                        row_index=page_start + index,
                        calendar_label=self._calendar_label(calendar_options, resolved_calendar_id),
                    )
                    for index, item in enumerate(paged_schedule, start=1)
                ),
                empty_state=self._build_schedule_empty_state(
                    resolved_project_id=resolved_project_id,
                    schedule_items=filtered_schedule,
                ),
            ),
            timeline=SchedulingCollectionViewModel(
                title="Timeline",
                subtitle="Current schedule bars, milestone markers, and baseline-ready planner lane.",
                items=tuple(
                    self._to_timeline_record_view_model(
                        item,
                        timeline_items=paged_schedule,
                    )
                    for item in paged_schedule
                ),
                empty_state=self._build_schedule_empty_state(
                    resolved_project_id=resolved_project_id,
                    schedule_items=filtered_schedule,
                ),
            ),
            critical_path=SchedulingCollectionViewModel(
                title="Critical Path",
                subtitle="Zero-float activities driving the current finish date.",
                items=tuple(
                    self._to_critical_path_record_view_model(item)
                    for item in critical_items[:12]
                ),
                empty_state=(
                    "No critical-path activities are available for the current filter."
                    if resolved_project_id
                    else "Select a project to review the critical path."
                ),
            ),
            diagnostics=self._build_diagnostics_collection(
                schedule_items=schedule_items,
                filtered_schedule=filtered_schedule,
                dependency_rows=dependency_rows,
                resource_load=resource_load,
            ),
            delayed_activities=SchedulingCollectionViewModel(
                title="Delayed Activities",
                subtitle="Activities already late against their current deadline logic.",
                items=tuple(
                    self._to_delayed_activity_record_view_model(item)
                    for item in delayed_items[:12]
                ),
                empty_state=(
                    "No delayed activities are visible for the current planning filter."
                    if resolved_project_id
                    else "Select a project to review delayed activities."
                ),
            ),
            resource_loading=SchedulingCollectionViewModel(
                title="Resource Loading",
                subtitle="Peak allocation pressure and overload risk.",
                items=tuple(
                    self._to_resource_load_record_view_model(item)
                    for item in resource_load[:12]
                ),
                empty_state=(
                    "No resource loading records are available for the selected project."
                    if resolved_project_id
                    else "Select a project to review resource loading."
                ),
            ),
            baseline_register=SchedulingCollectionViewModel(
                title="Baseline Register",
                subtitle="Stored schedule freezes available for comparison and governance.",
                items=tuple(
                    self._to_baseline_register_record_view_model(row)
                    for row in baseline_rows
                ),
                empty_state=(
                    "No baselines are stored for the selected project."
                    if resolved_project_id
                    else "Select a project to review baselines."
                ),
            ),
            dependencies=SchedulingCollectionViewModel(
                title="Dependencies",
                subtitle="Sequencing links for the selected activity.",
                items=tuple(
                    self._to_dependency_record_view_model(row)
                    for row in activity_dependencies
                ),
                empty_state=(
                    "No dependencies are linked to the selected activity."
                    if resolved_selected_activity_id
                    else "Select an activity to review dependency logic."
                ),
            ),
            constraints=self._build_constraints_collection(selected_activity),
            constraint_violations=SchedulingCollectionViewModel(
                title="Constraint Violations",
                subtitle="Hard and soft date-constraint violations detected by the schedule validator.",
                items=tuple(
                    self._to_constraint_violation_record_view_model(v)
                    for v in constraint_violations
                ),
                empty_state=(
                    "No constraint violations are detected for the current schedule."
                    if resolved_project_id
                    else "Select a project to run constraint validation."
                ),
            ),
            activity_feed=self._build_activity_feed_collection(
                schedule_items=schedule_items,
                delayed_items=delayed_items,
                resource_load=resource_load,
                activity_log=activity_log,
            ),
            selected_activity_detail=self._build_detail_view_model(
                selected_activity=selected_activity,
                calendar_label=self._calendar_label(calendar_options, resolved_calendar_id),
                dependency_rows=activity_dependencies,
                resource_load=resource_load,
                baseline_rows=baseline_rows,
            ),
        )

    def save_calendar(self, payload: dict[str, Any]) -> None:
        working_days = tuple(
            int(value)
            for value in payload.get("workingDays", [])
            if str(value).strip() != ""
        )
        hours_per_day = self._require_float(
            payload,
            "hoursPerDay",
            "Hours per day must be a positive number.",
        )
        self._desktop_api.update_calendar(
            SchedulingCalendarUpdateCommand(
                working_days=working_days,
                hours_per_day=hours_per_day,
            )
        )

    def add_holiday(self, payload: dict[str, Any]) -> None:
        self._desktop_api.add_holiday(
            SchedulingHolidayCreateCommand(
                holiday_date=self._require_date(
                    payload,
                    "holidayDate",
                    "Holiday date must use YYYY-MM-DD.",
                ),
                name=self._optional_text(payload, "name") or "",
            )
        )

    def delete_holiday(self, holiday_id: str) -> None:
        normalized_id = (holiday_id or "").strip()
        if not normalized_id:
            raise ValueError("Select a holiday before deleting it.")
        self._desktop_api.delete_holiday(normalized_id)

    def create_baseline(self, payload: dict[str, Any]) -> None:
        self._desktop_api.create_baseline(
            SchedulingBaselineCreateCommand(
                project_id=self._require_text(
                    payload,
                    "projectId",
                    "Select a project before creating a baseline.",
                ),
                name=self._optional_text(payload, "name") or "Baseline",
            )
        )

    def delete_baseline(self, baseline_id: str) -> None:
        normalized_id = (baseline_id or "").strip()
        if not normalized_id:
            raise ValueError("Select a baseline before deleting it.")
        self._desktop_api.delete_baseline(normalized_id)

    def submit_baseline(self, baseline_id: str) -> None:
        normalized_id = (baseline_id or "").strip()
        if not normalized_id:
            raise ValueError("Select a baseline before submitting it.")
        self._desktop_api.submit_baseline(
            SchedulingBaselineSubmitCommand(baseline_id=normalized_id)
        )

    def approve_baseline(self, baseline_id: str) -> None:
        normalized_id = (baseline_id or "").strip()
        if not normalized_id:
            raise ValueError("Select a baseline before approving it.")
        self._desktop_api.approve_baseline(
            SchedulingBaselineApproveCommand(baseline_id=normalized_id)
        )

    def reject_baseline(self, baseline_id: str) -> None:
        normalized_id = (baseline_id or "").strip()
        if not normalized_id:
            raise ValueError("Select a baseline before rejecting it.")
        self._desktop_api.reject_baseline(
            SchedulingBaselineRejectCommand(baseline_id=normalized_id)
        )

    def build_baseline_variance_collection(
        self,
        baseline_id: str,
    ) -> SchedulingCollectionViewModel:
        normalized_id = (baseline_id or "").strip()
        if not normalized_id:
            return SchedulingCollectionViewModel(
                title="Baseline Variance",
                subtitle="Per-task variance recorded when this baseline was approved.",
                empty_state="Select a baseline to review its approval-time variance records.",
            )
        try:
            records = self._desktop_api.list_baseline_variance_records(normalized_id)
        except Exception:
            records = ()
        if not records:
            return SchedulingCollectionViewModel(
                title="Baseline Variance",
                subtitle="Per-task variance recorded when this baseline was approved.",
                empty_state=(
                    "No variance records are stored for this baseline. "
                    "Variance is recorded when a new baseline supersedes the previously approved one."
                ),
            )
        return SchedulingCollectionViewModel(
            title="Baseline Variance",
            subtitle=f"Approval-time variance: {len(records)} task(s) changed from the previous baseline.",
            items=tuple(
                self._to_baseline_variance_record_view_model(rec)
                for rec in records
            ),
        )

    @staticmethod
    def _to_baseline_variance_record_view_model(rec) -> SchedulingRecordViewModel:
        task_name = str(getattr(rec, "task_name", "") or getattr(rec, "task_id", "") or "Unknown")
        start_var = int(getattr(rec, "start_variance_days", 0) or 0)
        finish_var = int(getattr(rec, "finish_variance_days", 0) or 0)
        cost_var = float(getattr(rec, "cost_variance", 0.0) or 0.0)
        created = getattr(rec, "created_at", None)
        if start_var > 0 or finish_var > 0:
            status_label = "Delayed"
        elif start_var < 0 or finish_var < 0:
            status_label = "Ahead"
        else:
            status_label = "Shifted"
        return SchedulingRecordViewModel(
            id=str(getattr(rec, "id", "") or ""),
            title=task_name,
            status_label=status_label,
            subtitle=f"Start {ProjectSchedulingWorkspacePresenter._shift_label(start_var)} | Finish {ProjectSchedulingWorkspacePresenter._shift_label(finish_var)}",
            supporting_text=f"Cost delta {cost_var:+,.2f}",
            meta_text=_format_date(created) if created else "-",
            state={
                "taskId": str(getattr(rec, "task_id", "") or ""),
                "taskName": task_name,
                "startVarianceDays": start_var,
                "startVarianceDaysLabel": ProjectSchedulingWorkspacePresenter._shift_label(start_var),
                "finishVarianceDays": finish_var,
                "finishVarianceDaysLabel": ProjectSchedulingWorkspacePresenter._shift_label(finish_var),
                "costVariance": cost_var,
                "costVarianceLabel": f"{cost_var:+,.2f}",
                "createdLabel": _format_date(created) if created else "-",
            },
        )

    def recalculate_schedule(self, project_id: str) -> None:
        normalized_id = (project_id or "").strip()
        if not normalized_id:
            raise ValueError("Select a project before recalculating the schedule.")
        self._desktop_api.recalculate_schedule(normalized_id)

    def create_dependency(self, payload: dict[str, Any]) -> None:
        self._desktop_api.create_dependency(
            SchedulingDependencyCreateCommand(
                task_id=self._require_text(payload, "taskId", "Select an activity first."),
                related_activity_id=self._require_text(
                    payload,
                    "relatedActivityId",
                    "Select a related activity.",
                ),
                relationship_direction=self._require_text(
                    payload,
                    "relationshipDirection",
                    "Choose a dependency direction.",
                ),
                dependency_type=self._optional_text(payload, "dependencyType") or "FS",
                lag_days=self._require_int(payload, "lagDays", "Lag must be a whole number."),
            )
        )

    def update_dependency(self, payload: dict[str, Any]) -> None:
        current_task_id = self._require_text(payload, "taskId", "Select an activity first.")
        self._desktop_api.update_dependency(
            SchedulingDependencyUpdateCommand(
                dependency_id=self._require_text(
                    payload,
                    "dependencyId",
                    "Select a dependency to update.",
                ),
                dependency_type=self._optional_text(payload, "dependencyType") or "FS",
                lag_days=self._require_int(payload, "lagDays", "Lag must be a whole number."),
            ),
            current_task_id=current_task_id,
        )

    def delete_dependency(self, dependency_id: str) -> None:
        normalized_id = (dependency_id or "").strip()
        if not normalized_id:
            raise ValueError("Select a dependency before deleting it.")
        self._desktop_api.delete_dependency(normalized_id)

    def calculate_working_days(self, payload: dict[str, Any]) -> str:
        calculation = self._desktop_api.calculate_working_days(
            SchedulingWorkingDayCalculationCommand(
                start_date=self._require_date(
                    payload,
                    "startDate",
                    "Start date must use YYYY-MM-DD.",
                ),
                working_days=self._require_int(
                    payload,
                    "workingDays",
                    "Working days must be a whole number.",
                ),
            )
        )
        return (
            f"Result: Start {calculation.start_date.isoformat()} + "
            f"{calculation.working_days} working days = "
            f"{calculation.result_date.isoformat()} "
            f"(skipped {calculation.skipped_non_working_days} non-working days)."
        )

    @staticmethod
    def export_schedule(project_id: str) -> str:
        if not str(project_id or "").strip():
            raise ValueError("Select a project before exporting the schedule.")
        return "Export is not available here. Open the Reports section to generate schedule reports, Gantt exports, and baseline comparisons."

    @staticmethod
    def _resolve_project_id(
        project_id: str | None,
        project_options: tuple[SchedulingSelectorOptionViewModel, ...],
    ) -> str:
        normalized_id = (project_id or "").strip()
        option_values = {option.value for option in project_options}
        if normalized_id and normalized_id in option_values:
            return normalized_id
        if project_options:
            return project_options[0].value
        return ""

    @staticmethod
    def _resolve_selected_option(
        selected_value: str | None,
        options: tuple[SchedulingSelectorOptionViewModel, ...],
        *,
        default_value: str,
    ) -> str:
        normalized_value = (selected_value or "").strip()
        if normalized_value and any(option.value == normalized_value for option in options):
            return normalized_value
        if options:
            return options[0].value
        return default_value

    @staticmethod
    def _resolve_baseline_ids(
        *,
        baseline_options: tuple[SchedulingSelectorOptionViewModel, ...],
        selected_baseline_a_id: str | None,
        selected_baseline_b_id: str | None,
    ) -> tuple[str, str]:
        option_values = [option.value for option in baseline_options]
        if not option_values:
            return "", ""
        normalized_a = (selected_baseline_a_id or "").strip()
        normalized_b = (selected_baseline_b_id or "").strip()
        if normalized_a not in option_values:
            normalized_a = option_values[1] if len(option_values) > 1 else option_values[0]
        if normalized_b not in option_values:
            normalized_b = option_values[0]
        return normalized_a, normalized_b

    @staticmethod
    def _build_status_options(schedule_items) -> tuple[SchedulingSelectorOptionViewModel, ...]:
        labels = sorted(
            {
                str(item.status or "").strip()
                for item in schedule_items
                if str(item.status or "").strip()
            }
        )
        return (
            SchedulingSelectorOptionViewModel(value="all", label="All statuses"),
            *(
                SchedulingSelectorOptionViewModel(
                    value=value,
                    label=value.replace("_", " ").title(),
                )
                for value in labels
            ),
        )

    @staticmethod
    def _matches_schedule_filters(
        item,
        *,
        status_filter: str,
        search_text: str,
        show_critical_only: bool,
        show_delayed_only: bool,
    ) -> bool:
        if status_filter != "all" and str(item.status or "").strip().upper() != status_filter.upper():
            return False
        if show_critical_only and not bool(item.is_critical):
            return False
        if show_delayed_only and not ((item.late_by_days or 0) > 0):
            return False
        if not search_text:
            return True
        normalized_search = search_text.casefold()
        haystacks = (
            item.id,
            item.name,
            item.description or "",
            item.status_label or "",
            _format_date(item.start_date),
            _format_date(item.finish_date),
        )
        return any(normalized_search in str(value or "").casefold() for value in haystacks)

    @staticmethod
    def _resolve_selected_activity_id(
        selected_activity_id: str | None,
        *,
        filtered_schedule,
        paged_schedule,
    ) -> str:
        normalized_id = (selected_activity_id or "").strip()
        filtered_ids = {item.id for item in filtered_schedule}
        if normalized_id and normalized_id in filtered_ids:
            return normalized_id
        if paged_schedule:
            return paged_schedule[0].id
        return ""

    @staticmethod
    def _calendar_label(
        calendar_options: tuple[SchedulingSelectorOptionViewModel, ...],
        selected_calendar_id: str,
    ) -> str:
        for option in calendar_options:
            if option.value == selected_calendar_id:
                return option.label
        return "Default Calendar"

    def _build_overview(
        self,
        *,
        resolved_project_id: str,
        schedule_items,
        filtered_schedule,
        critical_items,
        delayed_items,
        dependency_rows,
        baseline_rows,
        calendar_snapshot,
        resource_load,
    ) -> SchedulingOverviewViewModel:
        open_ends = self._count_open_ends(schedule_items, dependency_rows)
        negative_float = sum(
            1 for item in schedule_items if (item.total_float_days or 0) < 0
        )
        overloaded_resources = sum(
            1 for item in resource_load if float(item.utilization_percent or 0.0) > 100.0
        )
        return SchedulingOverviewViewModel(
            title="Scheduling",
            subtitle=(
                "Enterprise planning console for activities, CPM diagnostics, baselines, and resource pressure."
                if resolved_project_id
                else "Select a project to review schedule control, baselines, and resource pressure."
            ),
            metrics=(
                SchedulingMetricViewModel(
                    label="Activities",
                    value=str(len(filtered_schedule)),
                    supporting_text=f"{len(schedule_items)} loaded",
                ),
                SchedulingMetricViewModel(
                    label="Critical",
                    value=str(len(critical_items)),
                    supporting_text="Zero-float path",
                ),
                SchedulingMetricViewModel(
                    label="Delayed",
                    value=str(len(delayed_items)),
                    supporting_text="Activities already late",
                ),
                SchedulingMetricViewModel(
                    label="Open ends",
                    value=str(open_ends),
                    supporting_text="Missing predecessor/successor",
                ),
                SchedulingMetricViewModel(
                    label="Neg. float",
                    value=str(negative_float),
                    supporting_text="Activities with float below zero",
                ),
                SchedulingMetricViewModel(
                    label="Baselines",
                    value=str(len(baseline_rows)),
                    supporting_text="Stored schedule freezes",
                ),
                SchedulingMetricViewModel(
                    label="Calendar",
                    value=f"{float(calendar_snapshot.hours_per_day or 0.0):g}h",
                    supporting_text=f"{len(calendar_snapshot.holidays)} holiday(s)",
                ),
                SchedulingMetricViewModel(
                    label="Overloads",
                    value=str(overloaded_resources),
                    supporting_text="Resources above capacity",
                ),
            ),
        )

    @staticmethod
    def _build_calendar_view_model(calendar_snapshot) -> SchedulingCalendarViewModel:
        holidays = tuple(
            SchedulingRecordViewModel(
                id=holiday.id,
                title=holiday.date.isoformat(),
                status_label="Holiday",
                subtitle=holiday.name or "Non-working day",
                supporting_text="Removed days are excluded from scheduling and working-day calculation.",
                meta_text="Exception",
                can_tertiary_action=True,
                state={
                    "holidayId": holiday.id,
                    "calendar": "Default Calendar",
                    "workingDays": "",
                    "shiftPattern": "Holiday",
                    "hoursPerDay": "-",
                    "exceptions": holiday.name or "Non-working day",
                },
            )
            for holiday in calendar_snapshot.holidays
        )
        active_days = [
            day.label
            for day in calendar_snapshot.working_days
            if day.checked
        ]
        summary = (
            f"Working days: {', '.join(active_days) or 'none'} | "
            f"{float(calendar_snapshot.hours_per_day or 0.0):g} hours per day | "
            f"{len(calendar_snapshot.holidays)} holiday(s)"
        )
        return SchedulingCalendarViewModel(
            summary_text=summary,
            working_day_options=tuple(
                SchedulingDayOptionViewModel(
                    index=day.index,
                    label=day.label,
                    checked=day.checked,
                )
                for day in calendar_snapshot.working_days
            ),
            hours_per_day=f"{float(calendar_snapshot.hours_per_day or 0.0):g}",
            holidays=holidays,
            empty_state="No non-working day exceptions have been configured yet.",
        )

    def _to_schedule_record_view_model(
        self,
        item,
        *,
        row_index: int,
        calendar_label: str,
    ) -> SchedulingRecordViewModel:
        activity_code = f"A-{row_index:03d}"
        progress_value = float(item.percent_complete or 0.0)
        remaining_duration = item.remaining_duration_days
        constraint_label = self._constraint_label_for_activity(item)
        late_label = (
            f"Late by {item.late_by_days} day(s)"
            if (item.late_by_days or 0) > 0
            else "On plan"
        )
        return SchedulingRecordViewModel(
            id=item.id,
            title=item.name,
            status_label=item.status_label,
            subtitle=f"Activity {activity_code} | {_format_date(item.start_date)} -> {_format_date(item.finish_date)}",
            supporting_text=(
                f"Duration {self._int_label(item.duration_days)} | Remaining {self._int_label(remaining_duration)} | "
                f"Float {self._int_label(item.total_float_days)}"
            ),
            meta_text=f"{late_label} | Calendar {calendar_label}",
            state={
                "activityId": item.id,
                "activityCode": activity_code,
                "wbs": f"1.{row_index:02d}",
                "taskName": item.name,
                "startDateLabel": _format_date(item.start_date),
                "finishDateLabel": _format_date(item.finish_date),
                "durationLabel": self._int_label(item.duration_days),
                "remainingDurationLabel": self._int_label(remaining_duration),
                "floatLabel": self._int_label(item.total_float_days),
                "criticalLabel": "Critical" if item.is_critical else "Normal",
                "constraintLabel": constraint_label,
                "calendarLabel": calendar_label,
                "progressValue": {
                    "value": progress_value / 100.0,
                    "label": f"{progress_value:.0f}%",
                },
                "statusLabel": item.status_label,
                "deadlineLabel": _format_date(item.deadline),
                "latestStartLabel": _format_date(item.latest_start),
                "latestFinishLabel": _format_date(item.latest_finish),
                "lateByLabel": self._int_label(item.late_by_days),
                "actualStartLabel": _format_date(item.actual_start),
                "actualFinishLabel": _format_date(item.actual_end),
                "description": item.description or "",
            },
        )

    def _to_timeline_record_view_model(self, item, *, timeline_items) -> SchedulingRecordViewModel:
        bounds = self._timeline_bounds(timeline_items)
        start_offset = self._days_between(bounds[0], item.start_date)
        finish_offset = self._days_between(bounds[0], item.finish_date)
        current_offset = self._days_between(bounds[0], date.today())
        window_days = (
            max(1, ((bounds[1] - bounds[0]).days + 1))
            if bounds[0] is not None and bounds[1] is not None
            else 1
        )
        span_days = max(1, (finish_offset - start_offset) + 1) if start_offset is not None and finish_offset is not None else 1
        milestone = bool(item.start_date and item.finish_date and item.start_date == item.finish_date)
        return SchedulingRecordViewModel(
            id=item.id,
            title=item.name,
            status_label="Critical" if item.is_critical else item.status_label,
            subtitle=f"{_format_date(item.start_date)} -> {_format_date(item.finish_date)}",
            supporting_text=f"Progress {float(item.percent_complete or 0.0):.0f}% | Float {self._int_label(item.total_float_days)}",
            meta_text=f"Window {bounds[0].isoformat()} -> {bounds[1].isoformat()}" if bounds[0] and bounds[1] else "",
            state={
                "startOffsetDays": start_offset if start_offset is not None else 0,
                "spanDays": span_days,
                "milestone": milestone,
                "critical": bool(item.is_critical),
                "progressPercent": float(item.percent_complete or 0.0),
                "baselinePlaceholder": True,
                "startDateLabel": _format_date(item.start_date),
                "finishDateLabel": _format_date(item.finish_date),
                "windowStartLabel": _format_date(bounds[0]),
                "windowFinishLabel": _format_date(bounds[1]),
                "windowDays": window_days,
                "currentOffsetDays": current_offset if current_offset is not None else -1,
            },
        )

    @staticmethod
    def _to_critical_path_record_view_model(item) -> SchedulingRecordViewModel:
        return SchedulingRecordViewModel(
            id=item.id,
            title=item.name,
            status_label="Critical",
            subtitle=f"{_format_date(item.start_date)} -> {_format_date(item.finish_date)}",
            supporting_text=f"Float {ProjectSchedulingWorkspacePresenter._int_label(item.total_float_days)} | Progress {float(item.percent_complete or 0.0):.0f}%",
            meta_text=f"Latest finish {_format_date(item.latest_finish)}",
            state={"activityId": item.id},
        )

    @staticmethod
    def _to_delayed_activity_record_view_model(item) -> SchedulingRecordViewModel:
        return SchedulingRecordViewModel(
            id=item.id,
            title=item.name,
            status_label="Delayed",
            subtitle=f"Finish {_format_date(item.finish_date)} | Deadline {_format_date(item.deadline)}",
            supporting_text=f"Late by {ProjectSchedulingWorkspacePresenter._int_label(item.late_by_days)} day(s)",
            meta_text=f"Progress {float(item.percent_complete or 0.0):.0f}%",
            state={"activityId": item.id},
        )

    @staticmethod
    def _to_baseline_compare_record_view_model(item) -> SchedulingRecordViewModel:
        return SchedulingRecordViewModel(
            id=item.task_id,
            title=item.task_name,
            status_label=item.change_type.title(),
            subtitle=(
                f"Start {_format_date(item.baseline_a_start)} -> {_format_date(item.baseline_b_start)} | "
                f"Finish {_format_date(item.baseline_a_finish)} -> {_format_date(item.baseline_b_finish)}"
            ),
            supporting_text=(
                f"Start shift {ProjectSchedulingWorkspacePresenter._shift_label(item.start_shift_days)} | "
                f"Finish shift {ProjectSchedulingWorkspacePresenter._shift_label(item.finish_shift_days)} | "
                f"Duration {ProjectSchedulingWorkspacePresenter._shift_label(item.duration_delta_days)}"
            ),
            meta_text=f"Planned cost delta {float(item.planned_cost_delta or 0.0):,.2f}",
            state={
                "taskId": item.task_id,
                "baselineState": item.change_type.title(),
                "createdLabel": "",
                "approvedByLabel": "",
                "varianceState": item.change_type.title(),
            },
        )

    @staticmethod
    def _to_baseline_register_record_view_model(item) -> SchedulingRecordViewModel:
        return SchedulingRecordViewModel(
            id=item.id,
            title=item.name,
            status_label=item.status_label,
            subtitle=item.created_at_label,
            supporting_text=f"Approved by {item.approved_by_label}",
            meta_text=f"Snapshot {item.variance_state_label}",
            can_primary_action=item.can_submit,
            can_secondary_action=item.can_approve,
            can_tertiary_action=item.can_reject,
            state={
                "baselineId": item.id,
                "baselineName": item.name,
                "createdLabel": item.created_at_label,
                "approvedByLabel": item.approved_by_label,
                "varianceState": item.variance_state_label,
                "status": item.status,
                "statusLabel": item.status_label,
                "canSubmit": item.can_submit,
                "canApprove": item.can_approve,
                "canReject": item.can_reject,
            },
        )

    @staticmethod
    def _to_dependency_record_view_model(item) -> SchedulingRecordViewModel:
        return SchedulingRecordViewModel(
            id=item.id,
            title=item.related_activity_name,
            status_label=item.direction_label,
            subtitle=f"{item.dependency_type_label} | Lag {item.lag_days:+d}d",
            supporting_text=item.relationship_label,
            meta_text="Linked activity",
            can_secondary_action=True,
            can_tertiary_action=True,
            state={
                "dependencyId": item.id,
                "taskId": item.related_activity_id,
                "directionLabel": item.direction_label,
                "relatedActivityName": item.related_activity_name,
                "dependencyType": item.dependency_type,
                "dependencyTypeLabel": item.dependency_type_label,
                "lagDays": item.lag_days,
                "lagLabel": f"{item.lag_days:+d}d",
                "relationshipLabel": item.relationship_label,
                "statusLabel": item.status_label,
            },
        )

    def _build_constraints_collection(self, selected_activity) -> SchedulingCollectionViewModel:
        if selected_activity is None:
            return SchedulingCollectionViewModel(
                title="Constraints",
                subtitle="Schedule controls and date guards for the selected activity.",
                empty_state="Select an activity to inspect schedule constraints and controls.",
            )
        rows: list[SchedulingRecordViewModel] = []
        if selected_activity.start_date:
            rows.append(
                SchedulingRecordViewModel(
                    id=f"{selected_activity.id}:start",
                    title="Planned Start",
                    status_label="Start Control",
                    subtitle=_format_date(selected_activity.start_date),
                    supporting_text="Current start anchor used by the scheduling engine.",
                    meta_text="Derived from current plan",
                    state={
                        "constraintType": "Planned Start",
                        "constraintValue": _format_date(selected_activity.start_date),
                        "constraintStatus": "Current plan",
                    },
                )
            )
        if selected_activity.deadline:
            rows.append(
                SchedulingRecordViewModel(
                    id=f"{selected_activity.id}:deadline",
                    title="Finish No Later Than",
                    status_label="Deadline",
                    subtitle=_format_date(selected_activity.deadline),
                    supporting_text="Current deadline control used for delay diagnostics.",
                    meta_text="Project deadline guard",
                    state={
                        "constraintType": "Finish No Later Than",
                        "constraintValue": _format_date(selected_activity.deadline),
                        "constraintStatus": "Active",
                    },
                )
            )
        if selected_activity.actual_start:
            rows.append(
                SchedulingRecordViewModel(
                    id=f"{selected_activity.id}:actual-start",
                    title="Actual Start Lock",
                    status_label="Actual",
                    subtitle=_format_date(selected_activity.actual_start),
                    supporting_text="Actual progress constrains forward-pass recalculation.",
                    meta_text="Execution lock",
                )
            )
        if selected_activity.actual_end:
            rows.append(
                SchedulingRecordViewModel(
                    id=f"{selected_activity.id}:actual-finish",
                    title="Actual Finish Lock",
                    status_label="Actual",
                    subtitle=_format_date(selected_activity.actual_end),
                    supporting_text="Actual finish constrains recalculation and variance reporting.",
                    meta_text="Execution lock",
                )
            )
        return SchedulingCollectionViewModel(
            title="Constraints",
            subtitle="Schedule controls and date guards for the selected activity.",
            items=tuple(rows),
            empty_state="No explicit schedule controls are recorded for the selected activity.",
        )

    @staticmethod
    def _to_resource_load_record_view_model(item) -> SchedulingRecordViewModel:
        return SchedulingRecordViewModel(
            id=item.resource_id,
            title=item.resource_name,
            status_label=item.status_label,
            subtitle=f"Utilization {item.utilization_label} | Capacity {item.capacity_label}",
            supporting_text=f"Peak allocation {item.total_allocation_label} across {item.tasks_count} task(s)",
            meta_text=item.status_label,
            state={
                "resourceId": item.resource_id,
                "resourceName": item.resource_name,
                "allocationLabel": item.total_allocation_label,
                "capacityLabel": item.capacity_label,
                "utilizationLabel": item.utilization_label,
                "tasksCount": item.tasks_count,
                "statusLabel": item.status_label,
            },
        )

    @staticmethod
    def _to_constraint_violation_record_view_model(
        item: SchedulingConstraintViolationDto,
    ) -> SchedulingRecordViewModel:
        return SchedulingRecordViewModel(
            id=f"{item.task_id}:{item.constraint_type}",
            title=item.task_name,
            status_label=item.severity_label,
            subtitle=f"{item.constraint_type_label} | Required {item.constraint_date_label}",
            supporting_text=f"Computed {item.computed_date_label} | Overrun {item.overrun_working_days}d",
            meta_text=item.message,
            state={
                "taskId": item.task_id,
                "constraintType": item.constraint_type,
                "constraintTypeLabel": item.constraint_type_label,
                "constraintDateLabel": item.constraint_date_label,
                "computedDateLabel": item.computed_date_label,
                "overrunDays": item.overrun_working_days,
                "severity": item.severity,
                "severityLabel": item.severity_label,
                "message": item.message,
            },
        )

    def _build_diagnostics_collection(
        self,
        *,
        schedule_items,
        filtered_schedule,
        dependency_rows,
        resource_load,
    ) -> SchedulingCollectionViewModel:
        open_ends = self._count_open_ends(schedule_items, dependency_rows)
        negative_float = sum(
            1 for item in schedule_items if (item.total_float_days or 0) < 0
        )
        delayed = sum(1 for item in filtered_schedule if (item.late_by_days or 0) > 0)
        constraints = sum(
            1 for item in schedule_items if item.deadline is not None and (item.late_by_days or 0) > 0
        )
        overloads = sum(
            1 for item in resource_load if float(item.utilization_percent or 0.0) > 100.0
        )
        rows = (
            SchedulingRecordViewModel(
                id="critical",
                title="Critical Path Length",
                status_label="Critical",
                subtitle=str(sum(1 for item in schedule_items if item.is_critical)),
                supporting_text="Activities on the current zero-float path.",
                meta_text="CPM",
            ),
            SchedulingRecordViewModel(
                id="open-ends",
                title="Open Ends",
                status_label="Warning" if open_ends else "Stable",
                subtitle=str(open_ends),
                supporting_text="Activities missing a predecessor or successor.",
                meta_text="Network quality",
            ),
            SchedulingRecordViewModel(
                id="negative-float",
                title="Negative Float",
                status_label="Danger" if negative_float else "Stable",
                subtitle=str(negative_float),
                supporting_text="Activities with float below zero.",
                meta_text="Schedule pressure",
            ),
            SchedulingRecordViewModel(
                id="delayed",
                title="Delayed Activities",
                status_label="Warning" if delayed else "Stable",
                subtitle=str(delayed),
                supporting_text="Filtered activities already late.",
                meta_text="Execution risk",
            ),
            SchedulingRecordViewModel(
                id="constraints",
                title="Constraint Violations",
                status_label="Danger" if constraints else "Stable",
                subtitle=str(constraints),
                supporting_text="Activities missing their current deadline guard.",
                meta_text="Deadline control",
            ),
            SchedulingRecordViewModel(
                id="overloads",
                title="Resource Conflicts",
                status_label="Danger" if overloads else "Stable",
                subtitle=str(overloads),
                supporting_text="Resources above effective capacity.",
                meta_text="Loading pressure",
            ),
        )
        return SchedulingCollectionViewModel(
            title="Diagnostics",
            subtitle="Planner checks for network quality, float pressure, and resource overload.",
            items=rows,
            empty_state="No diagnostics are available yet.",
        )

    def _build_activity_feed_collection(
        self,
        *,
        schedule_items,
        delayed_items,
        resource_load,
        activity_log: tuple[dict[str, str], ...],
    ) -> SchedulingCollectionViewModel:
        rows: list[SchedulingRecordViewModel] = [
            SchedulingRecordViewModel(
                id=f"log:{index}",
                title=str(item.get("title", "") or ""),
                status_label=str(item.get("statusLabel", "") or "Info"),
                subtitle=str(item.get("subtitle", "") or ""),
                supporting_text="",
                meta_text=str(item.get("metaText", "") or ""),
            )
            for index, item in enumerate(activity_log, start=1)
            if str(item.get("title", "") or "").strip()
        ]
        if delayed_items:
            top_delay = delayed_items[0]
            rows.append(
                SchedulingRecordViewModel(
                    id=f"delay:{top_delay.id}",
                    title=f"{top_delay.name} is late",
                    status_label="Warning",
                    subtitle=f"Late by {self._int_label(top_delay.late_by_days)} day(s)",
                    supporting_text="Review deadline protection and downstream impact.",
                    meta_text=_format_date(top_delay.finish_date),
                )
            )
        overloaded = next(
            (item for item in resource_load if float(item.utilization_percent or 0.0) > 100.0),
            None,
        )
        if overloaded is not None:
            rows.append(
                SchedulingRecordViewModel(
                    id=f"resource:{overloaded.resource_id}",
                    title=f"{overloaded.resource_name} exceeds capacity",
                    status_label="Danger",
                    subtitle=f"Utilization {overloaded.utilization_label}",
                    supporting_text="Resource leveling or reassignment may be required.",
                    meta_text=f"{overloaded.tasks_count} task(s)",
                )
            )
        if not rows and schedule_items:
            rows.append(
                SchedulingRecordViewModel(
                    id="feed:loaded",
                    title="Schedule snapshot loaded",
                    status_label="Info",
                    subtitle=f"{len(schedule_items)} activities available",
                    supporting_text="Planner data is ready for review and recalculation.",
                    meta_text="Current session",
                )
            )
        return SchedulingCollectionViewModel(
            title="Planning Activity",
            subtitle="Recent planning actions, warnings, and schedule control events.",
            items=tuple(rows[:12]),
            empty_state="No planning activity has been recorded in this session.",
        )

    def _build_detail_view_model(
        self,
        *,
        selected_activity,
        calendar_label: str,
        dependency_rows,
        resource_load,
        baseline_rows,
    ) -> SchedulingDetailViewModel:
        if selected_activity is None:
            return SchedulingDetailViewModel(
                title="No activity selected",
                empty_state="Select an activity from the schedule table to inspect logic, constraints, resource pressure, and baseline context.",
            )
        related_resource = resource_load[0] if resource_load else None
        latest_baseline = baseline_rows[0] if baseline_rows else None
        return SchedulingDetailViewModel(
            id=selected_activity.id,
            title=selected_activity.name,
            status_label="Critical" if selected_activity.is_critical else selected_activity.status_label,
            subtitle=f"{_format_date(selected_activity.start_date)} -> {_format_date(selected_activity.finish_date)}",
            description=selected_activity.description or "Schedule activity selected for planning inspection.",
            fields=(
                SchedulingDetailFieldViewModel(
                    label="Activity ID",
                    value=selected_activity.id,
                    supporting_text="Current operational identifier.",
                ),
                SchedulingDetailFieldViewModel(
                    label="Start",
                    value=_format_date(selected_activity.start_date),
                    supporting_text=f"Latest {_format_date(selected_activity.latest_start)}",
                ),
                SchedulingDetailFieldViewModel(
                    label="Finish",
                    value=_format_date(selected_activity.finish_date),
                    supporting_text=f"Latest {_format_date(selected_activity.latest_finish)}",
                ),
                SchedulingDetailFieldViewModel(
                    label="Duration",
                    value=self._int_label(selected_activity.duration_days),
                    supporting_text=f"Remaining {self._int_label(selected_activity.remaining_duration_days)}",
                ),
                SchedulingDetailFieldViewModel(
                    label="Float",
                    value=self._int_label(selected_activity.total_float_days),
                    supporting_text="Total float in working days.",
                ),
                SchedulingDetailFieldViewModel(
                    label="Deadline",
                    value=_format_date(selected_activity.deadline),
                    supporting_text=self._constraint_label_for_activity(selected_activity),
                ),
                SchedulingDetailFieldViewModel(
                    label="Calendar",
                    value=calendar_label,
                    supporting_text="Current planning calendar.",
                ),
                SchedulingDetailFieldViewModel(
                    label="Dependencies",
                    value=str(len(dependency_rows)),
                    supporting_text="Active predecessor/successor links.",
                ),
                SchedulingDetailFieldViewModel(
                    label="Top resource pressure",
                    value=related_resource.resource_name if related_resource else "None",
                    supporting_text=related_resource.utilization_label if related_resource else "No resource load data",
                ),
                SchedulingDetailFieldViewModel(
                    label="Latest baseline",
                    value=latest_baseline.name if latest_baseline else "None",
                    supporting_text=latest_baseline.created_at_label if latest_baseline else "No baseline stored",
                ),
            ),
            state={
                "activityId": selected_activity.id,
                "projectId": selected_activity.project_id,
                "title": selected_activity.name,
                "description": selected_activity.description or "",
                "statusLabel": selected_activity.status_label,
                "startDateLabel": _format_date(selected_activity.start_date),
                "finishDateLabel": _format_date(selected_activity.finish_date),
                "durationLabel": self._int_label(selected_activity.duration_days),
                "remainingDurationLabel": self._int_label(selected_activity.remaining_duration_days),
                "floatLabel": self._int_label(selected_activity.total_float_days),
                "deadlineLabel": _format_date(selected_activity.deadline),
                "progressPercent": float(selected_activity.percent_complete or 0.0),
            },
        )

    @staticmethod
    def _build_schedule_empty_state(
        *,
        resolved_project_id: str,
        schedule_items,
    ) -> str:
        if not resolved_project_id:
            return "Select a project to review the current schedule."
        if schedule_items:
            return ""
        return "No scheduled activities are available for the selected project."

    @staticmethod
    def _constraint_label_for_activity(item) -> str:
        if item.actual_end:
            return "Actual finish locked"
        if item.actual_start:
            return "Actual start locked"
        if item.deadline:
            return "Finish no later than"
        if item.start_date:
            return "Planned start anchor"
        return "Open"

    @staticmethod
    def _timeline_bounds(items) -> tuple[date | None, date | None]:
        starts = [item.start_date for item in items if item.start_date]
        finishes = [item.finish_date for item in items if item.finish_date]
        if not starts and not finishes:
            return None, None
        minimum = min(starts or finishes)
        maximum = max(finishes or starts)
        return minimum, maximum

    @staticmethod
    def _days_between(origin: date | None, target: date | None) -> int | None:
        if origin is None or target is None:
            return None
        return (target - origin).days

    @staticmethod
    def _count_open_ends(schedule_items, dependency_rows) -> int:
        if not schedule_items:
            return 0
        predecessor_count: dict[str, int] = {}
        successor_count: dict[str, int] = {}
        for row in dependency_rows:
            successor_count[row.predecessor_task_id] = successor_count.get(row.predecessor_task_id, 0) + 1
            predecessor_count[row.successor_task_id] = predecessor_count.get(row.successor_task_id, 0) + 1
        open_ends = 0
        for item in schedule_items:
            if predecessor_count.get(item.id, 0) == 0 or successor_count.get(item.id, 0) == 0:
                open_ends += 1
        return open_ends

    @staticmethod
    def _label_for_option(
        option_value: str,
        options: tuple[SchedulingSelectorOptionViewModel, ...],
    ) -> str:
        for option in options:
            if option.value == option_value:
                return option.label
        return option_value

    @staticmethod
    def _int_label(value: int | None) -> str:
        return "-" if value is None else str(int(value))

    @staticmethod
    def _shift_label(value: int | None) -> str:
        if value is None:
            return "-"
        return f"{int(value):+d}d"

    @staticmethod
    def _require_text(payload: dict[str, Any], key: str, message: str) -> str:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            raise ValueError(message)
        return value

    @staticmethod
    def _optional_text(payload: dict[str, Any], key: str) -> str | None:
        value = str(payload.get(key, "") or "").strip()
        return value or None

    @staticmethod
    def _require_int(payload: dict[str, Any], key: str, message: str) -> int:
        value = str(payload.get(key, "") or "").strip()
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError(message) from exc

    @staticmethod
    def _require_float(payload: dict[str, Any], key: str, message: str) -> float:
        value = str(payload.get(key, "") or "").strip()
        try:
            parsed = float(value)
        except ValueError as exc:
            raise ValueError(message) from exc
        if parsed <= 0:
            raise ValueError(message)
        return parsed

    @staticmethod
    def _require_date(payload: dict[str, Any], key: str, message: str) -> date:
        value = str(payload.get(key, "") or "").strip()
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(message) from exc


def _format_date(value: date | None) -> str:
    return value.isoformat() if value else "-"


__all__ = ["ProjectSchedulingWorkspacePresenter"]
