from __future__ import annotations

from typing import Set

from core.models import (
    BaselineTask,
    CalendarEvent,
    CostItem,
    CostType,
    Holiday,
    Project,
    ProjectBaseline,
    ProjectResource,
    Resource,
    Task,
    TaskAssignment,
    TaskDependency,
    WorkingCalendar,
)
from infra.db.models import (
    BaselineTaskORM,
    CalendarEventORM,
    CostItemORM,
    HolidayORM,
    ProjectBaselineORM,
    ProjectORM,
    ProjectResourceORM,
    ResourceORM,
    TaskAssignmentORM,
    TaskDependencyORM,
    TaskORM,
    WorkingCalendarORM,
)


def project_to_orm(project: Project) -> ProjectORM:
    return ProjectORM(
        id=project.id,
        name=project.name,
        description=project.description,
        start_date=project.start_date,
        end_date=project.end_date,
        status=project.status,
        client_name=project.client_name,
        client_contact=project.client_contact,
        planned_budget=project.planned_budget,
        currency=project.currency,
    )


def project_from_orm(obj: ProjectORM) -> Project:
    return Project(
        id=obj.id,
        name=obj.name,
        description=obj.description,
        start_date=obj.start_date,
        end_date=obj.end_date,
        status=obj.status,
        client_name=obj.client_name,
        client_contact=obj.client_contact,
        planned_budget=obj.planned_budget,
        currency=obj.currency,
    )


def task_to_orm(task: Task) -> TaskORM:
    return TaskORM(
        id=task.id,
        project_id=task.project_id,
        name=task.name,
        description=task.description,
        start_date=task.start_date,
        end_date=task.end_date,
        duration_days=task.duration_days,
        status=task.status,
        priority=task.priority,
        percent_complete=task.percent_complete,
        actual_start=task.actual_start,
        actual_end=task.actual_end,
        deadline=task.deadline,
    )


def task_from_orm(obj: TaskORM) -> Task:
    return Task(
        id=obj.id,
        project_id=obj.project_id,
        name=obj.name,
        description=obj.description,
        start_date=obj.start_date,
        end_date=obj.end_date,
        duration_days=obj.duration_days,
        status=obj.status,
        priority=obj.priority,
        percent_complete=obj.percent_complete,
        actual_start=obj.actual_start,
        actual_end=obj.actual_end,
        deadline=obj.deadline,
    )


def resource_to_orm(resource: Resource) -> ResourceORM:
    return ResourceORM(
        id=resource.id,
        name=resource.name,
        role=resource.role,
        hourly_rate=resource.hourly_rate,
        is_active=resource.is_active,
        cost_type=resource.cost_type,
        currency_code=resource.currency_code,
    )


def resource_from_orm(obj: ResourceORM) -> Resource:
    return Resource(
        id=obj.id,
        name=obj.name,
        role=obj.role,
        hourly_rate=obj.hourly_rate,
        is_active=obj.is_active,
        cost_type=obj.cost_type,
        currency_code=obj.currency_code,
    )


def assignment_to_orm(assignment: TaskAssignment) -> TaskAssignmentORM:
    return TaskAssignmentORM(
        id=assignment.id,
        task_id=assignment.task_id,
        resource_id=assignment.resource_id,
        project_resource_id=getattr(assignment, "project_resource_id", None),
        allocation_percent=assignment.allocation_percent,
        hours_logged=getattr(assignment, "hours_logged", 0.0),
    )


def assignment_from_orm(obj: TaskAssignmentORM) -> TaskAssignment:
    return TaskAssignment(
        id=obj.id,
        task_id=obj.task_id,
        resource_id=obj.resource_id,
        project_resource_id=getattr(obj, "project_resource_id", None),
        allocation_percent=obj.allocation_percent,
        hours_logged=getattr(obj, "hours_logged", 0.0),
    )


def dependency_to_orm(dependency: TaskDependency) -> TaskDependencyORM:
    return TaskDependencyORM(
        id=dependency.id,
        predecessor_task_id=dependency.predecessor_task_id,
        successor_task_id=dependency.successor_task_id,
        dependency_type=dependency.dependency_type,
        lag_days=dependency.lag_days,
    )


def dependency_from_orm(obj: TaskDependencyORM) -> TaskDependency:
    return TaskDependency(
        id=obj.id,
        predecessor_task_id=obj.predecessor_task_id,
        successor_task_id=obj.successor_task_id,
        dependency_type=obj.dependency_type,
        lag_days=obj.lag_days,
    )


def cost_to_orm(cost: CostItem) -> CostItemORM:
    return CostItemORM(
        id=cost.id,
        project_id=cost.project_id,
        task_id=cost.task_id,
        description=cost.description,
        planned_amount=cost.planned_amount,
        actual_amount=cost.actual_amount,
        committed_amount=cost.committed_amount,
        cost_type=(cost.cost_type.value if hasattr(cost.cost_type, "value") else cost.cost_type),
        incurred_date=cost.incurred_date,
        currency_code=cost.currency_code,
    )


