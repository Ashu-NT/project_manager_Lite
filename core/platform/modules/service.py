from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class EnterpriseModule:
    code: str
    label: str
    description: str
    default_enabled: bool = False
    stage: str = "planned"
    primary_capabilities: tuple[str, ...] = ()


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


def parse_enabled_module_codes(raw_value: str | None) -> set[str]:
    tokens = {
        token.strip().lower()
        for token in (raw_value or "").split(",")
        if token.strip()
    }
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
    planned_modules: tuple[EnterpriseModule, ...]


class ModuleCatalogService:
    def __init__(
        self,
        *,
        modules: Iterable[EnterpriseModule],
        enabled_codes: Iterable[str],
    ) -> None:
        known_modules = tuple(modules)
        enabled = {str(code).strip().lower() for code in enabled_codes if str(code).strip()}
        if not enabled:
            enabled = {
                module.code
                for module in known_modules
                if module.default_enabled
            }
        self._modules = known_modules
        self._enabled_codes = frozenset(enabled)

    def list_modules(self) -> list[EnterpriseModule]:
        return list(self._modules)

    def list_enabled_modules(self) -> list[EnterpriseModule]:
        return [module for module in self._modules if module.code in self._enabled_codes]

    def list_planned_modules(self) -> list[EnterpriseModule]:
        return [module for module in self._modules if module.code not in self._enabled_codes]

    def is_enabled(self, module_code: str) -> bool:
        return str(module_code).strip().lower() in self._enabled_codes

    def snapshot(self) -> ModuleCatalogSnapshot:
        return ModuleCatalogSnapshot(
            enabled_modules=tuple(self.list_enabled_modules()),
            planned_modules=tuple(self.list_planned_modules()),
        )

    def shell_summary(self) -> str:
        enabled_labels = ", ".join(module.label for module in self.list_enabled_modules()) or "None"
        planned_labels = ", ".join(module.label for module in self.list_planned_modules()) or "None"
        return f"Active module: {enabled_labels}. Planned: {planned_labels}."


def build_default_module_catalog(raw_enabled_modules: str | None = None) -> ModuleCatalogService:
    return ModuleCatalogService(
        modules=DEFAULT_ENTERPRISE_MODULES,
        enabled_codes=parse_enabled_module_codes(
            raw_enabled_modules if raw_enabled_modules is not None else os.getenv("PM_ENABLED_MODULES")
        ),
    )


ModuleCatalogEntry = EnterpriseModule


__all__ = [
    "DEFAULT_ENTERPRISE_MODULES",
    "EnterpriseModule",
    "ModuleCatalogEntry",
    "ModuleCatalogService",
    "ModuleCatalogSnapshot",
    "build_default_module_catalog",
    "parse_enabled_module_codes",
]
