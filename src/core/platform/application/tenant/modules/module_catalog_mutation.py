from __future__ import annotations

from typing import Iterable

from src.core.shared.audit import record_audit_entry
from src.core.platform.common.exceptions import ValidationError
from src.core.shared.events.domain_events import domain_events
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.domain.tenant.modules.defaults import (
    MODULE_LIFECYCLE_INACTIVE,
    MODULE_RUNTIME_ACCESS_STATUSES,
    default_lifecycle_status,
    normalize_lifecycle_status,
)
from src.core.platform.domain.tenant.modules.module_entitlement import ModuleEntitlement
from src.core.platform.domain.tenant.modules.subscription import ModuleEntitlementRecord


class ModuleCatalogMutationMixin:
    def set_module_state(
        self,
        organization_id: str,
        module_code: str,
        *,
        licensed: bool | None = None,
        enabled: bool | None = None,
        lifecycle_status: str | None = None,
    ) -> ModuleEntitlement:
        """License/enable/disable/lifecycle-transition a module for `organization_id` --
        explicit (P5B prerequisite), never derived ambiently from the active-session
        organization. `organization_id` may be ANY organization within the caller's own
        authenticated tenant, not only the currently active one (structurally impossible before
        this change -- see the P5B report). Callers that mean "whichever organization is
        currently active" (e.g. `PlatformRuntimeApplicationService.set_module_state`) must
        resolve that explicitly themselves and pass it in -- this method never reads
        `UserSessionContext`/`TenantContextService` to guess."""
        require_permission(
            self._user_session,
            "settings.manage",
            operation_label="manage module entitlements",
        )
        normalized_organization_id = str(organization_id or "").strip()
        if not normalized_organization_id:
            raise ValidationError(
                "Organization context is required to manage module entitlements.",
                code="ORGANIZATION_REQUIRED",
            )
        if self._uow_factory is None:
            raise RuntimeError("Module entitlement UnitOfWork factory is not configured.")

        with self._uow_factory.create(context=self._new_context()) as uow:
            entitlement = self._set_module_state_using(
                uow.entitlements,
                uow,
                organization_id=normalized_organization_id,
                module_code=module_code,
                licensed=licensed,
                enabled=enabled,
                lifecycle_status=lifecycle_status,
            )
            uow.commit()
        domain_events.modules_changed.emit(module_code)
        return entitlement

    def _set_module_state_using(
        self,
        entitlement_repo,
        uow,
        *,
        organization_id: str,
        module_code: str,
        licensed: bool | None,
        enabled: bool | None,
        lifecycle_status: str | None,
    ) -> ModuleEntitlement:
        """The module-entitlement state-transition business operation, transaction-agnostic:
        does not open or commit a transaction itself -- that remains the caller's
        responsibility. `uow` is duck-typed against `_enterprise_audit_service`
        (`record_audit_entry`'s existing contract), never a concrete UoW class import."""
        module = self._require_module(module_code)
        current_record = entitlement_repo.get_for_organization_in_tenant(organization_id, module.code)
        current = self._build_entitlement(
            module, {current_record.module_code: current_record} if current_record is not None else {}
        )

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

        record = ModuleEntitlementRecord(
            module_code=module.code,
            licensed=next_licensed,
            enabled=next_enabled,
            lifecycle_status=next_status,
        )
        entitlement_repo.upsert_for_organization_in_tenant(organization_id, record)
        # P5B prerequisite fix: staged in the SAME transaction as the entitlement write (ADR-003)
        # -- the previous implementation recorded this audit entry *after* the business mutation's
        # own commit, via a second, independent commit (never atomic). Fixing the ordering is a
        # necessary consequence of the fresh UoW's commit-then-close lifecycle, not opportunistic
        # cleanup: calling `record_audit_entry` after `uow.commit()` would hit an already-closed
        # Session.
        record_audit_entry(
            uow,
            operation="update",
            entity_type="module_entitlement",
            entity_id=module.code,
            module="platform",
            severity="low",
            metadata={
                "action": "module.entitlement.update",
                "organization_id": organization_id,
                "module_code": module.code,
                "licensed": str(next_licensed),
                "enabled": str(next_enabled),
                "lifecycle_status": next_status,
                "stage": module.stage,
            },
            commit=False,
        )
        return self._build_entitlement(module, {record.module_code: record})

    def provision_organization_entitlements(
        self,
        organization_id: str,
        *,
        licensed_module_codes: Iterable[str],
        enabled_module_codes: Iterable[str] | None = None,
        commit: bool = True,
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

        # Tenant-administration/provisioning write: this seeds a *specified*
        # organization's entitlements, which is explicitly allowed to target an
        # organization other than the currently active one (e.g. a
        # newly-created, not-yet-active organization) as long as it belongs to
        # the authenticated tenant. Ordinary runtime entitlement changes
        # (set_module_state, above) keep using the active-organization-only
        # upsert_for_organization.
        for module in self._modules:
            licensed = module.code in licensed_codes
            enabled = module.code in enabled_codes and licensed
            lifecycle_status = default_lifecycle_status(licensed)
            self._entitlement_repo.upsert_for_organization_in_tenant(
                normalized_organization_id,
                ModuleEntitlementRecord(
                    module_code=module.code,
                    licensed=licensed,
                    enabled=enabled,
                    lifecycle_status=lifecycle_status,
                ),
            )

        # Audit is staged in the same transaction as the entitlement writes
        # (ADR-003: business mutation and audit intent commit atomically for
        # platform provisioning) — never a second, separate commit.
        record_audit_entry(
            self,
            operation="update",
            entity_type="organization",
            entity_id=normalized_organization_id,
            module="platform",
            severity="low",
            metadata={
                "action": "organization.modules.provision",
                "organization_id": normalized_organization_id,
                "licensed_modules": ",".join(sorted(licensed_codes)),
                "enabled_modules": ",".join(sorted(enabled_codes)),
            },
            commit=False,
            fail_closed=True,
        )
        if self._session is not None:
            if commit:
                self._session.commit()
            else:
                self._session.flush()
        if commit:
            active_organization = self._current_organization()
            if active_organization is not None and active_organization.id == normalized_organization_id:
                domain_events.modules_changed.emit(f"organization:{normalized_organization_id}")
        return self._entitlement_repo.list_all_for_organization_in_tenant(normalized_organization_id)


__all__ = ["ModuleCatalogMutationMixin"]
