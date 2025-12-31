# core/services/project_service.py
from __future__ import annotations
from typing import List
from ..models import Project, ProjectStatus
from ..interfaces import (
    ProjectRepository,
    TaskRepository,
    DependencyRepository,
    AssignmentRepository,
    CalendarEventRepository,
    CostRepository,
)
from ..exceptions import ValidationError, NotFoundError
from sqlalchemy.orm import Session
from datetime import date
import logging
from core.events.domain_events import domain_events

logger = logging.getLogger(__name__)
    
class ProjectService:
    def __init__(
        self,
        session: Session,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        dependency_repo: DependencyRepository,
        assignment_repo: AssignmentRepository,
        calendar_repo: CalendarEventRepository,
        cost_repo: CostRepository,
    ):
        self._session = session
        self._project_repo = project_repo
        self._task_repo = task_repo
        self._dependency_repo = dependency_repo
        self._assignment_repo = assignment_repo
        self._calendar_repo = calendar_repo
        self._cost_repo = cost_repo

    def _validate_project_name(self, name: str) -> None:
        if not name or not name.strip():
            raise ValidationError("Project name cannot be empty.", code="PROJECT_NAME_EMPTY")
        if len(name.strip()) < 3:
            raise ValidationError("Project name must be at least 3 characters.", code="PROJECT_NAME_TOO_SHORT")
        # optional: uniqueness check
        for p in self._project_repo.list_all():
            if p.name.strip().lower() == name.strip().lower():
                raise ValidationError("A project with this name already exists.", code="PROJECT_NAME_DUPLICATE")

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
        project = Project.create(
            name=name.strip(), 
            description=description.strip(),
            client_name=(client_name or "").strip() or None,
            client_contact=(client_contact or "").strip() or None,
            planned_budget=planned_budget,  
            currency=(currency or "").strip() or None,
            start_date=start_date,  
            end_date=end_date,
        )
        try:
            self._project_repo.add(project)
            self._session.commit()
            logger.info(f"Created project {project.id} - {project.name}")
            domain_events.project_changed.emit(project.id)
            return project
        except Exception as e:
            self._session.rollback()
            logger.error(f"Error creating project: {e}")
            raise 
        
        

    def list_projects(self) -> List[Project]:
        return self._project_repo.list_all()

    def get_project(self, project_id: str) -> Project | None:
        return self._project_repo.get(project_id)

    def set_status(self, project_id: str, status: ProjectStatus) -> None:
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found")
        project.status = status
        try:
            self._project_repo.update(project)
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            raise e

    def update_dates_from_tasks(self, project_id: str) -> None:
        """Compute project start/end from its tasks."""
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found")

        tasks = self._task_repo.list_by_project(project_id)
        if not tasks:
            return

        start_dates = [t.start_date for t in tasks if t.start_date]
        end_dates = [t.end_date for t in tasks if t.end_date]

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
            project.currency = currency.strip() or None
        
        try:
            self._project_repo.update(project)
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            raise e
        
        domain_events.project_changed.emit(project_id)
        return project

    def delete_project(self, project_id: str) -> None:
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found")

        try:
            # delete tasks and task-related entities
            tasks = self._task_repo.list_by_project(project_id)
            for t in tasks:
                self._dependency_repo.delete_for_task(t.id)
                self._assignment_repo.delete_by_task(t.id)
                self._calendar_repo.delete_for_task(t.id)
                self._task_repo.delete(t.id)

            # delete project-level cost items
            self._cost_repo.delete_by_project(project_id)

            # delete project-level calendar events
            self._calendar_repo.delete_for_project(project_id)

            # finally delete the project record
            self._project_repo.delete(project_id)
            # session.begin() will commit automatically at end of block
            domain_events.project_changed.emit(project_id)
            
        except Exception as e:
            self._session.rollback()
            raise e
        
    def list_projects_by_status(self, status: ProjectStatus) -> List[Project]:
        return [p for p in self._project_repo.list_all() if p.status == status]

    def search_projects_by_name(self, query: str) -> List[Project]:
        q = query.strip().lower()
        return [p for p in self._project_repo.list_all() if q in p.name.lower()]    
        
        
        
        
        
        