from __future__ import annotations

from core.platform.modules.defaults import MODULE_RUNTIME_ACCESS_STATUSES, default_lifecycle_status
from core.platform.modules.repository import ModuleEntitlementRecord


class ModuleCatalogContextMixin:
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

    def _effective_records(self) -> list[ModuleEntitlementRecord]:
        if self._entitlement_repo is None:
            return [
                ModuleEntitlementRecord(
                    module_code=module.code,
                    licensed=module.code in self._licensed_codes,
                    enabled=module.code in self._enabled_codes and module.code in self._licensed_codes,
                    lifecycle_status=default_lifecycle_status(module.code in self._licensed_codes),
                )
                for module in self._modules
            ]
        records = self._ensure_context_defaults()
        if not records:
            return []
        return records

    def _ensure_context_defaults(self) -> list[ModuleEntitlementRecord]:
        if self._entitlement_repo is None:
            return []
        records = self._entitlement_repo.list_all()
        if records:
            return records
        changed = False
        for module in self._modules:
            self._entitlement_repo.upsert(
                ModuleEntitlementRecord(
                    module_code=module.code,
                    licensed=module.code in self._licensed_codes,
                    enabled=module.code in self._enabled_codes and module.code in self._licensed_codes,
                    lifecycle_status=default_lifecycle_status(module.code in self._licensed_codes),
                )
            )
            changed = True
        if changed and self._session is not None:
            self._session.commit()
        return self._entitlement_repo.list_all()

    def _effective_codes(self) -> tuple[set[str], set[str]]:
        records = self._effective_records()
        if not records:
            return set(self._licensed_codes), set(self._enabled_codes)
        licensed_codes = {record.module_code for record in records if record.licensed}
        enabled_codes = {
            record.module_code
            for record in records
            if (
                record.licensed
                and record.enabled
                and record.lifecycle_status in MODULE_RUNTIME_ACCESS_STATUSES
            )
        }
        return licensed_codes, enabled_codes

    def _current_organization(self):
        if self._organization_context_provider is None:
            return None
        return self._organization_context_provider()


__all__ = ["ModuleCatalogContextMixin"]
