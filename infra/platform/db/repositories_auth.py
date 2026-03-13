"""Compatibility wrapper for auth repositories."""

from infra.platform.db.auth.repository import (
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

