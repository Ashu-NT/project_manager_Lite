from __future__ import annotations

from datetime import date
from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementSchedulingDesktopApi,
    SchedulingBaselineCreateCommand,
    SchedulingCalendarUpdateCommand,
    SchedulingHolidayCreateCommand,
    SchedulingWorkingDayCalculationCommand,
    build_project_management_scheduling_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.scheduling import (
    SchedulingBaselineCompareViewModel,
    SchedulingCalendarViewModel,
    SchedulingCollectionViewModel,
    SchedulingDayOptionViewModel,
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
        selected_baseline_a_id: str | None = None,
        selected_baseline_b_id: str | None = None,
        include_unchanged: bool = False,
    ) -> SchedulingWorkspaceViewModel:
        project_options = tuple(
            SchedulingSelectorOptionViewModel(value=option.value, label=option.label)
            for option in self._desktop_api.list_projects()
        )
        resolved_project_id = self._resolve_project_id(project_id, project_options)
        calendar_snapshot = self._desktop_api.get_calendar_snapshot()
        schedule_items = self._desktop_api.list_schedule(resolved_project_id) if resolved_project_id else ()
        critical_items = tuple(item for item in schedule_items if item.is_critical)
        baseline_options = tuple(
            SchedulingSelectorOptionViewModel(value=option.value, label=option.label)
            for option in self._desktop_api.list_baselines(resolved_project_id)
        ) if resolved_project_id else ()
        resolved_baseline_a_id, resolved_baseline_b_id = self._resolve_baseline_ids(
            baseline_options=baseline_options,
            selected_baseline_a_id=selected_baseline_a_id,
            selected_baseline_b_id=selected_baseline_b_id,
        )
        comparison_rows = ()
        comparison_summary = ""
        comparison_empty_state = ""
        if resolved_project_id and resolved_baseline_a_id and resolved_baseline_b_id:
            comparison_rows = self._desktop_api.compare_baselines(
                project_id=resolved_project_id,
                baseline_a_id=resolved_baseline_a_id,
                baseline_b_id=resolved_baseline_b_id,
                include_unchanged=include_unchanged,
            )
        if not baseline_options:
            comparison_empty_state = (
                "Create at least two baselines before comparing scheduling drift."
                if resolved_project_id
                else "Select a project to review baseline comparisons."
            )
        elif resolved_baseline_a_id == resolved_baseline_b_id:
            comparison_empty_state = "Select two different baselines to compare."
        elif comparison_rows:
            comparison_summary = (
                f"Comparing {baseline_options_by_id(baseline_options)[resolved_baseline_a_id]} "
                f"to {baseline_options_by_id(baseline_options)[resolved_baseline_b_id]}."
            )
        else:
            comparison_empty_state = "No baseline changes match the current comparison filter."

        return SchedulingWorkspaceViewModel(
            overview=self._build_overview(
                schedule_items=schedule_items,
                critical_items=critical_items,
                baseline_options=baseline_options,
                calendar_snapshot=calendar_snapshot,
            ),
            project_options=project_options,
            selected_project_id=resolved_project_id,
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
                title="Schedule Snapshot",
                subtitle="Preview current start/finish, float, and deadline pressure.",
                items=tuple(
                    self._to_schedule_record_view_model(item)
                    for item in schedule_items
                ),
                empty_state=self._build_schedule_empty_state(
                    resolved_project_id=resolved_project_id,
                    schedule_items=schedule_items,
                ),
            ),
            critical_path=SchedulingCollectionViewModel(
                title="Critical Path",
                subtitle="Tasks with zero float that drive the current delivery path.",
                items=tuple(
                    self._to_critical_path_record_view_model(item)
                    for item in critical_items
                ),
                empty_state=(
                    "No critical-path tasks are available for the selected project."
                    if resolved_project_id
                    else "Select a project to review the critical path."
                ),
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

    def recalculate_schedule(self, project_id: str) -> None:
        normalized_id = (project_id or "").strip()
        if not normalized_id:
            raise ValueError("Select a project before recalculating the schedule.")
        self._desktop_api.recalculate_schedule(normalized_id)

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
    def _build_overview(
        *,
        schedule_items,
        critical_items,
        baseline_options,
        calendar_snapshot,
    ) -> SchedulingOverviewViewModel:
        late_count = sum(1 for item in schedule_items if (item.late_by_days or 0) > 0)
        return SchedulingOverviewViewModel(
            title="Scheduling",
            subtitle="Calendars, baseline comparison, dependency graphs, and critical-path views.",
            metrics=(
                SchedulingMetricViewModel(
                    label="Scheduled tasks",
                    value=str(len(schedule_items)),
                    supporting_text="Current CPM preview.",
                ),
                SchedulingMetricViewModel(
                    label="Critical path",
                    value=str(len(critical_items)),
                    supporting_text="Zero-float tasks.",
                ),
                SchedulingMetricViewModel(
                    label="Late tasks",
                    value=str(late_count),
                    supporting_text="Behind deadline today.",
                ),
                SchedulingMetricViewModel(
                    label="Baselines",
                    value=str(len(baseline_options)),
                    supporting_text="Snapshots available.",
                ),
                SchedulingMetricViewModel(
                    label="Holidays",
                    value=str(len(calendar_snapshot.holidays)),
                    supporting_text="Non-working days configured.",
                ),
                SchedulingMetricViewModel(
                    label="Hours / day",
                    value=f"{float(calendar_snapshot.hours_per_day or 0.0):g}",
                    supporting_text="Current working calendar.",
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
                supporting_text="Removed days are excluded from CPM calculations and working-day math.",
                meta_text="",
                can_tertiary_action=True,
                state={"holidayId": holiday.id},
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
            empty_state="No non-working days have been configured yet.",
        )

    @staticmethod
    def _to_schedule_record_view_model(item) -> SchedulingRecordViewModel:
        float_label = (
            str(item.total_float_days)
            if item.total_float_days is not None
            else "-"
        )
        deadline_label = item.deadline.isoformat() if item.deadline else "Not set"
        late_label = (
            f"Late by {item.late_by_days} day(s)"
            if (item.late_by_days or 0) > 0
            else "On plan"
        )
        return SchedulingRecordViewModel(
            id=item.id,
            title=item.name,
            status_label=item.status_label,
            subtitle=(
                f"Start {format_date(item.start_date)} | "
                f"Finish {format_date(item.finish_date)} | "
                f"Float {float_label} day(s)"
            ),
            supporting_text=(
                f"Latest: {format_date(item.latest_start)} -> {format_date(item.latest_finish)} | "
                f"Deadline: {deadline_label}"
            ),
            meta_text=(
                f"Progress: {float(item.percent_complete or 0.0):.1f}% | "
                f"{late_label} | Critical: {'Yes' if item.is_critical else 'No'}"
            ),
            state={
                "taskId": item.id,
                "isCritical": item.is_critical,
            },
        )

    @staticmethod
    def _to_critical_path_record_view_model(item) -> SchedulingRecordViewModel:
        return SchedulingRecordViewModel(
            id=item.id,
            title=item.name,
            status_label="Critical",
            subtitle=(
                f"Start {format_date(item.start_date)} | "
                f"Finish {format_date(item.finish_date)}"
            ),
            supporting_text=(
                f"Latest finish {format_date(item.latest_finish)} | "
                f"Deadline {format_date(item.deadline)}"
            ),
            meta_text=f"Progress: {float(item.percent_complete or 0.0):.1f}%",
            state={"taskId": item.id},
        )

    @staticmethod
    def _to_baseline_compare_record_view_model(item) -> SchedulingRecordViewModel:
        return SchedulingRecordViewModel(
            id=item.task_id,
            title=item.task_name,
            status_label=item.change_type.title(),
            subtitle=(
                f"Start {format_date(item.baseline_a_start)} -> {format_date(item.baseline_b_start)} | "
                f"Finish {format_date(item.baseline_a_finish)} -> {format_date(item.baseline_b_finish)}"
            ),
            supporting_text=(
                f"Start shift {format_shift(item.start_shift_days)} | "
                f"Finish shift {format_shift(item.finish_shift_days)} | "
                f"Duration delta {format_shift(item.duration_delta_days)}"
            ),
            meta_text=f"Planned cost delta: {item.planned_cost_delta:,.2f}",
            state={"taskId": item.task_id},
        )

    @staticmethod
    def _build_schedule_empty_state(
        *,
        resolved_project_id: str,
        schedule_items,
    ) -> str:
        if not resolved_project_id:
            return "Select a project to preview the current schedule."
        if schedule_items:
            return ""
        return "No scheduled tasks are available for the selected project."

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
    def _resolve_baseline_ids(
        *,
        baseline_options: tuple[SchedulingSelectorOptionViewModel, ...],
        selected_baseline_a_id: str | None,
        selected_baseline_b_id: str | None,
    ) -> tuple[str, str]:
        option_values = [option.value for option in baseline_options]
        normalized_a = (selected_baseline_a_id or "").strip()
        normalized_b = (selected_baseline_b_id or "").strip()
        if normalized_a not in option_values:
            normalized_a = option_values[1] if len(option_values) > 1 else (option_values[0] if option_values else "")
        if normalized_b not in option_values:
            normalized_b = option_values[0] if option_values else ""
        return normalized_a, normalized_b

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
            parsed = int(value)
        except ValueError as exc:
            raise ValueError(message) from exc
        if parsed <= 0:
            raise ValueError(message)
        return parsed

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


def format_date(value: date | None) -> str:
    return value.isoformat() if value else "-"


def format_shift(value: int | None) -> str:
    if value is None:
        return "-"
    return f"{value:+d}d"


def baseline_options_by_id(
    options: tuple[SchedulingSelectorOptionViewModel, ...],
) -> dict[str, str]:
    return {option.value: option.label for option in options}


__all__ = ["ProjectSchedulingWorkspacePresenter"]
