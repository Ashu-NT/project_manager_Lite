from __future__ import annotations


MAINTENANCE_SCOPE_ROLE_ALIASES: dict[str, str] = {
    "editor": "operator",
}


MAINTENANCE_SCOPE_ROLE_CHOICES: tuple[str, ...] = (
    "viewer",
    "operator",
    "manager",
)


MAINTENANCE_SCOPE_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "viewer": {
        "maintenance.read",
    },
    "operator": {
        "maintenance.read",
        "maintenance.manage",
    },
    "manager": {
        "maintenance.read",
        "maintenance.manage",
        "report.view",
    },
}


def normalize_maintenance_scope_role(scope_role: str) -> str:
    key = (scope_role or "").strip().lower() or "viewer"
    return MAINTENANCE_SCOPE_ROLE_ALIASES.get(key, key)


def resolve_maintenance_scope_permissions(scope_role: str) -> set[str]:
    key = normalize_maintenance_scope_role(scope_role)
    return set(MAINTENANCE_SCOPE_ROLE_PERMISSIONS.get(key, MAINTENANCE_SCOPE_ROLE_PERMISSIONS["viewer"]))


__all__ = [
    "MAINTENANCE_SCOPE_ROLE_ALIASES",
    "MAINTENANCE_SCOPE_ROLE_CHOICES",
    "MAINTENANCE_SCOPE_ROLE_PERMISSIONS",
    "normalize_maintenance_scope_role",
    "resolve_maintenance_scope_permissions",
]