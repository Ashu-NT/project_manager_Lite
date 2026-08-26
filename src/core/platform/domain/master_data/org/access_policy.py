from __future__ import annotations

from src.core.platform.domain.security.authorization.roles.role_permission_catalog import (
    DEFAULT_ROLE_PERMISSIONS,
)

ORGANIZATION_SCOPE_ROLE_ALIASES: dict[str, str] = {}


ORGANIZATION_SCOPE_ROLE_CHOICES: tuple[str, ...] = (
    "viewer",
    "member",
    "admin",
)

ORGANIZATION_SCOPE_ROLE_CANONICAL_NAMES: dict[str, str] = {
    "viewer": "org_viewer",
    "member": "org_member",
    "admin": "org_admin",
}


def normalize_organization_scope_role(scope_role: str) -> str:
    key = (scope_role or "").strip().lower() or "viewer"
    return ORGANIZATION_SCOPE_ROLE_ALIASES.get(key, key)


def resolve_organization_scope_permissions(scope_role: str) -> set[str]:
    key = normalize_organization_scope_role(scope_role)
    canonical_role_name = ORGANIZATION_SCOPE_ROLE_CANONICAL_NAMES.get(key, "org_viewer")
    return set(
        DEFAULT_ROLE_PERMISSIONS.get(canonical_role_name, DEFAULT_ROLE_PERMISSIONS["org_viewer"])
    )


__all__ = [
    "ORGANIZATION_SCOPE_ROLE_ALIASES",
    "ORGANIZATION_SCOPE_ROLE_CANONICAL_NAMES",
    "ORGANIZATION_SCOPE_ROLE_CHOICES",
    "normalize_organization_scope_role",
    "resolve_organization_scope_permissions",
]
