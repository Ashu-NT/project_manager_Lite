from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional, Set
from uuid import uuid4


def generate_id() -> str:
    return str(uuid4())

# ---------- Enums ----------

class ProjectStatus(str, Enum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"

class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    DONE = "DONE"

class DependencyType(str, Enum):
    FINISH_TO_START = "FS"
    FINISH_TO_FINISH = "FF"
    START_TO_START = "SS"
    START_TO_FINISH = "SF"


class CostType(str, Enum):
    LABOR = "LABOR"
    MATERIAL = "MATERIAL"
    OVERHEAD = "OVERHEAD"
    EQUIPMENT = "EQUIPMENT"
    CONTINGENCY = "CONTINGENCY"
    SUBCONTRACT = "SUBCONTRACT"
    OTHER = "OTHER"

# ---------- Core models ----------

@dataclass
class Project:
    id: str
    name: str
    description: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: ProjectStatus = ProjectStatus.PLANNED
    
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    planned_budget: Optional[float] = None
    currency: Optional[str] = None #' EUR, USD, etc.'

    @staticmethod
    def create(name: str, description: str = "",**extra) -> "Project":
        return Project(
            id=generate_id(), 
            name=name, 
            description=description,
            **extra
        )

@dataclass
class ProjectResource:
    id: str
    project_id: str
    resource_id: str
    
    hourly_rate: Optional[float] = None  # overrides Resource hourly_rate if set
    currency_code: Optional[str] = None  # overrides Resource currency_code if set
    
    planned_hours: float = 0.0
    is_active: bool = True
    
    @staticmethod
    def create(
        project_id: str, 
        resource_id: str,
        hourly_rate: Optional[float] = None,
        currency_code: Optional[str] = None,
        planned_hours: float = 0.0,
        is_active: bool = True,
        ) -> "ProjectResource":
        return ProjectResource(
            id=generate_id(),
            project_id=project_id,
            resource_id=resource_id,
            hourly_rate=hourly_rate,
            currency_code=currency_code,
            planned_hours=planned_hours,
            is_active=is_active,
        )

@dataclass
class Task:
    id: str
    project_id: str
    name: str
    description: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    duration_days: Optional[int] = None
    status: TaskStatus = TaskStatus.TODO
    priority: int = 0

    # NEW PROGRESS FIELDS
    percent_complete: float = 0.0
    actual_start: Optional[date] = None
    actual_end: Optional[date] = None
    deadline: date | None = None
    

    @staticmethod
    def create(project_id: str, name: str, description: str = "", **extra) -> "Task":
        return Task(id=generate_id(), project_id=project_id, name=name, description=description, **extra)


@dataclass
class Resource:
    id: str
    name: str
    role: str = ""
    hourly_rate: float = 0.0
    is_active: bool = True

    # Category and currency
    cost_type: CostType = CostType.LABOR
    currency_code: Optional[str] = None

    @staticmethod
    def create(
        name: str,
        role: str = "",
        hourly_rate: float = 0.0,
        is_active: bool = True,
        cost_type: CostType = CostType.LABOR,
        currency_code: Optional[str] = None,
    ) -> "Resource":
        return Resource(
            id=generate_id(),
            name=name,
            role=role,
            hourly_rate=hourly_rate,
            is_active=is_active,
            cost_type=cost_type,
            currency_code=currency_code,
        )


@dataclass
class TaskAssignment:
    id: str
    task_id: str
    resource_id: str
    allocation_percent: float = 100.0  # 0–100
    hours_logged: float = 0.0  # total hours logged against this task assignment
    project_resource_id: Optional[str] = None  # link to ProjectResource if applicable

    @staticmethod
    def create(task_id: str, resource_id: str, allocation_percent: float = 100.0, hours_logged: float = 0.0) -> "TaskAssignment":
        return TaskAssignment(
            id=generate_id(),
            task_id=task_id,
            resource_id=resource_id,
            allocation_percent=allocation_percent,
            hours_logged=hours_logged,
        )


@dataclass
class TaskDependency:
    id: str
    predecessor_task_id: str
    successor_task_id: str
    dependency_type: DependencyType = DependencyType.FINISH_TO_START
    lag_days: int = 0  # can be negative for lead time

    @staticmethod
    def create(predecessor_id: str, successor_id: str,
               dependency_type: DependencyType = DependencyType.FINISH_TO_START,lag_days: int=0 ) -> "TaskDependency":
        return TaskDependency(
            id=generate_id(),
            predecessor_task_id=predecessor_id,
            successor_task_id=successor_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
        )


@dataclass
class CostItem:
    id: str
    project_id: str
    task_id: Optional[str]
    description: str
    planned_amount: float
    
    cost_type: CostType = CostType.OVERHEAD
    
    committed_amount: float = 0.0
    actual_amount: float = 0.0
    
    incurred_date: Optional[date] = None
    currency_code: Optional[str] = None

    @staticmethod
    def create(
        project_id: str, 
        description: str, 
        planned_amount: float,
        task_id: Optional[str] = None,
        cost_type: CostType = CostType.OVERHEAD,
        committed_amount: float = 0.0,
        actual_amount: float = 0.0,
        incurred_date: Optional[date] = None,
        currency_code: Optional[str] = None,
        
        ) -> "CostItem":
        return CostItem(
            id=generate_id(),
            project_id=project_id,
            task_id=task_id,
            description=description,
            planned_amount=planned_amount,
            cost_type=cost_type,
            committed_amount=committed_amount, 
            actual_amount=actual_amount,
            incurred_date=incurred_date,
            currency_code = currency_code,
            
        )


# ---------- Calendar module ----------

@dataclass
class CalendarEvent:
    """
    A generic calendar event. It can be linked to a task or project,
    or just be a standalone project-related event (milestone, meeting, etc).
    """
    id: str
    title: str
    start_date: date
    end_date: date
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    all_day: bool = True
    description: str = ""

    @staticmethod
    def create(
        title: str,
        start_date: date,
        end_date: date,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        all_day: bool = True,
        description: str = "",
    ) -> "CalendarEvent":
        return CalendarEvent(
            id=generate_id(),
            title=title,
            start_date=start_date,
            end_date=end_date,
            project_id=project_id,
            task_id=task_id,
            all_day=all_day,
            description=description,
        )
        
@dataclass
class WorkingCalendar:
    id: str
    name: str = "Default"
    # 0=Monday, 6=Sunday
    working_days: Set[int] = field(default_factory=lambda: {0, 1, 2, 3, 4})
    hours_per_day: float = 8.0

    @staticmethod
    def create_default() -> "WorkingCalendar":
        return WorkingCalendar(id="default", name="Default")

@dataclass
class Holiday:
    id: str
    calendar_id: str
    date: date
    name: str = ""

    @staticmethod
    def create(calendar_id: str, date: date, name: str = "") -> "Holiday":
        return Holiday(id=generate_id(), calendar_id=calendar_id, date=date, name=name)
 
#   ----------------------------  EVM + Baseline ------------------------------------    

@dataclass
class ProjectBaseline:
    id: str
    project_id: str
    name: str
    created_at: date

    @staticmethod
    def create(project_id: str, name: str) -> "ProjectBaseline":
        return ProjectBaseline(
            id=generate_id(),
            project_id=project_id,
            name=name.strip() or "Baseline",
            created_at=date.today(),
        )

@dataclass
class BaselineTask:
    id: str
    baseline_id: str
    task_id: str
    baseline_start: Optional[date]
    baseline_finish: Optional[date]
    baseline_duration_days: int
    baseline_planned_cost: float = 0.0

    @staticmethod
    def create(
        baseline_id: str,
        task_id: str,
        baseline_start: Optional[date],
        baseline_finish: Optional[date],
        baseline_duration_days: int,
        baseline_planned_cost: float,
    ) -> "BaselineTask":
        return BaselineTask(
            id=generate_id(),
            baseline_id=baseline_id,
            task_id=task_id,
            baseline_start=baseline_start,
            baseline_finish=baseline_finish,
            baseline_duration_days=max(0, baseline_duration_days),
            baseline_planned_cost=max(0.0, baseline_planned_cost),
        )