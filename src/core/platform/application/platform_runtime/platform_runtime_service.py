from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.core.platform.api.desktop_runtime.service_resolver import (
    ModuleRuntimeSnapshot,
    build_module_runtime_snapshot,
)
from src.core.platform.application.tenant.modules import ModuleCatalogService
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.application.master_data.org.organization_service import OrganizationService
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.shared.events.domain_events import domain_events


@dataclass(frozen=True)
class PlatformRuntimeContextSnapshot:
    context_label: str
    module_snapshot: ModuleRuntimeSnapshot


class PlatformRuntimeApplicationService:
    """Application-facing seam for active platform runtime context.

    Desktop UI and transport adapters use this orchestration contract instead
    of depending on shell-specific code or lower-level runtime services.
    """

    def __init__(
        self,
        *,
        module_catalog_service: ModuleCatalogService,
        organization_service: OrganizationService | None = None,
        tenant_context_service: TenantContextService | None = None,
        user_session: UserSessionContext | None = None,
        session: Session | None = None,
    ) -> None:
        self._module_catalog_service = module_catalog_service
        self._organization_service = organization_service
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._session = session

    @property
    def module_catalog_service(self) -> ModuleCatalogService:
        return self._module_catalog_service

    @property
    def organization_service(self) -> OrganizationService | None:
        return self._organization_service

    @property
    def tenant_context_service(self) -> TenantContextService | None:
        return self._tenant_context_service

    @property
    def user_session(self) -> UserSessionContext | None:
        return self._user_session

    def list_modules(self):
        return self._module_catalog_service.list_modules()

    def list_platform_capabilities(self):
        return self._module_catalog_service.list_platform_capabilities()

    def list_entitlements(self):
        return self._module_catalog_service.list_entitlements()

    def list_licensed_modules(self):
        return self._module_catalog_service.list_licensed_modules()

    def list_enabled_modules(self):
        return self._module_catalog_service.list_enabled_modules()

    def list_available_modules(self):
        return self._module_catalog_service.list_available_modules()

    def list_planned_modules(self):
        return self._module_catalog_service.list_planned_modules()

    def enabled_capability_codes(self) -> tuple[str, ...]:
        return self._module_catalog_service.enabled_capability_codes()

    def is_licensed(self, module_code: str) -> bool:
        return self._module_catalog_service.is_licensed(module_code)

    def is_enabled(self, module_code: str) -> bool:
        return self._module_catalog_service.is_enabled(module_code)

    def get_entitlement(self, module_code: str):
        return self._module_catalog_service.get_entitlement(module_code)

    def set_module_state(
        self,
        module_code: str,
        *,
        licensed: bool | None = None,
        enabled: bool | None = None,
        lifecycle_status: str | None = None,
    ):
        return self._module_catalog_service.set_module_state(
            module_code,
            licensed=licensed,
            enabled=enabled,
            lifecycle_status=lifecycle_status,
        )

    def shell_summary(self) -> str:
        return self._module_catalog_service.shell_summary()

    def current_context_label(self) -> str:
        return self._module_catalog_service.current_context_label()

    def snapshot(self) -> PlatformRuntimeContextSnapshot:
        module_snapshot = build_module_runtime_snapshot(self._module_catalog_service)
        return PlatformRuntimeContextSnapshot(
            context_label=module_snapshot.context_label,
            module_snapshot=module_snapshot,
        )

    def list_organizations(self, *, active_only: bool | None = None) -> list[Organization]:
        if self._organization_service is None:
            return []
        return self._organization_service.list_organizations(active_only=active_only)

    def get_active_organization(self) -> Organization | None:
        if self._tenant_context_service is not None:
            return self._tenant_context_service.get_active_organization()
        return None

    def create_organization(
        self,
        *,
        organization_code: str,
        display_name: str,
        timezone_name: str,
        base_currency: str,
        is_active: bool,
    ) -> Organization:
        if self._organization_service is None:
            raise RuntimeError("Organization service is not configured.")
        return self._organization_service.create_organization(
            organization_code=organization_code,
            display_name=display_name,
            timezone_name=timezone_name,
            base_currency=base_currency,
            is_active=is_active,
        )

    def update_organization(
        self,
        organization_id: str,
        *,
        organization_code: str | None = None,
        display_name: str | None = None,
        timezone_name: str | None = None,
        base_currency: str | None = None,
        is_active: bool | None = None,
        expected_version: int | None = None,
    ) -> Organization:
        if self._organization_service is None:
            raise RuntimeError("Organization service is not configured.")
        return self._organization_service.update_organization(
            organization_id,
            organization_code=organization_code,
            display_name=display_name,
            timezone_name=timezone_name,
            base_currency=base_currency,
            is_active=is_active,
            expected_version=expected_version,
        )

    def provision_organization(
        self,
        *,
        organization_code: str,
        display_name: str,
        timezone_name: str,
        base_currency: str,
        is_active: bool,
        initial_module_codes: list[str] | tuple[str, ...] | set[str] | None = None,
    ) -> Organization:
        if self._organization_service is None:
            raise RuntimeError("Organization service is not configured.")
        if self._session is None:
            raise RuntimeError("Session is not configured.")

        selected_module_codes = (
            set(initial_module_codes)
            if initial_module_codes is not None
            else {
                module.code
                for module in self._module_catalog_service.list_modules()
                if module.default_enabled and module.stage != "planned"
            }
        )
        # Stage every write with commit=False so the organization row, its
        # module entitlements, and (if requested) its activation all commit
        # in one transaction, together with their audit entries (ADR-003).
        organization = self._organization_service.create_organization(
            organization_code=organization_code,
            display_name=display_name,
            timezone_name=timezone_name,
            base_currency=base_currency,
            is_active=False,
            commit=False,
        )
        self._module_catalog_service.provision_organization_entitlements(
            organization.id,
            licensed_module_codes=selected_module_codes,
            enabled_module_codes=selected_module_codes,
            commit=False,
        )
        if is_active:
            self._require_settings_manage("set active organization context")
            organization = self._organization_service.set_active_organization(
                organization.id, commit=False
            )
        self._session.commit()
        domain_events.organizations_changed.emit(organization.id)
        if is_active:
            if self._tenant_context_service is None:
                raise RuntimeError("Tenant context service is not configured.")
            self._tenant_context_service.set_active_organization(organization.id)
        return organization

    def set_active_organization(self, organization_id: str) -> Organization:
        if self._organization_service is None:
            raise RuntimeError("Organization service is not configured.")
        # Routes through OrganizationService so activation is actually
        # persisted (is_active=True, other organizations deactivated, audited)
        # before the in-memory tenant context is rebuilt — calling
        # tenant_context_service directly here previously skipped persistence
        # entirely, which also made this the root cause of provision_organization's
        # is_active=True branch always raising ORGANIZATION_INACTIVE.
        return self._organization_service.set_active_organization(organization_id)

    def _require_settings_manage(self, operation_label: str) -> None:
        require_permission(
            self._user_session,
            "settings.manage",
            operation_label=operation_label,
        )


