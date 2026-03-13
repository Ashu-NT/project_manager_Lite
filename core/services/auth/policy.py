from __future__ import annotations

import os

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
    "register.read": "View risk, issue, and change register data",
    "register.manage": "Create and edit register entries",
    "report.view": "View reports",
    "report.export": "Export reports",
    "portfolio.read": "View portfolio intake and scenarios",
    "portfolio.manage": "Manage portfolio intake and scenarios",
    "collaboration.read": "View team collaboration activity",
    "collaboration.manage": "Post team collaboration updates",
    "timesheet.submit": "Submit timesheet periods",
    "timesheet.approve": "Approve or reject timesheet periods",
    "timesheet.lock": "Lock or unlock timesheet periods",
    "audit.read": "View audit history",
    "support.manage": "Access product support operations",
    "access.manage": "Manage project memberships and access scope",
    "import.manage": "Run project data imports",
    "approval.request": "Submit governed change requests",
    "approval.decide": "Approve or reject governed change requests",
    "settings.manage": "Manage app settings",
    "auth.manage": "Manage users and roles",
}


DEFAULT_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "viewer": {
        "project.read",
        "task.read",
        "resource.read",
        "cost.read",
        "register.read",
        "report.view",
        "collaboration.read",
    },
    "planner": {
        "project.read",
        "project.manage",
        "task.read",
        "task.manage",
        "resource.read",
        "cost.read",
        "baseline.manage",
        "register.read",
        "register.manage",
        "report.view",
        "report.export",
        "portfolio.read",
        "collaboration.read",
        "collaboration.manage",
        "timesheet.submit",
        "approval.request",
        "import.manage",
    },
    "finance": {
        "project.read",
        "task.read",
        "resource.read",
        "cost.read",
        "cost.manage",
        "register.read",
        "report.view",
        "report.export",
        "timesheet.approve",
        "approval.request",
    },
    "admin": set(DEFAULT_PERMISSIONS.keys()),
}

def login_lockout_threshold() -> int:
    raw = os.getenv("PM_AUTH_LOCKOUT_ATTEMPTS", "5").strip() or "5"
    try:
        return max(1, int(raw))
    except ValueError:
        return 5


def login_lockout_minutes() -> int:
    raw = os.getenv("PM_AUTH_LOCKOUT_MINUTES", "15").strip() or "15"
    try:
        return max(1, int(raw))
    except ValueError:
        return 15


def session_timeout_minutes() -> int:
    raw = os.getenv("PM_AUTH_SESSION_MINUTES", "480").strip() or "480"
    try:
        return max(5, int(raw))
    except ValueError:
        return 480


__all__ = [
    "DEFAULT_PERMISSIONS",
    "DEFAULT_ROLE_PERMISSIONS",
    "login_lockout_minutes",
    "login_lockout_threshold",
    "session_timeout_minutes",
]
