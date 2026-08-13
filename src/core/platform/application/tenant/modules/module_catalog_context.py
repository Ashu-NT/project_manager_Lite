from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.contract.repositories.tenant.modules.contracts import ModuleEntitlementRepository
from src.core.platform.contract.read.tenant.modules.module_entitlement_reader import (
    ModuleEntitlementReader,
    ModuleEntitlementSnapshot,
)

if TYPE_CHECKING:
    from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.tenant.modules.defaults import (
    MODULE_RUNTIME_ACCESS_STATUSES,
    default_lifecycle_status,
)
from src.core.platform.domain.tenant.modules.module_codes import normalize_module_code
from src.core.platform.domain.tenant.modules.subscription import ModuleEntitlementRecord


class ModuleCatalogContextMixin:
    _entitlement_repo: ModuleEntitlementRepository
    _entitlement_reader: ModuleEntitlementReader | None

    def _persist_state(self, record: ModuleEntitlementRecord) -> None:
        module_code = record.module_code
        normalized_record = record
        if self._entitlement_repo is None:
            if normalized_record.licensed:
                self._licensed_codes.add(module_code)
            else:
                self._licensed_codes.discard(module_code)
            if normalized_record.enabled and normalized_record.licensed:
                self._enabled_codes.add(module_code)
            else:
                self._enabled_codes.discard(module_code)
            return
        self._entitlement_repo.upsert(normalized_record)
        if self._session is not None:
            self._session.commit()

    def _active_tenant_id(self) -> str | None:
        if self._user_session is not None:
            return self._user_session.active_tenant_id()
        return None

    def _fetch_snapshot(self) -> ModuleEntitlementSnapshot | None:
        """One read, reusable for every derived question in one logical call
        (list_entitlements/shell_summary/snapshot each fetch at most once,
        not once per module) — the CQRS-pilot replacement for calling the
        write repository's list_all() from inside a per-module loop.

        Returns None when there's no reader wired, or no organization/tenant
        context yet — callers fall back to the pre-pilot repo-based path in
        that case, so behavior is unchanged for any caller not yet wired to
        an entitlement_reader."""
        if self._entitlement_reader is None:
            return None
        if not self._has_active_organization_context():
            return None
        # Prefer the session principal's already-validated ids (no query) over
        # _current_organization(), which fetches the full Organization row --
        # the same "fast path" TenantContextService.require_active_scope_ids()
        # uses for repository-level predicates.
        if self._user_session is not None:
            organization_id = self._user_session.active_organization_id()
        else:
            organization = self._current_organization()
            organization_id = organization.id if organization is not None else None
        tenant_id = self._active_tenant_id()
        if not organization_id or not tenant_id:
            return None
        return self._entitlement_reader.get_snapshot(
            tenant_id=tenant_id,
            organization_id=organization_id,
        )

    def _effective_records(
        self, snapshot: ModuleEntitlementSnapshot | None = None
    ) -> list[ModuleEntitlementRecord]:
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
        records = self._ensure_context_defaults(snapshot)
        if not records:
            return []
        return records

    def _ensure_context_defaults(
        self, snapshot: ModuleEntitlementSnapshot | None = None
    ) -> list[ModuleEntitlementRecord]:
        if self._entitlement_repo is None:
            return []
        if not self._has_active_organization_context():
            return []
        if snapshot is None:
            snapshot = self._fetch_snapshot()
        records = list(snapshot.records) if snapshot is not None else self._entitlement_repo.list_all()
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
        # The snapshot above (if any) predates this seeding write -- re-read
        # through the write repository directly rather than the now-stale
        # snapshot.
        return self._entitlement_repo.list_all()

    def _codes_from_records(self, records: list[ModuleEntitlementRecord]) -> tuple[set[str], set[str]]:
        if not records:
            if self._entitlement_repo is not None and not self._has_active_organization_context():
                return set(), set()
            return set(self._licensed_codes), set(self._enabled_codes)
        licensed_codes = {normalize_module_code(record.module_code) for record in records if record.licensed}
        enabled_codes = {
            normalize_module_code(record.module_code)
            for record in records
            if (
                record.licensed
                and record.enabled
                and record.lifecycle_status in MODULE_RUNTIME_ACCESS_STATUSES
            )
        }
        return licensed_codes, enabled_codes

    def _effective_codes(
        self, snapshot: ModuleEntitlementSnapshot | None = None
    ) -> tuple[set[str], set[str]]:
        records = self._effective_records(snapshot)
        return self._codes_from_records(records)

    def _current_organization(self) -> Organization | None:
        if self._organization_context_provider is None:
            return None
        return self._organization_context_provider()

    def _has_active_organization_context(self) -> bool:
        if self._user_session is not None:
            organization_id = self._user_session.active_organization_id()
            return bool(str(organization_id or "").strip())
        return self._current_organization() is not None


__all__ = ["ModuleCatalogContextMixin"]