def resolve_platform_runtime_application_service(
    *,
    platform_runtime_application_service: object | None,
    module_catalog_service: object | None,
    organization_service: OrganizationService | None = None,
    tenant_context_service: TenantContextService | None = None,
    user_session: UserSessionContext | None = None,
) -> object | None:
    if isinstance(platform_runtime_application_service, PlatformRuntimeApplicationService):
        if (
            module_catalog_service is None
            or (
                platform_runtime_application_service.module_catalog_service
                is module_catalog_service
                and (
                    organization_service is None
                    or platform_runtime_application_service.organization_service
                    is organization_service
                )
                and (
                    tenant_context_service is None
                    or platform_runtime_application_service.tenant_context_service
                    is tenant_context_service
                )
                and (
                    user_session is None
                    or platform_runtime_application_service.user_session is user_session
                )
            )
        ):
            return platform_runtime_application_service

    if isinstance(module_catalog_service, ModuleCatalogService):
        return PlatformRuntimeApplicationService(
            module_catalog_service=module_catalog_service,
            organization_service=organization_service,
            tenant_context_service=tenant_context_service,
            user_session=user_session,
        )
    return platform_runtime_application_service


__all__ = [
    "PlatformRuntimeApplicationService",
    "PlatformRuntimeContextSnapshot",
    "resolve_platform_runtime_application_service",
]
