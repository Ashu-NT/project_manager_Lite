"""Compatibility wrapper for task repositories."""

from infra.db.task.repository import (
    SqlAlchemyAssignmentRepository,
    SqlAlchemyDependencyRepository,
    SqlAlchemyTaskRepository,
)


__all__ = [
    "SqlAlchemyTaskRepository",
    "SqlAlchemyAssignmentRepository",
    "SqlAlchemyDependencyRepository",
]
