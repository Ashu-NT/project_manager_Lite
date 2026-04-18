from __future__ import annotations
from datetime import date
from typing import List
from core.modules.project_management.domain.calendar import CalendarEvent
from core.modules.project_management.domain.task import Task
from core.modules.project_management.interfaces import CalendarEventRepository, TaskRepository

from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.auth.authorization import require_permission
from core.modules.project_management.services.common.module_guard import ProjectManagementModuleGuardMixin
from sqlalchemy.orm import Session

class CalendarService(ProjectManagementModuleGuardMixin):
    """
    Calendar module:
    - Create manual events
    - Generate events from tasks
    - List events by project or date range
    """

    def __init__(
        self,
        session: Session,
        calendar_repo: CalendarEventRepository,
        task_repo: TaskRepository,
        user_session=None,
        module_catalog_service=None,
    ):
        self._session: Session = session
        self._calendar_repo: CalendarEventRepository = calendar_repo
        self._task_repo: TaskRepository = task_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service
        
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
        require_permission(self._user_session, "task.manage", operation_label="create calendar event")
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
        require_permission(self._user_session, "task.manage", operation_label="sync task to calendar")
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
        require_permission(self._user_session, "task.read", operation_label="list calendar events")
        return self._calendar_repo.list_for_project(project_id)

    def list_events_in_range(self, start: date, end: date) -> List[CalendarEvent]:
        require_permission(self._user_session, "task.read", operation_label="list calendar events in range")
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
        require_permission(self._user_session, "task.manage", operation_label="update calendar event")
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
        require_permission(self._user_session, "task.manage", operation_label="delete calendar event")
        if not self._calendar_repo.get(event_id):
            raise NotFoundError("Calendar event not found.", code="EVENT_NOT_FOUND")
        try:
            self._calendar_repo.delete(event_id)
            self._session.commit()
        except Exception as e:  
            self._session.rollback()
            raise e

