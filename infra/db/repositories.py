"""Compatibility facade for DB repositories and ORM mappers.

New code should import focused modules under ``infra.db.repositories_*`` and
``infra.db.mappers``. This module keeps legacy imports stable.
"""

from infra.db.mappers import (
    assignment_from_orm,
    assignment_to_orm,
    baseline_from_orm,
    baseline_task_from_orm,
    baseline_task_to_orm,
    baseline_to_orm,
    calendar_from_orm,
    calendar_to_orm,
    cost_from_orm,
    cost_to_orm,
    dependency_from_orm,
    dependency_to_orm,
    event_from_orm,
    event_to_orm,
    holiday_from_orm,
    holiday_to_orm,
    project_from_orm,
    project_resource_from_orm,
    project_resource_to_orm,
    project_to_orm,
    resource_from_orm,
    resource_to_orm,
    task_from_orm,
    task_to_orm,
)
from infra.db.repositories_baseline import SqlAlchemyBaselineRepository
from infra.db.repositories_cost_calendar import (
    SqlAlchemyCalendarEventRepository,
    SqlAlchemyCostRepository,
    SqlAlchemyWorkingCalendarRepository,
)
from infra.db.repositories_project import (
    SqlAlchemyProjectRepository,
    SqlAlchemyProjectResourceRepository,
)
from infra.db.repositories_resource import SqlAlchemyResourceRepository
from infra.db.repositories_task import (
    SqlAlchemyAssignmentRepository,
    SqlAlchemyDependencyRepository,
    SqlAlchemyTaskRepository,
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
    "SqlAlchemyProjectRepository",
    "SqlAlchemyProjectResourceRepository",
    "SqlAlchemyTaskRepository",
    "SqlAlchemyResourceRepository",
    "SqlAlchemyAssignmentRepository",
    "SqlAlchemyDependencyRepository",
    "SqlAlchemyCostRepository",
    "SqlAlchemyCalendarEventRepository",
    "SqlAlchemyWorkingCalendarRepository",
    "SqlAlchemyBaselineRepository",
]
