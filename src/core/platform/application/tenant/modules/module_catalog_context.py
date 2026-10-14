"""Read-side state shared by the module catalog query and entitlement command handlers.

`ModuleCatalogContext` owns the installed module definitions, the install-profile default
licensed/enabled codes, and the active-organization entitlement resolution (reader snapshot,
repository fallback and lazy default seeding). It performs no permission checks and owns no
UnitOfWork -- the only write it ever performs is the pre-existing lazy defaults seeding on the
shared session (`ensure_context_defaults`)."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.contract.read.tenant.modules.module_entitlement_reader import (
    ModuleEntitlementReader,
    ModuleEntitlementSnapshot,
)
from src.core.platform.contract.repositories.tenant.modules.contracts import (
    ModuleEntitlementRepository,
)
from src.core.platform.domain.tenant.modules.defaults import (
    DEFAULT_PLATFORM_CAPABILITIES,
    MODULE_RUNTIME_ACCESS_STATUSES,
    default_lifecycle_status,
)
from src.core.platform.domain.tenant.modules.module_codes import normalize_module_code
from src.core.platform.domain.tenant.modules.module_definition import (
    EnterpriseModule,
    PlatformCapability,
)
from src.core.platform.domain.tenant.modules.module_entitlement import ModuleEntitlement
from src.core.platform.domain.tenant.modules.subscription import ModuleEntitlementRecord

if TYPE_CHECKING:
    from src.core.platform.domain.master_data.org import Organization


class ModuleCatalogContext:
    def __init__(
        self,
        *,
        modules: Iterable[EnterpriseModule],
        enabled_codes: Iterable[str] | None,
        licensed_codes: Iterable[str] | None = None,
        platform_capabilities: Iterable[PlatformCapability] | None = None,
        entitlement_repo: ModuleEntitlementRepository | None = None,
        entitlement_reader: ModuleEntitlementReader | None = None,
        session: Session | None = None,
        user_session: Any = None,
        organization_context_provider: Callable[[], Organization | None] | None = None,
        read_only: bool = False,
    ) -> None:
        known_modules = tuple(modules)
        known_codes = {module.code for module in known_modules}
        default_codes = {module.code for module in known_modules if module.default_enabled}
        licensed = (
            {normalize_module_code(code) for code in licensed_codes if str(code).strip()}
            if licensed_codes is not None
            else set(default_codes)
        )
        enabled = (
            {normalize_module_code(code) for code in enabled_codes if str(code).strip()}
            if enabled_codes is not None
            else set(licensed)
        )
        self._modules = known_modules
        self._read_only = read_only
        self._platform_capabilities = tuple(platform_capabilities or DEFAULT_PLATFORM_CAPABILITIES)
        self._licensed_codes = {code for code in licensed if code in known_codes}
        self._enabled_codes = {code for code in enabled if code in self._licensed_codes}
        self._entitlement_repo = entitlement_repo
        self._entitlement_reader = entitlement_reader
        self._session = session
        self._user_session = user_session
        self._organization_context_provider = organization_context_provider

    @property
    def modules(self) -> tuple[EnterpriseModule, ...]:
        return self._modules

    @property
    def platform_capabilities(self) -> tuple[PlatformCapability, ...]:
        return self._platform_capabilities

    # -- scope ---------------------------------------------------------------------------------

    def active_tenant_id(self) -> str | None:
        if self._user_session is not None:
            return self._user_session.active_tenant_id()
        return None

    def current_organization(self) -> Organization | None:
        if self._organization_context_provider is None:
            return None
        return self._organization_context_provider()

    def has_active_organization_context(self) -> bool:
        if self._user_session is not None:
            organization_id = self._user_session.active_organization_id()
            return bool(str(organization_id or "").strip())
        return self.current_organization() is not None

    # -- entitlement resolution ----------------------------------------------------------------

    def fetch_snapshot(self) -> ModuleEntitlementSnapshot | None:
        """One read, reusable for every derived question in one logical call
        (list_entitlements/shell_summary/snapshot each fetch at most once,
        not once per module).

        Returns None when there's no reader wired, or no organization/tenant
        context yet -- callers fall back to the repo-based path in that case."""
        if self._entitlement_reader is None:
            return None
        if not self.has_active_organization_context():
            return None
        # Prefer the session principal's already-validated ids (no query) over
        # current_organization(), which fetches the full Organization row --
        # the same "fast path" TenantContextService.require_active_scope_ids()
        # uses for repository-level predicates.
        if self._user_session is not None:
            organization_id = self._user_session.active_organization_id()
        else:
            organization = self.current_organization()
            organization_id = organization.id if organization is not None else None
        tenant_id = self.active_tenant_id()
        if not organization_id or not tenant_id:
            return None
        return self._entitlement_reader.get_snapshot(
            tenant_id=tenant_id,
            organization_id=organization_id,
        )

    def effective_records(
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
        records = self.ensure_context_defaults(snapshot)
        if not records:
            return []
        return records

    def ensure_context_defaults(
        self, snapshot: ModuleEntitlementSnapshot | None = None
    ) -> list[ModuleEntitlementRecord]:
        if self._entitlement_repo is None:
            return []
        if not self.has_active_organization_context():
            return []
        if snapshot is None:
            snapshot = self.fetch_snapshot()
        records = list(snapshot.records) if snapshot is not None else self._entitlement_repo.list_all()
        if records or self._read_only:
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

    def codes_from_records(self, records: list[ModuleEntitlementRecord]) -> tuple[set[str], set[str]]:
        if not records:
            if self._read_only:
                return set(), set()
            if self._entitlement_repo is not None and not self.has_active_organization_context():
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

    def effective_codes(
        self, snapshot: ModuleEntitlementSnapshot | None = None
    ) -> tuple[set[str], set[str]]:
        return self.codes_from_records(self.effective_records(snapshot))

    def build_entitlement(
        self, module: EnterpriseModule, records_by_code: dict[str, ModuleEntitlementRecord]
    ) -> ModuleEntitlement:
        record = records_by_code.get(module.code)
        missing_organization_context = (
            self._entitlement_repo is not None and not self.has_active_organization_context()
        )
        if record is None:
            if missing_organization_context:
                licensed = False
                enabled = False
                lifecycle_status = default_lifecycle_status(False)
            else:
                licensed = module.code in self._licensed_codes
                enabled = module.code in self._enabled_codes
                lifecycle_status = default_lifecycle_status(licensed)
        else:
            licensed = record.licensed
            enabled = record.enabled
            lifecycle_status = record.lifecycle_status
        return ModuleEntitlement(
            module=module,
            licensed=licensed,
            enabled=enabled,
            lifecycle_status=lifecycle_status,
        )

    # -- module definitions --------------------------------------------------------------------

    def require_module(self, module_code: str) -> EnterpriseModule:
        target_code = normalize_module_code(module_code)
        for module in self._modules:
            if module.code == target_code:
                return module
        raise NotFoundError("Module not found.", code="MODULE_NOT_FOUND")

    def normalize_selected_module_codes(self, module_codes: Iterable[str] | None) -> set[str]:
        normalized_codes = {
            normalize_module_code(code)
            for code in (module_codes or ())
            if str(code or "").strip()
        }
        for module_code in normalized_codes:
            self.require_module(module_code)
        return normalized_codes


__all__ = ["ModuleCatalogContext"]
