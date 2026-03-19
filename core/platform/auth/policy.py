from __future__ import annotations

import os

DEFAULT_PERMISSIONS: dict[str, str] = {
    "project.read": "View projects",
    "project.manage": "Create and edit projects",
    "task.read": "View tasks",
    "task.manage": "Create and edit tasks",
    "resource.read": "View resources",
    "resource.manage": "Create and edit resources",
    "employee.read": "View employee directory records",
    "employee.manage": "Create and edit employee directory records",
    "inventory.read": "View inventory and procurement workspaces",
    "inventory.manage": "Create and edit inventory and procurement records",
    "site.read": "View shared site directory records",
    "department.read": "View shared department directory records",
    "party.read": "View shared supplier, vendor, and contractor directory records",
    "cost.read": "View costs",
    "cost.manage": "Create and edit costs",
    "finance.read": "View finance snapshots and ledgers",
    "finance.manage": "Manage finance controls and adjustments",
    "finance.export": "Export finance analytics and ledgers",
    "payroll.read": "View payroll periods and summaries",
    "payroll.manage": "Manage payroll configuration and prepared runs",
    "payroll.approve": "Approve or release payroll runs",
    "payroll.export": "Export payroll reports and payment files",
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
    "auth.read": "View user and role directory data",
    "auth.manage": "Manage users and roles",
    "security.manage": "Manage login security, lockouts, and session controls",
}

_VIEWER = {
    "project.read",
    "task.read",
    "resource.read",
    "cost.read",
    "register.read",
    "report.view",
    "collaboration.read",
}

_TEAM_MEMBER = _VIEWER | {
    "collaboration.manage",
    "timesheet.submit",
}

_PLANNER = _TEAM_MEMBER | {
    "project.manage",
    "task.manage",
    "baseline.manage",
    "register.manage",
    "report.export",
    "portfolio.read",
    "approval.request",
    "import.manage",
}

_PROJECT_MANAGER = _PLANNER | {
    "cost.manage",
    "finance.read",
    "finance.export",
    "timesheet.approve",
}

_RESOURCE_MANAGER = {
    "project.read",
    "task.read",
    "resource.read",
    "resource.manage",
    "employee.read",
    "employee.manage",
    "site.read",
    "department.read",
    "report.view",
    "report.export",
    "collaboration.read",
    "timesheet.approve",
    "timesheet.lock",
}

_FINANCE_CONTROLLER = {
    "project.read",
    "task.read",
    "resource.read",
    "cost.read",
    "cost.manage",
    "party.read",
    "register.read",
    "report.view",
    "report.export",
    "finance.read",
    "finance.manage",
    "finance.export",
    "payroll.read",
    "approval.request",
}

_INVENTORY_MANAGER = {
    "inventory.read",
    "inventory.manage",
    "site.read",
    "party.read",
    "report.view",
    "approval.request",
}

_PAYROLL_MANAGER = {
    "project.read",
    "task.read",
    "resource.read",
    "employee.read",
    "employee.manage",
    "site.read",
    "department.read",
    "report.view",
    "payroll.read",
    "payroll.manage",
    "payroll.approve",
    "payroll.export",
    "timesheet.approve",
    "timesheet.lock",
    "audit.read",
}

_PORTFOLIO_MANAGER = {
    "project.read",
    "task.read",
    "resource.read",
    "cost.read",
    "register.read",
    "report.view",
    "report.export",
    "portfolio.read",
    "portfolio.manage",
    "collaboration.read",
    "approval.request",
}

_APPROVER = {
    "project.read",
    "resource.read",
    "task.read",
    "cost.read",
    "register.read",
    "report.view",
    "portfolio.read",
    "finance.read",
    "payroll.read",
    "approval.decide",
}

_AUDITOR = {
    "project.read",
    "task.read",
    "resource.read",
    "cost.read",
    "finance.read",
    "payroll.read",
    "register.read",
    "report.view",
    "portfolio.read",
    "collaboration.read",
    "audit.read",
}

_ACCESS_ADMIN = {
    "project.read",
    "auth.read",
    "access.manage",
    "audit.read",
}

_SECURITY_ADMIN = {
    "auth.read",
    "audit.read",
    "settings.manage",
    "security.manage",
}

_SUPPORT_ADMIN = {
    "project.read",
    "task.read",
    "register.read",
    "report.view",
    "auth.read",
    "audit.read",
    "support.manage",
}

DEFAULT_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "viewer": set(_VIEWER),
    "team_member": set(_TEAM_MEMBER),
    "planner": set(_PLANNER),
    "project_manager": set(_PROJECT_MANAGER),
    "resource_manager": set(_RESOURCE_MANAGER),
    "finance": set(_FINANCE_CONTROLLER),
    "finance_controller": set(_FINANCE_CONTROLLER),
    "inventory_manager": set(_INVENTORY_MANAGER),
    "payroll_manager": set(_PAYROLL_MANAGER),
    "portfolio_manager": set(_PORTFOLIO_MANAGER),
    "approver": set(_APPROVER),
    "auditor": set(_AUDITOR),
    "access_admin": set(_ACCESS_ADMIN),
    "security_admin": set(_SECURITY_ADMIN),
    "support_admin": set(_SUPPORT_ADMIN),
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
