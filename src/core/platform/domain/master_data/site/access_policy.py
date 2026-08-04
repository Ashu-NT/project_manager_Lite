from __future__ import annotations


SITE_SCOPE_ROLE_ALIASES: dict[str, str] = {
    "editor": "operator",
}


SITE_SCOPE_ROLE_CHOICES: tuple[str, ...] = (
    "viewer",
    "operator",
    "manager",
)


SITE_SCOPE_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "viewer": {
        "site.read",
    },
    "operator": {
        "site.read",
        "inventory.read",
        "report.view",
    },
    "manager": {
        "site.read",
        "inventory.read",
        "inventory.manage",
        "import.manage",
        "report.view",
        "report.export",
    },
}


def normalize_site_scope_role(scope_role: str) -> str:
    key = (scope_role or "").strip().lower() or "viewer"
    return SITE_SCOPE_ROLE_ALIASES.get(key, key)


def resolve_site_scope_permissions(scope_role: str) -> set[str]:
    key = normalize_site_scope_role(scope_role)
    return set(SITE_SCOPE_ROLE_PERMISSIONS.get(key, SITE_SCOPE_ROLE_PERMISSIONS["viewer"]))


__all__ = [
    "SITE_SCOPE_ROLE_ALIASES",
    "SITE_SCOPE_ROLE_CHOICES",
    "SITE_SCOPE_ROLE_PERMISSIONS",
    "normalize_site_scope_role",
    "resolve_site_scope_permissions",
]
