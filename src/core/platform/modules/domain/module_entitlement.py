from __future__ import annotations

from dataclasses import dataclass

from src.core.platform.modules.domain.module_definition import EnterpriseModule


@dataclass(frozen=True)
class ModuleEntitlement:
    module: EnterpriseModule
    licensed: bool
    enabled: bool
    lifecycle_status: str

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

    @property
    def runtime_enabled(self) -> bool:
        from src.core.platform.modules.domain.defaults import MODULE_RUNTIME_ACCESS_STATUSES

        return bool(
            self.licensed
            and self.enabled
            and self.lifecycle_status in MODULE_RUNTIME_ACCESS_STATUSES
        )

    @property
    def lifecycle_label(self) -> str:
        return self.lifecycle_status.replace("_", " ").title()

    @property
    def lifecycle_alert(self) -> bool:
        from src.core.platform.modules.domain.defaults import (
            MODULE_LIFECYCLE_EXPIRED,
            MODULE_LIFECYCLE_SUSPENDED,
            MODULE_LIFECYCLE_TRIAL,
        )

        return self.lifecycle_status in {
            MODULE_LIFECYCLE_TRIAL,
            MODULE_LIFECYCLE_SUSPENDED,
            MODULE_LIFECYCLE_EXPIRED,
        }


@dataclass(frozen=True)
class ModuleCatalogSnapshot:
    enabled_modules: tuple[EnterpriseModule, ...]
    licensed_modules: tuple[EnterpriseModule, ...]
    available_modules: tuple[EnterpriseModule, ...]
    planned_modules: tuple[EnterpriseModule, ...]
    context_label: str


__all__ = ["ModuleCatalogSnapshot", "ModuleEntitlement"]
