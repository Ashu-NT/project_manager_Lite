from __future__ import annotations

DEFAULT_PERMISSIONS: dict[str, str] = {
    "project.read": "View projects",
    "project.manage": "Create and edit projects",
    "task.read": "View tasks",
    "task.manage": "Create and edit tasks",
    "time.read": "View shared labor bookings and time entries",
    "time.manage": "Create and edit shared labor bookings and time entries",
    "resource.read": "View resources",
    "resource.manage": "Create and edit resources",
    "employee.read": "View employee directory records",
    "employee.manage": "Create and edit employee directory records",
    "inventory.read": "View inventory and procurement workspaces",
    "inventory.manage": "Create and edit inventory and procurement records",
    "maintenance.read": "View maintenance master data and operational records",
    "maintenance.manage": "Create and edit maintenance master data and operational records",
    "site.read": "View shared site directory records",
    "department.read": "View shared department directory records",
    "party.read": "View shared supplier, vendor, and contractor directory records",
    "cost.read": "View costs",
    "cost.manage": "Create and edit costs",
    "finance.read": "View finance snapshots and ledgers",
    "finance.read_sensitive": "View sensitive finance rates and labor details",
    "finance.manage": "Manage finance controls and adjustments",
    "finance.export": "Export finance analytics and ledgers",
    "payroll.read": "View payroll periods and summaries",
    "payroll.manage": "Manage payroll configuration and prepared runs",
    "payroll.approve": "Approve or release payroll runs",
    "payroll.export": "Export payroll reports and payment files",
    "baseline.manage": "Create baselines",
    "baseline.approve": "Approve or reject baselines",
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
    "import.manage": "Run governed module data imports",
    "approval.request": "Submit governed change requests",
    "approval.decide": "Approve or reject governed change requests",
    "settings.manage": "Manage app settings",
    "auth.read": "View user and role directory data",
    "auth.manage": "Manage users and roles",
    "auth.role.assign": "Assign reviewed roles through explicit delegation policy",
    "security.manage": "Manage login security, lockouts, and session controls",
    "organization.access": "Access tenant organization context",
    "org.create": "Create organizations within a tenant",
    "org.manage": "Manage organization settings and structure",
    "tenant.create": "Create new tenants",
    "tenant.manage": "Manage and update existing tenants",
    "tenant.read": "View tenant list and details",
    "platform.admin": "Full platform administration access",
}

_VIEWER = {
    "organization.access",
    "project.read",
    "task.read",
    "time.read",
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
    "time.manage",
    "baseline.manage",
    "register.manage",
    "report.export",
    "portfolio.read",
    "approval.request",
    "import.manage",
}

_PROJECT_MANAGER = _PLANNER | {
    "baseline.approve",
    "cost.manage",
    "finance.read",
    "finance.export",
    "timesheet.approve",
}

_RESOURCE_MANAGER = {
    "project.read",
    "task.read",
    "time.read",
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
    "time.read",
    "resource.read",
    "cost.read",
    "cost.manage",
    "party.read",
    "register.read",
    "report.view",
    "report.export",
    "finance.read",
    "finance.read_sensitive",
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
    "report.export",
    "import.manage",
    "approval.request",
}

_MAINTENANCE_MANAGER = {
    "maintenance.read",
    "maintenance.manage",
    "time.read",
    "time.manage",
    "site.read",
    "employee.read",
    "party.read",
    "report.view",
    "report.export",
    "approval.request",
    "import.manage",
}

_PAYROLL_MANAGER = {
    "project.read",
    "task.read",
    "time.read",
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
    "time.read",
    "resource.read",
    "cost.read",
    "register.read",
    "report.view",
    "report.export",
    "portfolio.read",
    "portfolio.manage",
    "finance.read",
    "collaboration.read",
    "approval.request",
}

_APPROVER = {
    "baseline.approve",
    "project.read",
    "resource.read",
    "task.read",
    "time.read",
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
    "time.read",
    "resource.read",
    "cost.read",
    "finance.read",
    "finance.read_sensitive",
    "payroll.read",
    "register.read",
    "report.view",
    "portfolio.read",
    "collaboration.read",
    "audit.read",
}

_ACCESS_ADMIN = {
    "project.read",
    "site.read",
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
    "time.read",
    "register.read",
    "report.view",
    "auth.read",
    "audit.read",
    "support.manage",
}

