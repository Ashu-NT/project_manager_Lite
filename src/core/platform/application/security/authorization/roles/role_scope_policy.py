from __future__ import annotations

from src.core.platform.domain.security.authorization.roles.role_binding import (
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_TENANT,
)

# Stable names and scope metadata for code-owned system roles.
PLATFORM_ROLE_NAMES = frozenset({"admin", "support_admin"})
_ORGANIZATION_SCOPE_ROLE_NAMES = frozenset({"org_admin", "org_viewer", "org_member"})
_PROJECT_SCOPE_ROLE_NAMES = frozenset(
    {"project_viewer", "project_contributor", "project_lead", "project_owner"}
)
_SITE_SCOPE_ROLE_NAMES = frozenset({"site_viewer", "site_operator", "site_manager"})
_STOREROOM_SCOPE_ROLE_NAMES = frozenset(
    {"storeroom_viewer", "storeroom_operator", "storeroom_manager"}
)
_MAINTENANCE_SCOPE_ROLE_NAMES = frozenset(
    {"maintenance_viewer", "maintenance_operator", "maintenance_scope_manager"}
)
EXPLICIT_SCOPE_ROLE_NAMES = (
    _ORGANIZATION_SCOPE_ROLE_NAMES
    | _PROJECT_SCOPE_ROLE_NAMES
    | _SITE_SCOPE_ROLE_NAMES
    | _STOREROOM_SCOPE_ROLE_NAMES
    | _MAINTENANCE_SCOPE_ROLE_NAMES
)


def normalize_role_name(role_name: str) -> str:
    return str(role_name or "").strip().lower()


def is_platform_role(role_name: str) -> bool:
    return normalize_role_name(role_name) in PLATFORM_ROLE_NAMES


def is_customer_assignable_role(role_name: str) -> bool:
    normalized = normalize_role_name(role_name)
    return bool(normalized) and normalized not in (
        PLATFORM_ROLE_NAMES | EXPLICIT_SCOPE_ROLE_NAMES
    )


def system_role_scope_type(role_name: str) -> str:
    normalized = normalize_role_name(role_name)
    if normalized in PLATFORM_ROLE_NAMES:
        return ROLE_SCOPE_PLATFORM
    if normalized in _ORGANIZATION_SCOPE_ROLE_NAMES:
        return "organization"
    if normalized in _PROJECT_SCOPE_ROLE_NAMES:
        return "project"
    if normalized in _SITE_SCOPE_ROLE_NAMES:
        return "site"
    if normalized in _STOREROOM_SCOPE_ROLE_NAMES:
        return "storeroom"
    if normalized in _MAINTENANCE_SCOPE_ROLE_NAMES:
        return "maintenance"
    return ROLE_SCOPE_TENANT


__all__ = [
    "EXPLICIT_SCOPE_ROLE_NAMES",
    "PLATFORM_ROLE_NAMES",
    "is_customer_assignable_role",
    "is_platform_role",
    "normalize_role_name",
    "system_role_scope_type",
]
