from __future__ import annotations
from datetime import date
from typing import List
from core.models import CalendarEvent, Task
from core.interfaces import CalendarEventRepository, TaskRepository

from core.exceptions import NotFoundError, ValidationError
from sqlalchemy.orm import Session

class CalendarService:
    """
    Calendar module:
    - Create manual events
    - Generate events from tasks
    - List events by project or date range
    """

    def __init__(self, session: Session,calendar_repo: CalendarEventRepository, task_repo: TaskRepository):
        self._session = session
        self._calendar_repo = calendar_repo
        self._task_repo = task_repo
        
    def create_event(
        self,
        title: str,
        start_date: date,
        end_date: date,
        project_id: str | None = None,
        task_id: str | None = None,
        all_day: bool = True,
        description: str = "",
    ) -> CalendarEvent:
        event = CalendarEvent.create(
            title=title,
            start_date=start_date,
            end_date=end_date,
            project_id=project_id,
            task_id=task_id,
            all_day=all_day,
            description=description,
        )
        try:
            self._calendar_repo.add(event)
            self._session.commit()
            return event
        except Exception as e:
            self._session.rollback()
            raise e

    def sync_task_to_calendar(self, task: Task) -> CalendarEvent | None:
        """
        Simple rule: if task has start & end dates, create a calendar event.
        In a more advanced version, you'd update existing events or keep them in sync.
        """
        if not (task.start_date and task.end_date):
            return None

        title = f"Task: {task.name}"
        event = CalendarEvent.create(
            title=title,
            start_date=task.start_date,
            end_date=task.end_date,
            project_id=task.project_id,
            task_id=task.id,
            all_day=True,
            description=task.description,
        )
        try:
            self._calendar_repo.add(event)
            self._session.commit()
            
        except Exception as e:
            self._session.rollback()
            raise e
        return event

    def list_events_for_project(self, project_id: str) -> List[CalendarEvent]:
        return self._calendar_repo.list_for_project(project_id)

    def list_events_in_range(self, start: date, end: date) -> List[CalendarEvent]:
        return self._calendar_repo.list_range(start, end)

    def update_event(
        self,
        event_id: str,
        title: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        description: str | None = None,
        all_day: bool | None = None,
    ) -> CalendarEvent:
        event = self._calendar_repo.get(event_id)
        if not event:
            raise NotFoundError("Calendar event not found.", code="EVENT_NOT_FOUND")

        if title is not None:
            event.title = title.strip()
        if start_date is not None:
            event.start_date = start_date
        if end_date is not None:
            if event.start_date and end_date < event.start_date:
                raise ValidationError("Event end date cannot be before start date.")
            event.end_date = end_date
        if description is not None:
            event.description = description.strip()
        if all_day is not None:
            event.all_day = all_day

        try:
            self._calendar_repo.update(event)
            self._session.commit()
            return event
        except Exception as e:
            self._session.rollback()
            raise e

    def delete_event(self, event_id: str) -> None:
        if not self._calendar_repo.get(event_id):
            raise NotFoundError("Calendar event not found.", code="EVENT_NOT_FOUND")
        try:
            self._calendar_repo.delete(event_id)
            self._session.commit()
        except Exception as e:  
            self._session.rollback()
            raise e

