"""Compatibility wrapper for task repositories."""

from infra.db.task.repository import (
    SqlAlchemyAssignmentRepository,
    SqlAlchemyDependencyRepository,
    SqlAlchemyTaskRepository,
)
from infra.db.task.time_entry_repository import SqlAlchemyTimeEntryRepository


__all__ = [
    "SqlAlchemyTaskRepository",
    "SqlAlchemyAssignmentRepository",
    "SqlAlchemyDependencyRepository",
    "SqlAlchemyTimeEntryRepository",
]
