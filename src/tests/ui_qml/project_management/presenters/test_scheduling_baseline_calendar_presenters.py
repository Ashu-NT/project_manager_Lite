from dataclasses import FrozenInstanceError, replace
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.core.modules.project_management.application.scheduling.dto.responses.calendars import (
    SchedulingCalendarResponse,
    SchedulingCalendarSnapshot,
)
from src.core.modules.project_management.application.scheduling.mappers.baselines import (
    map_baseline,
)
from src.core.modules.project_management.domain.scheduling.baseline import (
    ProjectBaseline,
)
from src.core.platform.api.desktop.time_management.calendar.models.platform_calendar import (
    CalendarDto,
)
from src.core.platform.application.time_management.calendar.dto.responses.working_calendar import (
    WorkingCalendarHolidayDto,
)
from src.tests.ui_qml.project_management.controllers.test_r4_5b_gantt_read_contract import (
    _projection,
)
from src.ui_qml.modules.project_management.controllers.scheduling.gantt_list_model import (
    GanttListModel,
)
from src.ui_qml.modules.project_management.presenters.scheduling.calendar_builder import (
    build_calendar_view_model,
    to_calendar_option,
)
from src.ui_qml.modules.project_management.presenters.scheduling.gantt_labels import (
    constraint_label,
)
from src.ui_qml.modules.project_management.presenters.scheduling.record_mappers import (
    to_baseline_compare_record,
    to_baseline_register_record,
)


def test_baseline_register_formats_labels_and_preserves_lifecycle_actions() -> None:
    baseline = ProjectBaseline(
        id="base-1",
        project_id="project-1",
        name="Original",
        created_at=date(2026, 5, 1),
    )
    baseline.submit("Planner")
    facts = map_baseline(baseline)

    latest = to_baseline_register_record(facts, 0)
    stored = to_baseline_register_record(facts, 1)

    assert latest.status_label == "Submitted"
    assert latest.subtitle == "2026-05-01 00:00"
    assert latest.supporting_text == "Approved by System snapshot"
    assert latest.meta_text == "Snapshot Latest"
    assert stored.meta_text == "Snapshot Stored"
    assert not latest.can_primary_action
    assert latest.can_secondary_action and latest.can_tertiary_action
    assert facts.status == "submitted"


def test_calendar_presenter_owns_weekday_labels_and_selector_metadata() -> None:
    snapshot = SchedulingCalendarSnapshot(
        working_days=(0, 2),
        hours_per_day=6.5,
        holidays=(WorkingCalendarHolidayDto("holiday", date(2026, 5, 1), ""),),
        calendar_id="cal-1",
        calendar_name="Local",
    )
    view = build_calendar_view_model(snapshot)
    assert [day.label for day in view.working_day_options] == [
        "Mon",
        "Tue",
        "Wed",
        "Thu",
        "Fri",
        "Sat",
        "Sun",
    ]
    assert [day.index for day in view.working_day_options if day.checked] == [0, 2]
    assert (
        view.summary_text == "Working days: Mon, Wed | 6.5 hours per day | 1 holiday(s)"
    )
    assert view.holidays[0].subtitle == "Non-working day"
    assert (
        to_calendar_option(
            SchedulingCalendarResponse("legacy", "Local", (0, 2), 6.5)
        ).supporting_text
        == "Mon, Wed | 6.5h/day"
    )
    platform = CalendarDto(
        "cal-1", "org-1", "STD", "Standard", "work", "Europe/Berlin", True, True
    )
    assert to_calendar_option(platform).supporting_text == "Work \u00b7 Europe/Berlin"


def test_gantt_keeps_immutable_facts_and_formats_labels_only_in_ui() -> None:
    projection = _projection(2, with_edges=True)
    row = replace(projection.rows[0], status="in_progress", constraint_type="")
    model = GanttListModel()
    model.set_projection(projection)
    assert model.projection is projection
    assert model.all_rows[0] is projection.rows[0]
    assert not hasattr(row, "status_label")
    assert not hasattr(row, "constraint_type_label")
    assert not hasattr(projection.dependency_edges[0], "dependency_type_label")
    assert model.serialize_row(row)["statusLabel"] == "In Progress"
    assert constraint_label(row) == "As Soon As Possible (ASAP)"
    assert constraint_label(replace(row, is_summary=True)) == ""
    with pytest.raises(FrozenInstanceError):
        setattr(row, "name", "Changed")


def test_comparison_formats_decimal_without_a_float_round_trip() -> None:
    row = SimpleNamespace(
        task_id="task",
        task_name="Task",
        change_type="CHANGED",
        baseline_a_start=None,
        baseline_b_start=None,
        baseline_a_finish=None,
        baseline_b_finish=None,
        start_shift_days=0,
        finish_shift_days=0,
        duration_delta_days=0,
        planned_cost_delta=Decimal("12345678901234567890.123456789"),
    )
    assert (
        to_baseline_compare_record(row).meta_text
        == "Planned cost delta 12,345,678,901,234,567,890.12"
    )
