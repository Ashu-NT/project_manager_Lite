from __future__ import annotations

from datetime import date

import pytest

from src.core.modules.project_management.domain.calendar.assignment import (
    ProjectCalendarAssignment,
    ResourceCalendarAssignment,
)
from src.core.platform.common.exceptions import ValidationError


def test_project_calendar_assignment_dto_normalizes_and_validates_fields() -> None:
    assignment = ProjectCalendarAssignment.create(
        project_id="  proj-1  ",
        calendar_id="  cal-1  ",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        priority="2",
    )

    assert assignment.project_id == "proj-1"
    assert assignment.calendar_id == "cal-1"
    assert assignment.priority == 2

    with pytest.raises(ValidationError) as exc_id:
        ProjectCalendarAssignment(id=" ", project_id="proj-1", calendar_id="cal-1")
    assert exc_id.value.code == "PROJECT_CALENDAR_ASSIGNMENT_ID_REQUIRED"

    with pytest.raises(ValidationError) as exc_project:
        ProjectCalendarAssignment.create(project_id=" ", calendar_id="cal-1")
    assert exc_project.value.code == "PROJECT_CALENDAR_ASSIGNMENT_PROJECT_REQUIRED"

    with pytest.raises(ValidationError) as exc_calendar:
        ProjectCalendarAssignment.create(project_id="proj-1", calendar_id=" ")
    assert exc_calendar.value.code == "PROJECT_CALENDAR_ASSIGNMENT_CALENDAR_REQUIRED"

    with pytest.raises(ValidationError) as exc_priority:
        ProjectCalendarAssignment.create(
            project_id="proj-1",
            calendar_id="cal-1",
            priority="high",
        )
    assert exc_priority.value.code == "PM_CALENDAR_ASSIGNMENT_PRIORITY_INVALID"

    with pytest.raises(ValidationError) as exc_range:
        ProjectCalendarAssignment.create(
            project_id="proj-1",
            calendar_id="cal-1",
            effective_from=date(2026, 12, 31),
            effective_to=date(2026, 1, 1),
        )
    assert exc_range.value.code == "PROJECT_CALENDAR_ASSIGNMENT_DATE_RANGE_INVALID"


def test_resource_calendar_assignment_dto_normalizes_and_validates_fields() -> None:
    assignment = ResourceCalendarAssignment.create(
        resource_id="  res-1  ",
        calendar_id="  cal-1  ",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        priority="3",
    )

    assert assignment.resource_id == "res-1"
    assert assignment.calendar_id == "cal-1"
    assert assignment.priority == 3

    with pytest.raises(ValidationError) as exc_id:
        ResourceCalendarAssignment(id=" ", resource_id="res-1", calendar_id="cal-1")
    assert exc_id.value.code == "RESOURCE_CALENDAR_ASSIGNMENT_ID_REQUIRED"

    with pytest.raises(ValidationError) as exc_resource:
        ResourceCalendarAssignment.create(resource_id=" ", calendar_id="cal-1")
    assert exc_resource.value.code == "RESOURCE_CALENDAR_ASSIGNMENT_RESOURCE_REQUIRED"

    with pytest.raises(ValidationError) as exc_calendar:
        ResourceCalendarAssignment.create(resource_id="res-1", calendar_id=" ")
    assert exc_calendar.value.code == "RESOURCE_CALENDAR_ASSIGNMENT_CALENDAR_REQUIRED"

    with pytest.raises(ValidationError) as exc_priority:
        ResourceCalendarAssignment.create(
            resource_id="res-1",
            calendar_id="cal-1",
            priority="high",
        )
    assert exc_priority.value.code == "PM_CALENDAR_ASSIGNMENT_PRIORITY_INVALID"

    with pytest.raises(ValidationError) as exc_range:
        ResourceCalendarAssignment.create(
            resource_id="res-1",
            calendar_id="cal-1",
            effective_from=date(2026, 12, 31),
            effective_to=date(2026, 1, 1),
        )
    assert exc_range.value.code == "RESOURCE_CALENDAR_ASSIGNMENT_DATE_RANGE_INVALID"
