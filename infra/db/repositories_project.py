"""Compatibility wrapper for project repositories."""

from infra.db.project.repository import (
    SqlAlchemyProjectRepository,
    SqlAlchemyProjectResourceRepository,
)


__all__ = [
    "SqlAlchemyProjectRepository",
    "SqlAlchemyProjectResourceRepository",
]
