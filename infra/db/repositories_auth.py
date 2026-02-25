"""Compatibility wrapper for auth repositories."""

from infra.db.auth.repository import (
    SqlAlchemyPermissionRepository,
    SqlAlchemyRolePermissionRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyUserRepository,
    SqlAlchemyUserRoleRepository,
)

__all__ = [
    "SqlAlchemyUserRepository",
    "SqlAlchemyRoleRepository",
    "SqlAlchemyPermissionRepository",
    "SqlAlchemyUserRoleRepository",
    "SqlAlchemyRolePermissionRepository",
]