def cost_from_orm(obj: CostItemORM) -> CostItem:
    return CostItem(
        id=obj.id,
        project_id=obj.project_id,
        task_id=obj.task_id,
        description=obj.description,
        planned_amount=obj.planned_amount,
        committed_amount=obj.committed_amount,
        actual_amount=obj.actual_amount,
        cost_type=CostType(obj.cost_type) if obj.cost_type else CostType.OVERHEAD,
        incurred_date=obj.incurred_date,
        currency_code=obj.currency_code,
    )


def event_to_orm(event: CalendarEvent) -> CalendarEventORM:
    return CalendarEventORM(
        id=event.id,
        title=event.title,
        start_date=event.start_date,
        end_date=event.end_date,
        project_id=event.project_id,
        task_id=event.task_id,
        all_day=event.all_day,
        description=event.description,
    )


def event_from_orm(obj: CalendarEventORM) -> CalendarEvent:
    return CalendarEvent(
        id=obj.id,
        title=obj.title,
        start_date=obj.start_date,
        end_date=obj.end_date,
        project_id=obj.project_id,
        task_id=obj.task_id,
        all_day=obj.all_day,
        description=obj.description,
    )


def calendar_from_orm(obj: WorkingCalendarORM) -> WorkingCalendar:
    days: Set[int] = set()
    if obj.working_days:
        for part in obj.working_days.split(","):
            part = part.strip()
            if part:
                days.add(int(part))
    return WorkingCalendar(
        id=obj.id,
        name=obj.name,
        working_days=days,
        hours_per_day=obj.hours_per_day,
    )


def calendar_to_orm(calendar: WorkingCalendar) -> WorkingCalendarORM:
    wd_str = ",".join(str(day) for day in sorted(calendar.working_days))
    return WorkingCalendarORM(
        id=calendar.id,
        name=calendar.name,
        working_days=wd_str,
        hours_per_day=calendar.hours_per_day,
    )


def holiday_from_orm(obj: HolidayORM) -> Holiday:
    return Holiday(
        id=obj.id,
        calendar_id=obj.calendar_id,
        date=obj.date,
        name=obj.name,
    )


def holiday_to_orm(holiday: Holiday) -> HolidayORM:
    return HolidayORM(
        id=holiday.id,
        calendar_id=holiday.calendar_id,
        date=holiday.date,
        name=holiday.name,
    )


def baseline_from_orm(obj: ProjectBaselineORM) -> ProjectBaseline:
    return ProjectBaseline(
        id=obj.id,
        project_id=obj.project_id,
        name=obj.name,
        created_at=obj.created_at,
    )


def baseline_to_orm(baseline: ProjectBaseline) -> ProjectBaselineORM:
    return ProjectBaselineORM(
        id=baseline.id,
        project_id=baseline.project_id,
        name=baseline.name,
        created_at=baseline.created_at,
    )


def baseline_task_from_orm(obj: BaselineTaskORM) -> BaselineTask:
    return BaselineTask(
        id=obj.id,
        baseline_id=obj.baseline_id,
        task_id=obj.task_id,
        baseline_start=obj.baseline_start,
        baseline_finish=obj.baseline_finish,
        baseline_duration_days=obj.baseline_duration_days,
        baseline_planned_cost=obj.baseline_planned_cost,
    )


def baseline_task_to_orm(task: BaselineTask) -> BaselineTaskORM:
    return BaselineTaskORM(
        id=task.id,
        baseline_id=task.baseline_id,
        task_id=task.task_id,
        baseline_start=task.baseline_start,
        baseline_finish=task.baseline_finish,
        baseline_duration_days=task.baseline_duration_days,
        baseline_planned_cost=task.baseline_planned_cost,
    )


def project_resource_from_orm(obj: ProjectResourceORM) -> ProjectResource:
    return ProjectResource(
        id=obj.id,
        project_id=obj.project_id,
        resource_id=obj.resource_id,
        hourly_rate=obj.hourly_rate,
        currency_code=obj.currency_code,
        planned_hours=obj.planned_hours,
        is_active=obj.is_active,
    )


def project_resource_to_orm(resource: ProjectResource) -> ProjectResourceORM:
    return ProjectResourceORM(
        id=resource.id,
        project_id=resource.project_id,
        resource_id=resource.resource_id,
        hourly_rate=resource.hourly_rate,
        currency_code=resource.currency_code,
        planned_hours=resource.planned_hours,
        is_active=resource.is_active,
    )


__all__ = [
    "project_to_orm",
    "project_from_orm",
    "task_to_orm",
    "task_from_orm",
    "resource_to_orm",
    "resource_from_orm",
    "assignment_to_orm",
    "assignment_from_orm",
    "dependency_to_orm",
    "dependency_from_orm",
    "cost_to_orm",
    "cost_from_orm",
    "event_to_orm",
    "event_from_orm",
    "calendar_from_orm",
    "calendar_to_orm",
    "holiday_from_orm",
    "holiday_to_orm",
    "baseline_from_orm",
    "baseline_to_orm",
    "baseline_task_from_orm",
    "baseline_task_to_orm",
    "project_resource_from_orm",
    "project_resource_to_orm",
]
