from __future__ import annotations

from src.core.platform.auth.policy import DEFAULT_ROLE_PERMISSIONS


ORGANIZATION_SCOPE_ROLE_CHOICES: tuple[str, ...] = (
    "viewer",
    "member",
    "manager",
)


def normalize_organization_scope_role(scope_role: str) -> str:
    normalized = str(scope_role or "").strip().lower()
    if normalized in {"admin", "owner", "manager"}:
        return "manager"
    if normalized in {"member", "editor"}:
        return "member"
    return "viewer"


def resolve_organization_scope_permissions(scope_role: str) -> set[str]:
    normalized = normalize_organization_scope_role(scope_role)
    if normalized == "manager":
        return set(DEFAULT_ROLE_PERMISSIONS["project_manager"]) | {"organization.access"}
    if normalized == "member":
        return set(DEFAULT_ROLE_PERMISSIONS["team_member"]) | {"organization.access"}
    return set(DEFAULT_ROLE_PERMISSIONS["viewer"]) | {"organization.access"}


__all__ = [
    "ORGANIZATION_SCOPE_ROLE_CHOICES",
    "normalize_organization_scope_role",
    "resolve_organization_scope_permissions",
]
