from __future__ import annotations


PROJECT_SCOPE_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "viewer": {
        "project.read",
        "task.read",
        "cost.read",
        "register.read",
        "report.view",
        "collaboration.read",
    },
    "editor": {
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
        "approval.request",
    },
}


def resolve_project_scope_permissions(scope_role: str) -> set[str]:
    key = (scope_role or "").strip().lower() or "viewer"
    return set(PROJECT_SCOPE_ROLE_PERMISSIONS.get(key, PROJECT_SCOPE_ROLE_PERMISSIONS["viewer"]))


__all__ = ["PROJECT_SCOPE_ROLE_PERMISSIONS", "resolve_project_scope_permissions"]
