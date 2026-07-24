from __future__ import annotations


class Permissions:
    """Central registry of permission code strings."""

    # Audit
    AUDIT_READ = "audit.read"
    AUDIT_MANAGE = "audit.manage"

    # Activity
    ACTIVITY_READ = "activity.read"

    # Auth / Users / Roles
    AUTH_MANAGE = "auth.manage"
    AUTH_READ = "auth.read"
    SECURITY_MANAGE = "security.manage"

    # Tasks
    TASK_MANAGE = "task.manage"
    TASK_READ = "task.read"

    # Projects
    PROJECT_MANAGE = "project.manage"
    PROJECT_READ = "project.read"

    # Settings
    SETTINGS_MANAGE = "settings.manage"
    SITE_READ = "site.read"

    # Access
    ACCESS_MANAGE = "access.manage"

    # Employee
    EMPLOYEE_MANAGE = "employee.manage"
    EMPLOYEE_READ = "employee.read"

    # Timesheet
    TIMESHEET_SUBMIT = "timesheet.submit"
    TIMESHEET_APPROVE = "timesheet.approve"
    TIMESHEET_LOCK = "timesheet.lock"

    # Resources
    RESOURCE_MANAGE = "resource.manage"
    RESOURCE_READ = "resource.read"

    # Inventory
    INVENTORY_MANAGE = "inventory.manage"
    INVENTORY_READ = "inventory.read"


__all__ = ["Permissions"]
