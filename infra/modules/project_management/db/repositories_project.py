"""Compatibility wrapper for project repositories."""

from infra.modules.project_management.db.project.repository import (
    SqlAlchemyProjectRepository,
    SqlAlchemyProjectResourceRepository,
)


__all__ = [
    "SqlAlchemyProjectRepository",
    "SqlAlchemyProjectResourceRepository",
]
