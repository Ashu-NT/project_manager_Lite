"""Compatibility wrapper for task repositories."""

from infra.modules.project_management.db.task.repository import (
    SqlAlchemyAssignmentRepository,
    SqlAlchemyDependencyRepository,
    SqlAlchemyTaskRepository,
)
from infra.modules.project_management.db.task.time_entry_repository import SqlAlchemyTimeEntryRepository
from infra.modules.project_management.db.task.timesheet_period_repository import SqlAlchemyTimesheetPeriodRepository


__all__ = [
    "SqlAlchemyTaskRepository",
    "SqlAlchemyAssignmentRepository",
    "SqlAlchemyDependencyRepository",
    "SqlAlchemyTimeEntryRepository",
    "SqlAlchemyTimesheetPeriodRepository",
]
