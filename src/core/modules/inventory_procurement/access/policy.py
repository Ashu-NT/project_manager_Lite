from __future__ import annotations


STOREROOM_SCOPE_ROLE_ALIASES: dict[str, str] = {
    "editor": "operator",
}


STOREROOM_SCOPE_ROLE_CHOICES: tuple[str, ...] = (
    "viewer",
    "operator",
    "manager",
)


STOREROOM_SCOPE_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "viewer": {
        "inventory.read",
    },
    "operator": {
        "inventory.read",
        "inventory.manage",
    },
    "manager": {
        "inventory.read",
        "inventory.manage",
        "report.view",
    },
}


def normalize_storeroom_scope_role(scope_role: str) -> str:
    key = (scope_role or "").strip().lower() or "viewer"
    return STOREROOM_SCOPE_ROLE_ALIASES.get(key, key)


def resolve_storeroom_scope_permissions(scope_role: str) -> set[str]:
    key = normalize_storeroom_scope_role(scope_role)
    return set(STOREROOM_SCOPE_ROLE_PERMISSIONS.get(key, STOREROOM_SCOPE_ROLE_PERMISSIONS["viewer"]))


__all__ = [
    "STOREROOM_SCOPE_ROLE_ALIASES",
    "STOREROOM_SCOPE_ROLE_CHOICES",
    "STOREROOM_SCOPE_ROLE_PERMISSIONS",
    "normalize_storeroom_scope_role",
    "resolve_storeroom_scope_permissions",
]
