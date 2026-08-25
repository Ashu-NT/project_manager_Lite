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
    "site.read": "View shared site directory records",
    "department.read": "View shared department directory records",
    "party.read": "View shared supplier, vendor, and contractor directory records",
    "cost.read": "View costs",
    "project_cost.create": "Create canonical project cost-entry drafts",
    "project_cost.update_draft": "Update or delete canonical project cost-entry drafts",
    "project_cost.submit": "Submit canonical project cost entries for approval",
    "project_cost.approve": "Approve or reject canonical project cost entries",
    "project_cost.post": "Post approved project cost entries to the actual-cost ledger",
    "project_cost.reverse": "Reverse posted project cost entries",
    "finance.read": "View finance snapshots and ledgers",
    "finance.read_sensitive": "View sensitive finance rates and labor details",
    "finance.read_profitability": "View project commercial margin and profitability projections",
    "finance.manage": "Manage finance controls and adjustments",
    "finance.export": "Export finance analytics and ledgers",
    "payroll.read": "View payroll periods and summaries",
    "payroll.manage": "Manage payroll configuration and prepared runs",
    "payroll.approve": "Approve or release payroll runs",
    "payroll.export": "Export payroll reports and payment files",
    "baseline.manage": "Create baselines",
    "baseline.approve": "Approve or reject baselines",
    "budget.manage": "Create, edit, and submit project budgets",
    "budget.approve": "Approve, reject, or close project budgets",
    "plannedcost.manage": "Calculate versioned planned-cost snapshots",
    "forecast.manage": "Create, edit, and submit project forecasts",
    "forecast.approve": "Approve or reject project forecasts",
    "financial_change.manage": "Create and submit governed financial change orders",
    "register.read": "View risk, issue, and change register data",
    "register.manage": "Create and edit register entries",
    "report.view": "View reports",
    "report.export": "Export reports",
    "portfolio.read": "View portfolio intake and scenarios",
    "portfolio.manage": "Manage portfolio intake and scenarios",
    "collaboration.read": "View team collaboration activity",
    "collaboration.manage": "Post team collaboration updates",
    "timesheet.read_own": "View the signed-in resource's timesheets",
    "timesheet.edit_own": "Prepare the signed-in resource's timesheets",
    "timesheet.submit": "Submit timesheet periods",
    "timesheet.read_team": "View authorized project-team timesheets",
    "timesheet.edit_team": "Prepare authorized project-team timesheets",
    "timesheet.read_all": "View organization-wide resource timesheets",
    "timesheet.edit_all": "Prepare organization-wide resource timesheets",
    "timesheet.submit_on_behalf": "Submit another resource's timesheet period",
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
    "timesheet.read_own",
    "timesheet.edit_own",
    "timesheet.submit",
}

_PLANNER = _TEAM_MEMBER | {
    "project.manage",
    "task.manage",
    "time.manage",
    "baseline.manage",
    "budget.manage",
    "plannedcost.manage",
    "forecast.manage",
    "financial_change.manage",
    "finance.read",
    "register.manage",
    "report.export",
    "portfolio.read",
    "approval.request",
    "import.manage",
    "project_cost.create",
    "project_cost.update_draft",
    "project_cost.submit",
}

_PROJECT_MANAGER = _PLANNER | {
    "baseline.approve",
    "budget.approve",
    "forecast.approve",
    "finance.read",
    "finance.export",
    "timesheet.approve",
    "timesheet.read_team",
    "timesheet.edit_team",
    "timesheet.submit_on_behalf",
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
    "timesheet.read_team",
    "timesheet.edit_team",
    "timesheet.read_all",
    "timesheet.edit_all",
    "timesheet.submit_on_behalf",
    "timesheet.approve",
    "timesheet.lock",
}

_FINANCE_CONTROLLER = {
    "project.read",
    "task.read",
    "time.read",
    "resource.read",
    "cost.read",
    "party.read",
    "register.read",
    "report.view",
    "report.export",
    "finance.read",
    "finance.read_sensitive",
    "finance.read_profitability",
    "finance.manage",
    "finance.export",
    "payroll.read",
    "approval.request",
    "budget.manage",
    "plannedcost.manage",
    "forecast.manage",
    "budget.approve",
    "forecast.approve",
    "financial_change.manage",
    "project_cost.create",
    "project_cost.update_draft",
    "project_cost.submit",
    "project_cost.approve",
    "project_cost.post",
    "project_cost.reverse",
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
    "timesheet.read_all",
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
    "budget.approve",
    "forecast.approve",
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
    "project_cost.approve",
}

_AUDITOR = {
    "project.read",
    "task.read",
    "time.read",
    "resource.read",
    "cost.read",
    "finance.read",
    "finance.read_sensitive",
    "finance.read_profitability",
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
    "timesheet.read_own",
    "timesheet.edit_own",
    "timesheet.submit",
}

_PROJECT_LEAD = _PROJECT_CONTRIBUTOR | {
    "baseline.manage",
    "budget.manage",
    "plannedcost.manage",
    "forecast.manage",
    "register.manage",
    "report.export",
    "approval.request",
    "finance.read",
    "project_cost.create",
    "project_cost.update_draft",
    "project_cost.submit",
    "timesheet.read_team",
    "timesheet.edit_team",
    "timesheet.submit_on_behalf",
}

_PROJECT_OWNER = _PROJECT_LEAD | {
    "project.manage",
    "budget.approve",
    "forecast.approve",
    "timesheet.approve",
    "timesheet.lock",
    "project_cost.approve",
    "project_cost.post",
    "project_cost.reverse",
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
    "admin": set(DEFAULT_PERMISSIONS.keys()),
}

SYSTEM_ROLE_POLICY_NAME = "system-role-permissions"
SYSTEM_ROLE_POLICY_VERSION = 11

__all__ = [
    "DEFAULT_PERMISSIONS",
    "DEFAULT_ROLE_PERMISSIONS",
    "SYSTEM_ROLE_POLICY_NAME",
    "SYSTEM_ROLE_POLICY_VERSION",
]
