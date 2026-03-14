from __future__ import annotations

from core.platform.audit.helpers import record_audit
from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import NotFoundError, ValidationError
from core.platform.notifications.domain_events import domain_events
from core.platform.modules.defaults import (
    MODULE_LIFECYCLE_INACTIVE,
    MODULE_RUNTIME_ACCESS_STATUSES,
    default_lifecycle_status,
    normalize_lifecycle_status,
)
from core.platform.modules.repository import ModuleEntitlementRecord


class ModuleCatalogMutationMixin:
    def set_module_state(
        self,
        module_code: str,
        *,
        licensed: bool | None = None,
        enabled: bool | None = None,
        lifecycle_status: str | None = None,
    ):
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
        next_status = (
            current.lifecycle_status
            if lifecycle_status is None
            else normalize_lifecycle_status(lifecycle_status)
        )

        if lifecycle_status is not None and next_status != MODULE_LIFECYCLE_INACTIVE and not next_licensed:
            raise ValidationError(
                "A module must be licensed before its lifecycle can be changed.",
                code="MODULE_NOT_LICENSED",
            )
        if enabled is True and not next_licensed:
            raise ValidationError(
                "A module must be licensed before it can be enabled.",
                code="MODULE_NOT_LICENSED",
            )

        if module.stage == "planned" and (
            next_licensed
            or next_enabled
            or next_status != MODULE_LIFECYCLE_INACTIVE
        ):
            raise ValidationError(
                f"{module.label} is planned and cannot be licensed, enabled, or activated yet.",
                code="MODULE_NOT_AVAILABLE",
            )
        if not next_licensed:
            next_status = MODULE_LIFECYCLE_INACTIVE
            next_enabled = False
        else:
            if next_status == MODULE_LIFECYCLE_INACTIVE:
                next_status = default_lifecycle_status(True)
            if next_status not in MODULE_RUNTIME_ACCESS_STATUSES:
                if enabled is True:
                    raise ValidationError(
                        "Only active or trial modules can be enabled.",
                        code="MODULE_STATUS_BLOCKS_ENABLEMENT",
                    )
                next_enabled = False

        self._persist_state(
            ModuleEntitlementRecord(
                module_code=module.code,
                licensed=next_licensed,
                enabled=next_enabled,
                lifecycle_status=next_status,
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
                "lifecycle_status": next_status,
                "stage": module.stage,
            },
        )
        domain_events.modules_changed.emit(module.code)
        entitlement = self.get_entitlement(module.code)
        if entitlement is None:
            raise NotFoundError("Module entitlement not found after update.", code="MODULE_NOT_FOUND")
        return entitlement

    def provision_organization_entitlements(
        self,
        organization_id: str,
        *,
        licensed_module_codes,
        enabled_module_codes=None,
    ) -> list[ModuleEntitlementRecord]:
        require_permission(
            self._user_session,
            "settings.manage",
            operation_label="provision organization modules",
        )
        if self._entitlement_repo is None:
            raise RuntimeError("Module entitlement repository is not configured.")

        normalized_organization_id = str(organization_id or "").strip()
        if not normalized_organization_id:
            raise ValidationError(
                "Organization context is required for module provisioning.",
                code="ORGANIZATION_REQUIRED",
            )

        licensed_codes = self._normalize_selected_module_codes(licensed_module_codes)
        enabled_codes = (
            self._normalize_selected_module_codes(enabled_module_codes)
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
            module = self._require_module(module_code)
            if module.stage == "planned":
                raise ValidationError(
                    f"{module.label} is planned and cannot be provisioned yet.",
                    code="MODULE_NOT_AVAILABLE",
                )

        for module in self._modules:
            licensed = module.code in licensed_codes
            enabled = module.code in enabled_codes and licensed
            lifecycle_status = default_lifecycle_status(licensed)
            self._entitlement_repo.upsert_for_organization(
                normalized_organization_id,
                ModuleEntitlementRecord(
                    module_code=module.code,
                    licensed=licensed,
                    enabled=enabled,
                    lifecycle_status=lifecycle_status,
                ),
            )

        if self._session is not None:
            self._session.commit()

        record_audit(
            self,
            action="organization.modules.provision",
            entity_type="organization",
            entity_id=normalized_organization_id,
            details={
                "organization_id": normalized_organization_id,
                "licensed_modules": ",".join(sorted(licensed_codes)),
                "enabled_modules": ",".join(sorted(enabled_codes)),
            },
        )
        active_organization = self._current_organization()
        if active_organization is not None and active_organization.id == normalized_organization_id:
            domain_events.modules_changed.emit(f"organization:{normalized_organization_id}")
        return self._entitlement_repo.list_all_for_organization(normalized_organization_id)


__all__ = ["ModuleCatalogMutationMixin"]
