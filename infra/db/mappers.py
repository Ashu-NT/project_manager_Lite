"""Compatibility facade for ORM mappers.

New code should import focused aggregate modules under ``infra.db.<aggregate>.mapper``.
This module re-exports all mapper functions to preserve legacy imports.
"""

from infra.db.baseline.mapper import (
    baseline_from_orm,
    baseline_task_from_orm,
    baseline_task_to_orm,
    baseline_to_orm,
)
from infra.db.auth.mapper import (
    permission_from_orm,
    permission_to_orm,
    role_from_orm,
    role_permission_from_orm,
    role_permission_to_orm,
    role_to_orm,
    user_from_orm,
    user_role_from_orm,
    user_role_to_orm,
    user_to_orm,
)
from infra.db.cost_calendar.mapper import (
    calendar_from_orm,
    calendar_to_orm,
    cost_from_orm,
    cost_to_orm,
    event_from_orm,
    event_to_orm,
    holiday_from_orm,
    holiday_to_orm,
)
from infra.db.project.mapper import (
    project_from_orm,
    project_resource_from_orm,
    project_resource_to_orm,
    project_to_orm,
)
from infra.db.resource.mapper import resource_from_orm, resource_to_orm
from infra.db.task.mapper import (
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
    "user_to_orm",
    "user_from_orm",
    "role_to_orm",
    "role_from_orm",
    "permission_to_orm",
    "permission_from_orm",
    "user_role_to_orm",
    "user_role_from_orm",
    "role_permission_to_orm",
    "role_permission_from_orm",
]
