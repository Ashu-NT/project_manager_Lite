"""Compatibility facade for ORM mappers.

New code should import focused modules under ``infra.db.mappers_*``.
This module re-exports all mapper functions to preserve legacy imports.
"""

from infra.db.mappers_baseline import (
    baseline_from_orm,
    baseline_task_from_orm,
    baseline_task_to_orm,
    baseline_to_orm,
)
from infra.db.mappers_cost_calendar import (
    calendar_from_orm,
    calendar_to_orm,
    cost_from_orm,
    cost_to_orm,
    event_from_orm,
    event_to_orm,
    holiday_from_orm,
    holiday_to_orm,
)
from infra.db.mappers_project import (
    project_from_orm,
    project_resource_from_orm,
    project_resource_to_orm,
    project_to_orm,
)
from infra.db.mappers_resource import resource_from_orm, resource_to_orm
from infra.db.mappers_task import (
    assignment_from_orm,
    assignment_to_orm,
    dependency_from_orm,
    dependency_to_orm,
    task_from_orm,
    task_to_orm,
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
