from __future__ import annotations

import logging
from datetime import date

from core.events.domain_events import domain_events
from core.exceptions import NotFoundError, ValidationError
from core.models import Project, ProjectStatus
from core.services.project.validation import ProjectValidationMixin

logger = logging.getLogger(__name__)
DEFAULT_CURRENCY_CODE = "EUR"


class ProjectLifecycleMixin(ProjectValidationMixin):
    def create_project(
        self,
        name: str,
        description: str = "",
        client_name: str | None = None,
        client_contact: str | None = None,
        planned_budget: float | None = None,
        currency: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Project:
        self._validate_project_name(name)
        resolved_currency = (currency or "").strip().upper() or DEFAULT_CURRENCY_CODE
        project = Project.create(
            name=name.strip(),
            description=description.strip(),
            client_name=(client_name or "").strip() or None,
            client_contact=(client_contact or "").strip() or None,
            planned_budget=planned_budget,
            currency=resolved_currency,
            start_date=start_date,
            end_date=end_date,
        )

        try:
            self._project_repo.add(project)
            self._session.commit()
            logger.info("Created project %s - %s", project.id, project.name)
            domain_events.project_changed.emit(project.id)
            return project
        except Exception as e:
            self._session.rollback()
            logger.error("Error creating project: %s", e)
            raise

    def set_status(self, project_id: str, status: ProjectStatus) -> None:
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found")

        project.status = status
        try:
            self._project_repo.update(project)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    def update_dates_from_tasks(self, project_id: str) -> None:
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found")

        tasks = self._task_repo.list_by_project(project_id)
        if not tasks:
            return

        start_dates = [task.start_date for task in tasks if task.start_date]
        end_dates = [task.end_date for task in tasks if task.end_date]

        if start_dates:
            project.start_date = min(start_dates)
        if end_dates:
            project.end_date = max(end_dates)

        self._project_repo.update(project)

    def update_project(
        self,
        project_id: str,
        name: str | None = None,
        description: str | None = None,
        status: ProjectStatus | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        client_name: str | None = None,
        client_contact: str | None = None,
        planned_budget: float | None = None,
        currency: str | None = None,
    ) -> Project:
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        if name is not None:
            if not name.strip():
                raise ValidationError("Project name cannot be empty.", code="PROJECT_NAME_EMPTY")
            project.name = name.strip()
        if description is not None:
            project.description = description.strip()
        if status is not None:
            project.status = status
        if start_date is not None:
            project.start_date = start_date
        if end_date is not None:
            if project.start_date and end_date < project.start_date:
                raise ValidationError("Project end date cannot be before start date.")
            project.end_date = end_date
        if client_name is not None:
            project.client_name = client_name.strip() or None
        if client_contact is not None:
            project.client_contact = client_contact.strip() or None
        if planned_budget is not None:
            if planned_budget < 0:
                raise ValidationError("Planned budget cannot be negative.")
            project.planned_budget = planned_budget
        if currency is not None:
            project.currency = currency.strip().upper() or None

        try:
            self._project_repo.update(project)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        domain_events.project_changed.emit(project_id)
        return project

    def delete_project(self, project_id: str) -> None:
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found")

        try:
            tasks = self._task_repo.list_by_project(project_id)
            for task in tasks:
                self._dependency_repo.delete_for_task(task.id)
                self._assignment_repo.delete_by_task(task.id)
                self._calendar_repo.delete_for_task(task.id)
                self._task_repo.delete(task.id)

            self._cost_repo.delete_by_project(project_id)
            self._calendar_repo.delete_for_project(project_id)
            self._project_repo.delete(project_id)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        domain_events.project_changed.emit(project_id)


__all__ = ["ProjectLifecycleMixin", "DEFAULT_CURRENCY_CODE"]
