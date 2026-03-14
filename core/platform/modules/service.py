from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy.orm import Session

from core.platform.audit.helpers import record_audit
from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import NotFoundError, ValidationError
from core.platform.notifications.domain_events import domain_events
from core.platform.modules.repository import ModuleEntitlementRecord, ModuleEntitlementRepository


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
        entitlement_repo: ModuleEntitlementRepository | None = None,
        session: Session | None = None,
        user_session=None,
        audit_service=None,
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
        self._licensed_codes = set(code for code in licensed if code in known_codes)
        self._enabled_codes = set(code for code in enabled if code in self._licensed_codes)
        self._entitlement_repo = entitlement_repo
        self._session = session
        self._user_session = user_session
        self._audit_service = audit_service

    def bootstrap_defaults(self) -> None:
        if self._entitlement_repo is None:
            return
        existing_by_code = {
            record.module_code: record
            for record in self._entitlement_repo.list_all()
        }
        changed = False
        for module in self._modules:
            if module.code in existing_by_code:
                continue
            self._entitlement_repo.upsert(
                ModuleEntitlementRecord(
                    module_code=module.code,
                    licensed=module.code in self._licensed_codes,
                    enabled=module.code in self._enabled_codes and module.code in self._licensed_codes,
                )
            )
            changed = True
        if changed and self._session is not None:
            self._session.commit()

    def list_modules(self) -> list[EnterpriseModule]:
        return list(self._modules)

    def list_platform_capabilities(self) -> list[PlatformCapability]:
        return list(self._platform_capabilities)

    def list_entitlements(self) -> list[ModuleEntitlement]:
        return [self._build_entitlement(module) for module in self._modules]

    def list_licensed_modules(self) -> list[EnterpriseModule]:
        licensed_codes, _enabled_codes = self._effective_codes()
        return [module for module in self._modules if module.code in licensed_codes]

    def list_enabled_modules(self) -> list[EnterpriseModule]:
        _licensed_codes, enabled_codes = self._effective_codes()
        return [module for module in self._modules if module.code in enabled_codes]

    def list_available_modules(self) -> list[EnterpriseModule]:
        licensed_codes, _enabled_codes = self._effective_codes()
        return [
            module
            for module in self._modules
            if module.stage != "planned" and module.code not in licensed_codes
        ]

    def list_planned_modules(self) -> list[EnterpriseModule]:
        return [module for module in self._modules if module.stage == "planned"]

    def enabled_capability_codes(self) -> tuple[str, ...]:
        capability_codes = {capability.code for capability in self._platform_capabilities}
        for module in self.list_enabled_modules():
            capability_codes.update(module.primary_capabilities)
        return tuple(sorted(capability_codes))

    def is_licensed(self, module_code: str) -> bool:
        licensed_codes, _enabled_codes = self._effective_codes()
        return str(module_code).strip().lower() in licensed_codes

    def is_enabled(self, module_code: str) -> bool:
        _licensed_codes, enabled_codes = self._effective_codes()
        return str(module_code).strip().lower() in enabled_codes

    def get_entitlement(self, module_code: str) -> ModuleEntitlement | None:
        target_code = str(module_code).strip().lower()
        for module in self._modules:
            if module.code == target_code:
                return self._build_entitlement(module)
        return None

    def set_module_state(
        self,
        module_code: str,
        *,
        licensed: bool | None = None,
        enabled: bool | None = None,
    ) -> ModuleEntitlement:
        require_permission(
            self._user_session,
            "settings.manage",
            operation_label="manage module entitlements",
        )
        module = self._require_module(module_code)
        current = self.get_entitlement(module.code)
        if current is None:
            raise NotFoundError("Module not found.", code="MODULE_NOT_FOUND")

        next_licensed = current.licensed if licensed is None else bool(licensed)
        next_enabled = current.enabled if enabled is None else bool(enabled)

        if module.stage == "planned" and (next_licensed or next_enabled):
            raise ValidationError(
                f"{module.label} is planned and cannot be licensed or enabled yet.",
                code="MODULE_NOT_AVAILABLE",
            )
        if not next_licensed:
            next_enabled = False
        if next_enabled and not next_licensed:
            raise ValidationError(
                "A module must be licensed before it can be enabled.",
                code="MODULE_NOT_LICENSED",
            )

        self._persist_state(
            ModuleEntitlementRecord(
                module_code=module.code,
                licensed=next_licensed,
                enabled=next_enabled,
            )
        )
        record_audit(
            self,
            action="module.entitlement.update",
            entity_type="module_entitlement",
            entity_id=module.code,
            details={
                "module_code": module.code,
                "licensed": str(next_licensed),
                "enabled": str(next_enabled),
                "stage": module.stage,
            },
        )
        domain_events.modules_changed.emit(module.code)
        entitlement = self.get_entitlement(module.code)
        if entitlement is None:
            raise NotFoundError("Module entitlement not found after update.", code="MODULE_NOT_FOUND")
        return entitlement

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
        licensed_codes, enabled_codes = self._effective_codes()
        return ModuleEntitlement(
            module=module,
            licensed=module.code in licensed_codes,
            enabled=module.code in enabled_codes,
        )

    def _effective_codes(self) -> tuple[set[str], set[str]]:
        if self._entitlement_repo is None:
            return set(self._licensed_codes), set(self._enabled_codes)
        records = self._entitlement_repo.list_all()
        if not records:
            return set(self._licensed_codes), set(self._enabled_codes)
        licensed_codes = {record.module_code for record in records if record.licensed}
        enabled_codes = {
            record.module_code
            for record in records
            if record.licensed and record.enabled
        }
        return licensed_codes, enabled_codes

    def _persist_state(self, record: ModuleEntitlementRecord) -> None:
        if self._entitlement_repo is None:
            if record.licensed:
                self._licensed_codes.add(record.module_code)
            else:
                self._licensed_codes.discard(record.module_code)
            if record.enabled and record.licensed:
                self._enabled_codes.add(record.module_code)
            else:
                self._enabled_codes.discard(record.module_code)
            return
        self._entitlement_repo.upsert(record)
        if self._session is not None:
            self._session.commit()

    def _require_module(self, module_code: str) -> EnterpriseModule:
        target_code = str(module_code).strip().lower()
        for module in self._modules:
            if module.code == target_code:
                return module
        raise NotFoundError("Module not found.", code="MODULE_NOT_FOUND")


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
