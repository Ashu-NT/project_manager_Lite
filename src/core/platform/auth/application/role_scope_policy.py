from __future__ import annotations

from src.core.platform.auth.domain.role_binding import (
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_TENANT,
)

# Transitional classification for legacy global roles. Canonical role bindings
# will move this metadata into the role model during the schema migration.
PLATFORM_ROLE_NAMES = frozenset({"admin", "support_admin"})
EXPLICIT_SCOPE_ROLE_NAMES = frozenset({"org_admin"})


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
    if normalized == "org_admin":
        return "organization"
    return ROLE_SCOPE_TENANT


__all__ = [
    "EXPLICIT_SCOPE_ROLE_NAMES",
    "PLATFORM_ROLE_NAMES",
    "is_customer_assignable_role",
    "is_platform_role",
    "normalize_role_name",
    "system_role_scope_type",
]
