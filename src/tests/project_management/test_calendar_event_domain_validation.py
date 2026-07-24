from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from src.core.modules.project_management.application.scheduling.calendars.calendar_service import (
    CalendarService,
)
from src.core.modules.project_management.domain.scheduling.calendar import CalendarEvent
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.platform.common.exceptions import NotFoundError, ValidationError


class _FakeSession:
    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


class _FakeCalendarRepo:
    def __init__(self) -> None:
        self._events: dict[str, CalendarEvent] = {}

    def add(self, event: CalendarEvent) -> None:
        self._events[event.id] = event

    def get(self, event_id: str) -> CalendarEvent | None:
        return self._events.get(event_id)

    def update(self, event: CalendarEvent) -> None:
        if event.id not in self._events:
            raise NotFoundError("Calendar event not found.", code="EVENT_NOT_FOUND")
        self._events[event.id] = event

    def delete(self, event_id: str) -> None:
        self._events.pop(event_id, None)

    def list_for_project(self, project_id: str) -> list[CalendarEvent]:
        return [event for event in self._events.values() if event.project_id == project_id]

    def list_range(self, start_date: date, end_date: date) -> list[CalendarEvent]:
        return [
            event
            for event in self._events.values()
            if event.end_date >= start_date and event.start_date <= end_date
        ]


class _FakeTaskRepo:
    def __init__(self, tasks: list[Task] | None = None) -> None:
        self._tasks = {task.id: task for task in tasks or []}

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)


def _make_service(monkeypatch: pytest.MonkeyPatch, *, tasks: list[Task] | None = None) -> CalendarService:
    monkeypatch.setattr(
        "src.core.modules.project_management.application.scheduling.calendars.calendar_service.require_permission",
        lambda *args, **kwargs: None,
    )
    return CalendarService(
        session=_FakeSession(),
        calendar_repo=_FakeCalendarRepo(),
        task_repo=_FakeTaskRepo(tasks),
        user_session=object(),
    )


def test_calendar_event_dto_normalizes_and_validates_fields():
    event = CalendarEvent.create(
        title="  Planning Session  ",
        start_date=date(2026, 5, 10),
        end_date=date(2026, 5, 12),
        project_id="  proj-1  ",
        task_id="  task-1  ",
        description="  Initial plan  ",
    )

    assert event.title == "Planning Session"
    assert event.project_id == "proj-1"
    assert event.task_id == "task-1"
    assert event.description == "Initial plan"


def test_calendar_event_dto_rejects_invalid_local_fields():
    with pytest.raises(ValidationError) as exc_title:
        CalendarEvent.create(
            title=" ",
            start_date=date(2026, 5, 10),
            end_date=date(2026, 5, 12),
            project_id="proj-1",
        )
    assert exc_title.value.code == "EVENT_TITLE_EMPTY"

    with pytest.raises(ValidationError) as exc_project:
        CalendarEvent.create(
            title="Planning Session",
            start_date=date(2026, 5, 10),
            end_date=date(2026, 5, 12),
            project_id=" ",
        )
    assert exc_project.value.code == "EVENT_PROJECT_REQUIRED"

    with pytest.raises(ValidationError) as exc_range:
        CalendarEvent.create(
            title="Planning Session",
            start_date=date(2026, 5, 12),
            end_date=date(2026, 5, 10),
            project_id="proj-1",
        )
    assert exc_range.value.code == "EVENT_DATE_RANGE_INVALID"


def test_calendar_service_create_event_rejects_task_project_mismatch(monkeypatch: pytest.MonkeyPatch):
    task = Task.create(
        project_id="proj-b",
        name="Foreign Task",
        start_date=date(2026, 5, 10),
        end_date=date(2026, 5, 12),
    )
    service = _make_service(monkeypatch, tasks=[task])

    with pytest.raises(ValidationError) as exc:
        service.create_event(
            title="Task Review",
            start_date=date(2026, 5, 10),
            end_date=date(2026, 5, 12),
            project_id="proj-a",
            task_id=task.id,
        )
    assert exc.value.code == "TASK_PROJECT_MISMATCH"


def test_calendar_service_update_event_validates_final_state(monkeypatch: pytest.MonkeyPatch):
    service = _make_service(monkeypatch)
    event = service.create_event(
        title="Planning Session",
        start_date=date(2026, 5, 10),
        end_date=date(2026, 5, 12),
        project_id="proj-1",
        description="Initial plan",
    )

    updated = service.update_event(
        event.id,
        title="  Updated Session  ",
        description="  Updated plan  ",
        all_day=False,
    )
    assert updated.title == "Updated Session"
    assert updated.description == "Updated plan"
    assert updated.all_day is False

    with pytest.raises(ValidationError) as exc:
        service.update_event(
            event.id,
            start_date=date(2026, 5, 13),
            end_date=date(2026, 5, 11),
        )
    assert exc.value.code == "EVENT_DATE_RANGE_INVALID"
