from __future__ import annotations

PROJECT_SCOPE_ROLE_ALIASES: dict[str, str] = {
    "editor": "contributor",
}


PROJECT_SCOPE_ROLE_CHOICES: tuple[str, ...] = (
    "viewer",
    "contributor",
    "lead",
    "owner",
)


PROJECT_SCOPE_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "viewer": {
        "project.read",
        "task.read",
        "cost.read",
        "register.read",
        "report.view",
        "collaboration.read",
    },
    "contributor": {
        "project.read",
        "task.read",
        "task.manage",
        "cost.read",
        "register.read",
        "collaboration.read",
        "collaboration.manage",
        "timesheet.submit",
    },
    "lead": {
        "project.read",
        "task.read",
        "task.manage",
        "cost.read",
        "cost.manage",
        "baseline.manage",
        "register.read",
        "register.manage",
        "report.view",
        "report.export",
        "collaboration.read",
        "collaboration.manage",
        "timesheet.submit",
        "approval.request",
    },
    "owner": {
        "project.read",
        "project.manage",
        "task.read",
        "task.manage",
        "cost.read",
        "cost.manage",
        "baseline.manage",
        "register.read",
        "register.manage",
        "report.view",
        "report.export",
        "collaboration.read",
        "collaboration.manage",
        "timesheet.submit",
        "timesheet.approve",
        "timesheet.lock",
        "approval.request",
    },
}


def normalize_project_scope_role(scope_role: str) -> str:
    key = (scope_role or "").strip().lower() or "viewer"
    return PROJECT_SCOPE_ROLE_ALIASES.get(key, key)


def resolve_project_scope_permissions(scope_role: str) -> set[str]:
    key = normalize_project_scope_role(scope_role)
    return set(PROJECT_SCOPE_ROLE_PERMISSIONS.get(key, PROJECT_SCOPE_ROLE_PERMISSIONS["viewer"]))


__all__ = [
    "PROJECT_SCOPE_ROLE_ALIASES",
    "PROJECT_SCOPE_ROLE_CHOICES",
    "PROJECT_SCOPE_ROLE_PERMISSIONS",
    "normalize_project_scope_role",
    "resolve_project_scope_permissions",
]
