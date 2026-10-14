"""Organization module-entitlement provisioning.

`ModuleEntitlementProvisioningHandler` seeds a newly created organization's entitlements
inside the caller-owned provisioning UnitOfWork (the organization and its entitlements commit
together) and publishes the post-commit entitlement staleness hint."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.modules.event_handlers.view_invalidation import (
    MODULE_ENTITLEMENT_CATEGORY,
    MODULE_ENTITLEMENTS_SCOPE_CODE,
)
from src.core.platform.application.tenant.modules.module_catalog_context import (
    ModuleCatalogContext,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.contract.uow.provisioning.platform_provisioning_unit_of_work import (
    PlatformProvisioningUnitOfWork,
)
from src.core.platform.domain.tenant.modules.defaults import default_lifecycle_status
from src.core.platform.domain.tenant.modules.subscription import ModuleEntitlementRecord
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)


class ModuleEntitlementProvisioningHandler:
    def __init__(
        self,
        *,
        context: ModuleCatalogContext,
        user_session: Any = None,
        view_invalidation_channel: ViewInvalidationChannel | None = None,
    ) -> None:
        self._context = context
        self._user_session = user_session
        self._view_invalidation_channel = view_invalidation_channel

    def provision_organization_entitlements_using(
        self,
        uow: PlatformProvisioningUnitOfWork,
        organization_id: str,
        *,
        licensed_module_codes: Iterable[str],
        enabled_module_codes: Iterable[str] | None = None,
    ) -> list[ModuleEntitlementRecord]:
        """Seeds every module's entitlement for a newly provisioned organization inside the
        caller-owned provisioning UnitOfWork (`uow`) -- stages writes, audit and activity but
        never commits; the caller commits the organization and its entitlements together."""
        require_permission(
            self._user_session,
            "settings.manage",
            operation_label="provision organization modules",
        )
        entitlement_repo = uow.entitlements

        normalized_organization_id = str(organization_id or "").strip()
        if not normalized_organization_id:
            raise ValidationError(
                "Organization context is required for module provisioning.",
                code="ORGANIZATION_REQUIRED",
            )

        licensed_codes = self._context.normalize_selected_module_codes(licensed_module_codes)
        enabled_codes = (
            self._context.normalize_selected_module_codes(enabled_module_codes)
            if enabled_module_codes is not None
            else set(licensed_codes)
        )
        if not enabled_codes.issubset(licensed_codes):
            raise ValidationError(
                "Enabled modules must also be licensed.",
                code="MODULE_ENABLEMENT_REQUIRES_LICENSE",
            )

        requested_codes = licensed_codes | enabled_codes
        for module_code in requested_codes:
            module = self._context.require_module(module_code)
            if module.stage == "planned":
                raise ValidationError(
                    f"{module.label} is planned and cannot be provisioned yet.",
                    code="MODULE_NOT_AVAILABLE",
                )

        for module in self._context.modules:
            licensed = module.code in licensed_codes
            enabled = module.code in enabled_codes and licensed
            lifecycle_status = default_lifecycle_status(licensed)
            entitlement_repo.upsert_for_organization_in_tenant(
                normalized_organization_id,
                ModuleEntitlementRecord(
                    module_code=module.code,
                    licensed=licensed,
                    enabled=enabled,
                    lifecycle_status=lifecycle_status,
                ),
            )

        record_audit_entry(
            uow,
            operation="update",
            entity_type="organization",
            entity_id=normalized_organization_id,
            module="platform",
            category="PRIVILEGED_OPERATION",
            severity="low",
            organization_id=normalized_organization_id,
            after_data={
                "licensed_modules": sorted(licensed_codes),
                "enabled_modules": sorted(enabled_codes),
            },
            metadata={"action": "organization.modules.provision"},
            commit=False,
            fail_closed=True,
        )
        record_activity(
            uow,
            action="organization.modules.provision",
            entity_type="organization",
            entity_id=normalized_organization_id,
            module="platform",
            organization_id=normalized_organization_id,
            details={
                "licensed_modules": sorted(licensed_codes),
                "enabled_modules": sorted(enabled_codes),
            },
            commit=False,
        )
        return entitlement_repo.list_all_for_organization_in_tenant(normalized_organization_id)

    def notify_module_entitlements_stale(self, organization_id: str) -> None:
        channel = self._view_invalidation_channel
        if channel is None:
            return
        tenant_id = self._context.active_tenant_id()
        if not tenant_id:
            return
        channel.notify(
            ViewInvalidationHint(
                scope=OrganizationScope(tenant_id, organization_id),
                category=MODULE_ENTITLEMENT_CATEGORY,
                scope_code=MODULE_ENTITLEMENTS_SCOPE_CODE,
                entity_type="module_entitlement",
                entity_id=None,
            )
        )


__all__ = ["ModuleEntitlementProvisioningHandler"]
