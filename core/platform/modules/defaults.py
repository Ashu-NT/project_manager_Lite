from __future__ import annotations

from core.platform.common.exceptions import ValidationError
from core.platform.modules.catalog_models import EnterpriseModule, PlatformCapability
from core.platform.modules.module_codes import normalize_module_code

MODULE_LIFECYCLE_INACTIVE = "inactive"
MODULE_LIFECYCLE_ACTIVE = "active"
MODULE_LIFECYCLE_TRIAL = "trial"
MODULE_LIFECYCLE_SUSPENDED = "suspended"
MODULE_LIFECYCLE_EXPIRED = "expired"
MODULE_LIFECYCLE_STATUSES: tuple[str, ...] = (
    MODULE_LIFECYCLE_INACTIVE,
    MODULE_LIFECYCLE_ACTIVE,
    MODULE_LIFECYCLE_TRIAL,
    MODULE_LIFECYCLE_SUSPENDED,
    MODULE_LIFECYCLE_EXPIRED,
)
MODULE_RUNTIME_ACCESS_STATUSES: frozenset[str] = frozenset(
    {MODULE_LIFECYCLE_ACTIVE, MODULE_LIFECYCLE_TRIAL}
)


DEFAULT_PLATFORM_CAPABILITIES: tuple[PlatformCapability, ...] = (
    PlatformCapability(
        code="users",
        label="Users",
        description="Identity directory, user lifecycle, and account administration.",
    ),
    PlatformCapability(
        code="access",
        label="Access",
        description="Roles, permissions, and project-scoped access control.",
    ),
    PlatformCapability(
        code="audit",
        label="Audit",
        description="Immutable platform audit trail and control visibility.",
    ),
    PlatformCapability(
        code="approvals",
        label="Approvals",
        description="Shared approval routing and decision workflows.",
    ),
    PlatformCapability(
        code="employees",
        label="Employees",
        description="Shared employee directory for staffing and enterprise workflows.",
    ),
    PlatformCapability(
        code="documents",
        label="Documents",
        description="Shared attachments and document handling across modules.",
    ),
    PlatformCapability(
        code="inbox",
        label="Inbox",
        description="Cross-module action feed for mentions, approvals, and alerts.",
    ),
    PlatformCapability(
        code="notifications",
        label="Notifications",
        description="System and workflow notifications across the platform.",
    ),
    PlatformCapability(
        code="settings",
        label="Settings",
        description="Shared platform configuration and user preferences.",
    ),
)


DEFAULT_ENTERPRISE_MODULES: tuple[EnterpriseModule, ...] = (
    EnterpriseModule(
        code="project_management",
        label="Project Management",
        description="Planning, delivery, portfolio, governance, and execution control.",
        default_enabled=True,
        stage="enabled",
        primary_capabilities=(
            "projects",
            "tasks",
            "resources",
            "costs",
            "timesheets",
            "portfolio",
            "governance",
        ),
    ),
    EnterpriseModule(
        code="inventory_procurement",
        label="Inventory & Procurement",
        description="Item master, storerooms, stock control, purchasing, and receiving workflows.",
        stage="available",
        primary_capabilities=("items", "storerooms", "stock", "purchasing"),
    ),
    EnterpriseModule(
        code="maintenance_management",
        label="Maintenance Management",
        description="Assets, work orders, preventive maintenance, and downtime control.",
        primary_capabilities=("assets", "work_orders", "maintenance_plans", "downtime"),
    ),
    EnterpriseModule(
        code="qhse",
        label="QHSE",
        description="Quality, health, safety, environment, incidents, inspections, and CAPA.",
        primary_capabilities=("incidents", "inspections", "audits", "capa"),
    ),
    EnterpriseModule(
        code="hr_management",
        label="HR Management",
        description="Employee operations, approved time intake, payroll preparation, approval, and export workflows.",
        primary_capabilities=("hr_workflows", "payroll_periods", "payroll_runs", "exports"),
    ),
)
def parse_module_codes(raw_value: str | None) -> set[str]:
    return {
        normalize_module_code(token)
        for token in (raw_value or "").split(",")
        if token.strip()
    }


def parse_enabled_module_codes(raw_value: str | None) -> set[str]:
    tokens = parse_module_codes(raw_value)
    if not tokens:
        tokens = {
            module.code
            for module in DEFAULT_ENTERPRISE_MODULES
            if module.default_enabled
        }
    return tokens


def parse_licensed_module_codes(raw_value: str | None) -> set[str]:
    tokens = parse_module_codes(raw_value)
    if not tokens:
        tokens = {
            module.code
            for module in DEFAULT_ENTERPRISE_MODULES
            if module.default_enabled
        }
    return tokens


def default_lifecycle_status(licensed: bool) -> str:
    return MODULE_LIFECYCLE_ACTIVE if licensed else MODULE_LIFECYCLE_INACTIVE


def normalize_lifecycle_status(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in MODULE_LIFECYCLE_STATUSES:
        allowed = ", ".join(MODULE_LIFECYCLE_STATUSES)
        raise ValidationError(
            f"Lifecycle status must be one of: {allowed}.",
            code="MODULE_STATUS_INVALID",
        )
    return normalized


__all__ = [
    "DEFAULT_ENTERPRISE_MODULES",
    "DEFAULT_PLATFORM_CAPABILITIES",
    "MODULE_LIFECYCLE_ACTIVE",
    "MODULE_LIFECYCLE_EXPIRED",
    "MODULE_LIFECYCLE_INACTIVE",
    "MODULE_LIFECYCLE_STATUSES",
    "MODULE_LIFECYCLE_SUSPENDED",
    "MODULE_LIFECYCLE_TRIAL",
    "MODULE_RUNTIME_ACCESS_STATUSES",
    "default_lifecycle_status",
    "normalize_lifecycle_status",
    "parse_enabled_module_codes",
    "parse_licensed_module_codes",
    "parse_module_codes",
]
