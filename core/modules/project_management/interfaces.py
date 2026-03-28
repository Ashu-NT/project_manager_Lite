from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from core.modules.project_management.domain.baseline import BaselineTask, ProjectBaseline
from core.modules.project_management.domain.calendar import CalendarEvent, Holiday, WorkingCalendar
from core.modules.project_management.domain.collaboration import TaskComment, TaskPresence
from core.modules.project_management.domain.cost import CostItem
from core.modules.project_management.domain.portfolio import (
    PortfolioIntakeItem,
    PortfolioProjectDependency,
    PortfolioScoringTemplate,
    PortfolioScenario,
)
from core.modules.project_management.domain.project import Project, ProjectResource
from core.modules.project_management.domain.register import (
    RegisterEntry,
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from core.modules.project_management.domain.resource import Resource
from core.modules.project_management.domain.task import Task, TaskAssignment, TaskDependency


class ProjectRepository(ABC):
    @abstractmethod
    def add(self, project: Project) -> None: ...

    @abstractmethod
    def update(self, project: Project) -> None: ...

    @abstractmethod
    def delete(self, project_id: str) -> None: ...

    @abstractmethod
    def get(self, project_id: str) -> Optional[Project]: ...

    @abstractmethod
    def list_all(self) -> List[Project]: ...


class ProjectResourceRepository(ABC):
    @abstractmethod
    def add(self, pr: ProjectResource) -> None: ...

    @abstractmethod
    def get(self, pr_id: str) -> Optional[ProjectResource]: ...

    @abstractmethod
    def list_by_project(self, project_id: str) -> List[ProjectResource]: ...

    @abstractmethod
    def get_for_project(self, project_id: str, resource_id: str) -> Optional[ProjectResource]: ...

    @abstractmethod
    def delete(self, pr_id: str) -> None: ...

    @abstractmethod
    def delete_by_resource(self, res_id: str) -> None: ...

    @abstractmethod
    def update(self, pr: ProjectResource) -> None: ...


class TaskRepository(ABC):
    @abstractmethod
    def add(self, task: Task) -> None: ...

    @abstractmethod
    def update(self, task: Task) -> None: ...

    @abstractmethod
    def delete(self, task_id: str) -> None: ...

    @abstractmethod
    def get(self, task_id: str) -> Optional[Task]: ...

    @abstractmethod
    def list_by_project(self, project_id: str) -> List[Task]: ...


class ResourceRepository(ABC):
    @abstractmethod
    def add(self, resource: Resource) -> None: ...

    @abstractmethod
    def update(self, resource: Resource) -> None: ...

    @abstractmethod
    def delete(self, resource_id: str) -> None: ...

    @abstractmethod
    def get(self, resource_id: str) -> Optional[Resource]: ...

    @abstractmethod
    def list_all(self) -> List[Resource]: ...

    @abstractmethod
    def list_by_employee(self, employee_id: str) -> List[Resource]: ...


class AssignmentRepository(ABC):
    @abstractmethod
    def add(self, assignment: TaskAssignment) -> None: ...

    @abstractmethod
    def get(self, assignment_id: str) -> Optional[TaskAssignment]: ...

    @abstractmethod
    def list_by_task(self, task_id: str) -> List[TaskAssignment]: ...

    @abstractmethod
    def list_by_resource(self, resource_id: str) -> List[TaskAssignment]: ...

    @abstractmethod
    def update(self, assignment: TaskAssignment) -> None: ...

    @abstractmethod
    def delete(self, assignment_id: str) -> None: ...

    @abstractmethod
    def delete_by_task(self, task_id: str) -> None: ...

    @abstractmethod
    def list_by_assignment(self, task_id: str) -> List[TaskAssignment]: ...

    @abstractmethod
    def list_by_tasks(self, task_ids: List[str]) -> List[TaskAssignment]: ...


class TaskCommentRepository(ABC):
    @abstractmethod
    def add(self, comment: TaskComment) -> None: ...

    @abstractmethod
    def update(self, comment: TaskComment) -> None: ...

    @abstractmethod
    def get(self, comment_id: str) -> Optional[TaskComment]: ...

    @abstractmethod
    def list_by_task(self, task_id: str) -> List[TaskComment]: ...

    @abstractmethod
    def list_recent_for_tasks(self, task_ids: List[str], limit: int = 200) -> List[TaskComment]: ...


class TaskPresenceRepository(ABC):
    @abstractmethod
    def touch(
        self,
        *,
        task_id: str,
        user_id: str | None,
        username: str,
        display_name: str | None,
        activity: str,
    ) -> TaskPresence: ...

    @abstractmethod
    def clear(self, *, task_id: str, username: str) -> None: ...

    @abstractmethod
    def list_recent_for_tasks(
        self,
        task_ids: List[str],
        *,
        since,
        limit: int = 200,
    ) -> List[TaskPresence]: ...


class DependencyRepository(ABC):
    @abstractmethod
    def add(self, dependency: TaskDependency) -> None: ...

    @abstractmethod
    def get(self, dependency_id: str) -> Optional[TaskDependency]: ...

    @abstractmethod
    def list_by_project(self, project_id: str) -> List[TaskDependency]: ...

    @abstractmethod
    def delete(self, dependency_id: str) -> None: ...

    @abstractmethod
    def delete_for_task(self, task_id: str) -> None: ...

    @abstractmethod
    def list_by_task(self, task_id: str) -> List[TaskDependency]: ...


class CostRepository(ABC):
    @abstractmethod
    def add(self, cost_item: CostItem) -> None: ...

    @abstractmethod
    def update(self, cost_item: CostItem) -> None: ...

    @abstractmethod
    def delete(self, cost_id: str) -> None: ...

    @abstractmethod
    def list_by_project(self, project_id: str) -> List[CostItem]: ...

    @abstractmethod
    def delete_by_project(self, project_id: str) -> None: ...

    @abstractmethod
    def get(self, cost_id: str) -> Optional[CostItem]: ...


class CalendarEventRepository(ABC):
    @abstractmethod
    def add(self, event: CalendarEvent) -> None: ...

    @abstractmethod
    def update(self, event: CalendarEvent) -> None: ...

    @abstractmethod
    def delete(self, event_id: str) -> None: ...

    @abstractmethod
    def get(self, event_id: str) -> Optional[CalendarEvent]: ...

    @abstractmethod
    def list_for_project(self, project_id: str) -> List[CalendarEvent]: ...

    @abstractmethod
    def list_range(self, start_date, end_date) -> List[CalendarEvent]: ...

    @abstractmethod
    def delete_for_task(self, task_id: str) -> None: ...

    @abstractmethod
    def delete_for_project(self, project_id: str) -> None: ...


class WorkingCalendarRepository(ABC):
    @abstractmethod
    def get(self, calendar_id: str) -> Optional[WorkingCalendar]: ...

    @abstractmethod
    def get_default(self) -> Optional[WorkingCalendar]: ...

    @abstractmethod
    def upsert(self, calendar: WorkingCalendar) -> None: ...

    @abstractmethod
    def list_holidays(self, calendar_id: str) -> List[Holiday]: ...

    @abstractmethod
    def add_holiday(self, holiday: Holiday) -> None: ...

    @abstractmethod
    def delete_holiday(self, holiday_id: str) -> None: ...


class BaselineRepository(ABC):
    @abstractmethod
    def add_baseline(self, b: ProjectBaseline) -> ProjectBaseline: ...

    @abstractmethod
    def get_baseline(self, baseline_id: str) -> Optional[ProjectBaseline]: ...

    @abstractmethod
    def get_latest_for_project(self, project_id: str) -> Optional[ProjectBaseline]: ...

    @abstractmethod
    def list_for_project(self, project_id: str) -> List[ProjectBaseline]: ...

    @abstractmethod
    def delete_baseline(self, baseline_id: str) -> None: ...

    @abstractmethod
    def add_baseline_tasks(self, tasks: List[BaselineTask]) -> None: ...

    @abstractmethod
    def list_tasks(self, baseline_id: str) -> List[BaselineTask]: ...

    @abstractmethod
    def delete_tasks(self, baseline_id: str) -> None: ...


class RegisterEntryRepository(ABC):
    @abstractmethod
    def add(self, entry: RegisterEntry) -> None: ...

    @abstractmethod
    def update(self, entry: RegisterEntry) -> None: ...

    @abstractmethod
    def delete(self, entry_id: str) -> None: ...

    @abstractmethod
    def get(self, entry_id: str) -> Optional[RegisterEntry]: ...

    @abstractmethod
    def list_entries(
        self,
        *,
        project_id: str | None = None,
        entry_type: RegisterEntryType | None = None,
        status: RegisterEntryStatus | None = None,
        severity: RegisterEntrySeverity | None = None,
    ) -> List[RegisterEntry]: ...


class PortfolioIntakeRepository(ABC):
    @abstractmethod
    def add(self, item: PortfolioIntakeItem) -> None: ...

    @abstractmethod
    def update(self, item: PortfolioIntakeItem) -> None: ...

    @abstractmethod
    def get(self, item_id: str) -> Optional[PortfolioIntakeItem]: ...

    @abstractmethod
    def list_all(self) -> List[PortfolioIntakeItem]: ...

    @abstractmethod
    def delete(self, item_id: str) -> None: ...


class PortfolioScenarioRepository(ABC):
    @abstractmethod
    def add(self, scenario: PortfolioScenario) -> None: ...

    @abstractmethod
    def update(self, scenario: PortfolioScenario) -> None: ...

    @abstractmethod
    def get(self, scenario_id: str) -> Optional[PortfolioScenario]: ...

    @abstractmethod
    def list_all(self) -> List[PortfolioScenario]: ...

    @abstractmethod
    def delete(self, scenario_id: str) -> None: ...


class PortfolioProjectDependencyRepository(ABC):
    @abstractmethod
    def add(self, dependency: PortfolioProjectDependency) -> None: ...

    @abstractmethod
    def get(self, dependency_id: str) -> Optional[PortfolioProjectDependency]: ...

    @abstractmethod
    def list_all(self) -> List[PortfolioProjectDependency]: ...

    @abstractmethod
    def delete(self, dependency_id: str) -> None: ...


class PortfolioScoringTemplateRepository(ABC):
    @abstractmethod
    def add(self, template: PortfolioScoringTemplate) -> None: ...

    @abstractmethod
    def update(self, template: PortfolioScoringTemplate) -> None: ...

    @abstractmethod
    def get(self, template_id: str) -> Optional[PortfolioScoringTemplate]: ...

    @abstractmethod
    def list_all(self) -> List[PortfolioScoringTemplate]: ...


__all__ = [
    "AssignmentRepository",
    "BaselineRepository",
    "CalendarEventRepository",
    "CostRepository",
    "DependencyRepository",
    "PortfolioIntakeRepository",
    "PortfolioProjectDependencyRepository",
    "PortfolioScenarioRepository",
    "PortfolioScoringTemplateRepository",
    "ProjectRepository",
    "ProjectResourceRepository",
    "RegisterEntryRepository",
    "ResourceRepository",
    "TaskCommentRepository",
    "TaskPresenceRepository",
    "TaskRepository",
    "WorkingCalendarRepository",
]
