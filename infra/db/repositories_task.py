"""Compatibility wrapper for task repositories."""

from infra.db.task.repository import (
    SqlAlchemyAssignmentRepository,
    SqlAlchemyDependencyRepository,
    SqlAlchemyTaskRepository,
)
from infra.db.task.time_entry_repository import SqlAlchemyTimeEntryRepository
from infra.db.task.timesheet_period_repository import SqlAlchemyTimesheetPeriodRepository


__all__ = [
    "SqlAlchemyTaskRepository",
    "SqlAlchemyAssignmentRepository",
    "SqlAlchemyDependencyRepository",
    "SqlAlchemyTimeEntryRepository",
    "SqlAlchemyTimesheetPeriodRepository",
]