_TENANT_ADMIN = {
    "org.create",
    "org.manage",
    "organization.access",
    "settings.manage",
    "auth.read",
    "auth.manage",
    "auth.role.assign",
}

_ORG_ADMIN = {
    "org.manage",
    "employee.read",
    "employee.manage",
    "organization.access",
    "settings.manage",
    "auth.read",
    "auth.manage",
    "auth.role.assign",
}

_ORG_VIEWER = set(_VIEWER)
_ORG_MEMBER = set(_TEAM_MEMBER)

_PROJECT_VIEWER = {
    "project.read",
    "task.read",
    "cost.read",
    "register.read",
    "report.view",
    "collaboration.read",
}

_PROJECT_CONTRIBUTOR = _PROJECT_VIEWER | {
    "task.manage",
    "collaboration.manage",
    "timesheet.submit",
}

_PROJECT_LEAD = _PROJECT_CONTRIBUTOR | {
    "cost.manage",
    "baseline.manage",
    "register.manage",
    "report.export",
    "approval.request",
    "finance.read",
}

_PROJECT_OWNER = _PROJECT_LEAD | {
    "project.manage",
    "timesheet.approve",
    "timesheet.lock",
}

_SITE_VIEWER = {
    "site.read",
}

_SITE_OPERATOR = _SITE_VIEWER | {
    "inventory.read",
    "report.view",
}

_SITE_MANAGER = _SITE_OPERATOR | {
    "inventory.manage",
    "import.manage",
    "report.export",
}

_STOREROOM_VIEWER = {
    "inventory.read",
}

_STOREROOM_OPERATOR = _STOREROOM_VIEWER | {
    "inventory.manage",
}

_STOREROOM_MANAGER = _STOREROOM_OPERATOR | {
    "report.view",
}

_MAINTENANCE_VIEWER = {
    "maintenance.read",
}

_MAINTENANCE_OPERATOR = _MAINTENANCE_VIEWER | {
    "maintenance.manage",
}

_MAINTENANCE_SCOPE_MANAGER = _MAINTENANCE_OPERATOR | {
    "report.view",
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
    "maintenance_manager": set(_MAINTENANCE_MANAGER),
    "maintenance_admin": set(_MAINTENANCE_MANAGER),
    "payroll_manager": set(_PAYROLL_MANAGER),
    "portfolio_manager": set(_PORTFOLIO_MANAGER),
    "approver": set(_APPROVER),
    "auditor": set(_AUDITOR),
    "access_admin": set(_ACCESS_ADMIN),
    "security_admin": set(_SECURITY_ADMIN),
    "support_admin": set(_SUPPORT_ADMIN),
    "tenant_admin": set(_TENANT_ADMIN),
    "org_admin": set(_ORG_ADMIN),
    "org_viewer": set(_ORG_VIEWER),
    "org_member": set(_ORG_MEMBER),
    "project_viewer": set(_PROJECT_VIEWER),
    "project_contributor": set(_PROJECT_CONTRIBUTOR),
    "project_lead": set(_PROJECT_LEAD),
    "project_owner": set(_PROJECT_OWNER),
    "site_viewer": set(_SITE_VIEWER),
    "site_operator": set(_SITE_OPERATOR),
    "site_manager": set(_SITE_MANAGER),
    "storeroom_viewer": set(_STOREROOM_VIEWER),
    "storeroom_operator": set(_STOREROOM_OPERATOR),
    "storeroom_manager": set(_STOREROOM_MANAGER),
    "maintenance_viewer": set(_MAINTENANCE_VIEWER),
    "maintenance_operator": set(_MAINTENANCE_OPERATOR),
    "maintenance_scope_manager": set(_MAINTENANCE_SCOPE_MANAGER),
    "admin": set(DEFAULT_PERMISSIONS.keys()),
}

SYSTEM_ROLE_POLICY_NAME = "system-role-permissions"
SYSTEM_ROLE_POLICY_VERSION = 7

__all__ = [
    "DEFAULT_PERMISSIONS",
    "DEFAULT_ROLE_PERMISSIONS",
    "SYSTEM_ROLE_POLICY_NAME",
    "SYSTEM_ROLE_POLICY_VERSION",
]
