from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

from src.core.platform.api.desktop_runtime.service_resolver import (
    ModuleRuntimeSnapshot,
    build_module_runtime_snapshot,
)
from src.core.platform.application.tenant.modules import ModuleCatalogService
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.persistence.platform_provisioning_unit_of_work import (
    PlatformProvisioningUnitOfWorkFactory,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.application.master_data.org.organization_service import OrganizationService
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.shared.events.domain_event_context import DomainEventContext


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
        provisioning_uow_factory: PlatformProvisioningUnitOfWorkFactory | None = None,
    ) -> None:
        self._module_catalog_service = module_catalog_service
        self._organization_service = organization_service
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._provisioning_uow_factory = provisioning_uow_factory

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

    def get_current_permissions(self) -> frozenset[str]:
        """The current session principal's effective permission codes.

        Used by the QML shell to hide navigation destinations/actions the
        current user has no backend permission for, rather than showing
        them and letting the resulting desktop-API call fail server-side.
        Returns an empty set (nothing visible) if there is no authenticated
        principal, matching the fail-closed posture used everywhere else.
        """
        if self._user_session is None or self._user_session.principal is None:
            return frozenset()
        return frozenset(self._user_session.principal.permissions)

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

    def get_organization_count(self) -> int:
        if self._organization_service is None:
            return 0
        return self._organization_service.get_organization_count()

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
        if self._provisioning_uow_factory is None:
            raise RuntimeError("Provisioning UnitOfWork factory is not configured.")

        # P4C (Platform Runtime Organization Provisioning Transaction Convergence): organization
        # creation, module entitlement provisioning, and (if requested) activation now all
        # participate in ONE fresh `PlatformProvisioningUnitOfWork` -- never the shared,
        # process-lifetime Session, and never a nested UnitOfWork inside `OrganizationService`.
        # `create_organization()`/`set_active_organization()` are not called here (each opens its
        # OWN fresh `OrganizationUnitOfWork`, which would split this transaction in two); instead
        # this method calls the same shared, transaction-agnostic business operations those
        # methods themselves call (`_create_organization_using`/`_activate_organization_using`),
        # passing this provisioning UnitOfWork's own repository/audit-owner -- one implementation
        # of each business rule, two different transaction owners (ADR-005 Section 9/24's "one
        # business operation, one transaction owner" principle, applied to provisioning).
        require_permission(self._user_session, "settings.manage", operation_label="provision organization")
        tenant_id = self._organization_service.require_current_tenant_id(
            operation_label="provision organization"
        )
        if is_active:
            self._require_settings_manage("set active organization context")

        selected_module_codes = (
            set(initial_module_codes)
            if initial_module_codes is not None
            else {
                module.code
                for module in self._module_catalog_service.list_modules()
                if module.default_enabled and module.stage != "planned"
            }
        )

        context = DomainEventContext(correlation_id=generate_id())
        with self._provisioning_uow_factory.create(context=context) as uow:
            try:
                organization = self._organization_service._create_organization_using(
                    uow.organizations,
                    uow,
                    organization_code=organization_code,
                    display_name=display_name,
                    timezone_name=timezone_name,
                    base_currency=base_currency,
                    is_active=False,
                    tenant_id=tenant_id,
                )
                # A throwaway `ModuleCatalogService` instance bound to this provisioning UoW's own
                # fresh Session -- reuses `provision_organization_entitlements`'s existing,
                # unmodified business logic (module catalog metadata is read-only ambient data,
                # safely shared from the long-lived instance) without duplicating it, mirroring
                # the same "fresh instance of the same service class" pattern used for the 8
                # approval-backed PM/Inventory services (P4-PRE Step 1). Never touches the
                # long-lived `module_catalog_service`'s own in-memory
                # licensed/enabled-module-code state -- that instance is untouched by this call.
                provisioning_module_catalog_service = ModuleCatalogService(
                    modules=self._module_catalog_service.list_modules(),
                    enabled_codes=None,
                    licensed_codes=None,
                    platform_capabilities=self._module_catalog_service.list_platform_capabilities(),
                    entitlement_repo=uow.entitlements,
                    session=uow._session,
                    user_session=self._user_session,
                    enterprise_audit_service=uow._enterprise_audit_service,
                )
                provisioning_module_catalog_service.provision_organization_entitlements(
                    organization.id,
                    licensed_module_codes=selected_module_codes,
                    enabled_module_codes=selected_module_codes,
                    commit=False,
                )
                if is_active:
                    organization = self._organization_service._activate_organization_using(
                        uow.organizations, uow, organization_id=organization.id, tenant_id=tenant_id
                    )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError(
                    "Organization code already exists.", code="ORGANIZATION_CODE_EXISTS"
                ) from exc
        # Runtime context change follows commit, never precedes or survives a rolled-back
        # provisioning transaction. (P5A: the legacy `organizations_changed` reaction is now
        # driven post-commit from the committed `OrganizationCreated` fact recorded inside
        # `_create_organization_using`, via the registered legacy-compatibility handler -- never
        # emitted directly here, so standalone creation and provisioning both produce exactly one
        # legacy reaction from the same business fact.)
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
