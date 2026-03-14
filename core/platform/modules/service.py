from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class PlatformCapability:
    code: str
    label: str
    description: str
    always_on: bool = True


@dataclass(frozen=True)
class EnterpriseModule:
    code: str
    label: str
    description: str
    default_enabled: bool = False
    stage: str = "planned"
    primary_capabilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModuleEntitlement:
    module: EnterpriseModule
    licensed: bool
    enabled: bool

    @property
    def code(self) -> str:
        return self.module.code

    @property
    def label(self) -> str:
        return self.module.label

    @property
    def stage(self) -> str:
        return self.module.stage

    @property
    def available_to_license(self) -> bool:
        return self.module.stage != "planned" and not self.licensed

    @property
    def planned(self) -> bool:
        return self.module.stage == "planned" and not self.enabled


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
        code="payroll",
        label="Payroll",
        description="Approved time intake, payroll preparation, approval, and export workflows.",
        primary_capabilities=("payroll_periods", "payroll_runs", "exports"),
    ),
)


def parse_module_codes(raw_value: str | None) -> set[str]:
    return {
        token.strip().lower()
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


@dataclass(frozen=True)
class ModuleCatalogSnapshot:
    enabled_modules: tuple[EnterpriseModule, ...]
    licensed_modules: tuple[EnterpriseModule, ...]
    available_modules: tuple[EnterpriseModule, ...]
    planned_modules: tuple[EnterpriseModule, ...]


class ModuleCatalogService:
    def __init__(
        self,
        *,
        modules: Iterable[EnterpriseModule],
        enabled_codes: Iterable[str] | None,
        licensed_codes: Iterable[str] | None = None,
        platform_capabilities: Iterable[PlatformCapability] | None = None,
    ) -> None:
        known_modules = tuple(modules)
        known_codes = {module.code for module in known_modules}
        default_codes = {
            module.code
            for module in known_modules
            if module.default_enabled
        }
        licensed = (
            {str(code).strip().lower() for code in licensed_codes if str(code).strip()}
            if licensed_codes is not None
            else set(default_codes)
        )
        enabled = (
            {str(code).strip().lower() for code in enabled_codes if str(code).strip()}
            if enabled_codes is not None
            else set(licensed)
        )
        self._modules = known_modules
        self._platform_capabilities = tuple(platform_capabilities or DEFAULT_PLATFORM_CAPABILITIES)
        self._licensed_codes = frozenset(code for code in licensed if code in known_codes)
        self._enabled_codes = frozenset(code for code in enabled if code in self._licensed_codes)

    def list_modules(self) -> list[EnterpriseModule]:
        return list(self._modules)

    def list_platform_capabilities(self) -> list[PlatformCapability]:
        return list(self._platform_capabilities)

    def list_entitlements(self) -> list[ModuleEntitlement]:
        return [self._build_entitlement(module) for module in self._modules]

    def list_licensed_modules(self) -> list[EnterpriseModule]:
        return [module for module in self._modules if module.code in self._licensed_codes]

    def list_enabled_modules(self) -> list[EnterpriseModule]:
        return [module for module in self._modules if module.code in self._enabled_codes]

    def list_available_modules(self) -> list[EnterpriseModule]:
        return [
            module
            for module in self._modules
            if module.stage != "planned" and module.code not in self._licensed_codes
        ]

    def list_planned_modules(self) -> list[EnterpriseModule]:
        return [module for module in self._modules if module.stage == "planned"]

    def enabled_capability_codes(self) -> tuple[str, ...]:
        capability_codes = {capability.code for capability in self._platform_capabilities}
        for module in self.list_enabled_modules():
            capability_codes.update(module.primary_capabilities)
        return tuple(sorted(capability_codes))

    def is_licensed(self, module_code: str) -> bool:
        return str(module_code).strip().lower() in self._licensed_codes

    def is_enabled(self, module_code: str) -> bool:
        return str(module_code).strip().lower() in self._enabled_codes

    def get_entitlement(self, module_code: str) -> ModuleEntitlement | None:
        target_code = str(module_code).strip().lower()
        for module in self._modules:
            if module.code == target_code:
                return self._build_entitlement(module)
        return None

    def snapshot(self) -> ModuleCatalogSnapshot:
        return ModuleCatalogSnapshot(
            enabled_modules=tuple(self.list_enabled_modules()),
            licensed_modules=tuple(self.list_licensed_modules()),
            available_modules=tuple(self.list_available_modules()),
            planned_modules=tuple(self.list_planned_modules()),
        )

    def shell_summary(self) -> str:
        enabled_labels = ", ".join(module.label for module in self.list_enabled_modules()) or "None"
        licensed_labels = ", ".join(module.label for module in self.list_licensed_modules()) or "None"
        available_labels = ", ".join(module.label for module in self.list_available_modules()) or "None"
        planned_labels = ", ".join(module.label for module in self.list_planned_modules()) or "None"
        return (
            f"Platform Base active. Enabled: {enabled_labels}. "
            f"Licensed: {licensed_labels}. Available: {available_labels}. Planned: {planned_labels}."
        )

    def _build_entitlement(self, module: EnterpriseModule) -> ModuleEntitlement:
        return ModuleEntitlement(
            module=module,
            licensed=module.code in self._licensed_codes,
            enabled=module.code in self._enabled_codes,
        )


def build_default_module_catalog(
    raw_enabled_modules: str | None = None,
    raw_licensed_modules: str | None = None,
) -> ModuleCatalogService:
    resolved_enabled_raw = (
        raw_enabled_modules if raw_enabled_modules is not None else os.getenv("PM_ENABLED_MODULES")
    )
    resolved_licensed_raw = (
        raw_licensed_modules
        if raw_licensed_modules is not None
        else (
            raw_enabled_modules
            if raw_enabled_modules is not None
            else (
                os.getenv("PM_LICENSED_MODULES")
                if os.getenv("PM_LICENSED_MODULES") is not None
                else resolved_enabled_raw
            )
        )
    )
    return ModuleCatalogService(
        modules=DEFAULT_ENTERPRISE_MODULES,
        enabled_codes=parse_enabled_module_codes(
            resolved_enabled_raw if resolved_enabled_raw is not None else resolved_licensed_raw
        ),
        licensed_codes=parse_licensed_module_codes(resolved_licensed_raw),
    )


ModuleCatalogEntry = EnterpriseModule


__all__ = [
    "DEFAULT_PLATFORM_CAPABILITIES",
    "DEFAULT_ENTERPRISE_MODULES",
    "EnterpriseModule",
    "ModuleCatalogEntry",
    "ModuleCatalogService",
    "ModuleCatalogSnapshot",
    "ModuleEntitlement",
    "PlatformCapability",
    "build_default_module_catalog",
    "parse_enabled_module_codes",
    "parse_licensed_module_codes",
    "parse_module_codes",
]
