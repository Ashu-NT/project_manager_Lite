from __future__ import annotations

DEFAULT_PERMISSIONS: dict[str, str] = {
    "project.read": "View projects",
    "project.manage": "Create and edit projects",
    "task.read": "View tasks",
    "task.manage": "Create and edit tasks",
    "resource.read": "View resources",
    "resource.manage": "Create and edit resources",
    "cost.read": "View costs",
    "cost.manage": "Create and edit costs",
    "baseline.manage": "Create baselines",
    "report.view": "View reports",
    "report.export": "Export reports",
    "settings.manage": "Manage app settings",
    "auth.manage": "Manage users and roles",
}


DEFAULT_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "viewer": {
        "project.read",
        "task.read",
        "resource.read",
        "cost.read",
        "report.view",
    },
    "planner": {
        "project.read",
        "project.manage",
        "task.read",
        "task.manage",
        "resource.read",
        "cost.read",
        "baseline.manage",
        "report.view",
        "report.export",
    },
    "finance": {
        "project.read",
        "task.read",
        "resource.read",
        "cost.read",
        "cost.manage",
        "report.view",
        "report.export",
    },
    "admin": set(DEFAULT_PERMISSIONS.keys()),
}


__all__ = ["DEFAULT_PERMISSIONS", "DEFAULT_ROLE_PERMISSIONS"]

