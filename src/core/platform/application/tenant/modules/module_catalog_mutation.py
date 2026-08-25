from __future__ import annotations

from typing import Callable, Iterable

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
from src.core.platform.domain.tenant.modules.events import (
    ModuleDisabled,
    ModuleEnabled,
    ModuleLicenseRevoked,
    ModuleLicensed,
    ModuleLifecycleTransitioned,
)
from src.core.platform.domain.tenant.modules.module_definition import EnterpriseModule
from src.core.platform.domain.tenant.modules.module_entitlement import ModuleEntitlement
from src.core.platform.domain.tenant.modules.subscription import ModuleEntitlementRecord

# P5B-SEM: the only lifecycle_status values a caller may explicitly select. `inactive` is
# deliberately excluded -- it is reached only as an automatic consequence of
# `revoke_module_license`, never as a direct lifecycle command target (matches the settings
# workspace's own lifecycle dropdown, which never offers "Inactive").
_USER_SELECTABLE_LIFECYCLE_STATUSES = frozenset({"active", "trial", "suspended", "expired"})

_Transition = Callable[[EnterpriseModule, ModuleEntitlement], tuple[bool, bool, str]]
# (tenant_id, organization_id, module_code, current-before-transition, occurred_at) -> DomainEvent.
# Called only when the transition actually changed persisted state (P5B-2: no event on a no-op).
_EventFactory = Callable[..., object]


class ModuleCatalogMutationMixin:
    """P5B-SEM: the generic `set_module_state(licensed=..., enabled=..., lifecycle_status=...)`
    patch API is retired. Every real caller (the three settings-workspace presenter actions)
    already expressed exactly one business intention per call -- licensing terminology, dedicated
    business commands below make that intention explicit and let each command enforce its own
    invariants, instead of a shared method inferring what changed from an arbitrary field
    combination."""

    def license_module(self, organization_id: str, module_code: str) -> ModuleEntitlement:
        """LICENSE_MODULE: grants a license. Idempotent -- licensing an already-licensed module
        is a business no-op that preserves its current `enabled`/`lifecycle_status` (never resets
        an active trial back to `active`) and records no `ModuleLicensed` event."""
        return self._run_module_transition(
            organization_id,
            module_code,
            transition=self._license_module_transition,
            audit_action="module.entitlement.license_granted",
            event_factory=self._license_module_event,
        )

    def revoke_module_license(self, organization_id: str, module_code: str) -> ModuleEntitlement:
        """REVOKE_MODULE_LICENSE: one compound business fact. Forcing `enabled=False` and
        `lifecycle_status=inactive` is an implementation consequence of revocation, not a
        separate disablement/lifecycle business action -- exactly one `ModuleLicenseRevoked`,
        never also `ModuleDisabled`/`ModuleLifecycleTransitioned`."""
        return self._run_module_transition(
            organization_id,
            module_code,
            transition=self._revoke_module_license_transition,
            audit_action="module.entitlement.license_revoked",
            event_factory=self._revoke_module_license_event,
        )

    def enable_module(self, organization_id: str, module_code: str) -> ModuleEntitlement:
        """ENABLE_MODULE: pure runtime activation. Requires an existing license and a
        runtime-access lifecycle status (`active`/`trial`) -- never changes either itself."""
        return self._run_module_transition(
            organization_id,
            module_code,
            transition=self._enable_module_transition,
            audit_action="module.entitlement.enabled",
            event_factory=self._enable_module_event,
        )

    def disable_module(self, organization_id: str, module_code: str) -> ModuleEntitlement:
        """DISABLE_MODULE: pure runtime deactivation. Never revokes the license or changes
        lifecycle status -- kept distinct from `revoke_module_license`."""
        return self._run_module_transition(
            organization_id,
            module_code,
            transition=self._disable_module_transition,
            audit_action="module.entitlement.disabled",
            event_factory=self._disable_module_event,
        )

    def transition_module_lifecycle(
        self,
        organization_id: str,
        module_code: str,
        lifecycle_status: str,
    ) -> ModuleEntitlement:
        """TRANSITION_MODULE_LIFECYCLE: explicit user-selected lifecycle move among
        active/trial/suspended/expired (`inactive` is never a valid target here -- it is only
        reached via `revoke_module_license`). Moving into suspended/expired forces
        `enabled=False` as an implementation consequence of that one transition (recorded as
        exactly one `ModuleLifecycleTransitioned`, never also `ModuleDisabled`); moving into
        active/trial never silently re-enables the module -- enablement remains its own command."""
        normalized_status = normalize_lifecycle_status(lifecycle_status)
        if normalized_status not in _USER_SELECTABLE_LIFECYCLE_STATUSES:
            raise ValidationError(
                "Lifecycle status must be one of: active, trial, suspended, expired.",
                code="MODULE_LIFECYCLE_NOT_SELECTABLE",
            )
        return self._run_module_transition(
            organization_id,
            module_code,
            transition=lambda module, current: self._transition_module_lifecycle_transition(
                module, current, normalized_status
            ),
            audit_action="module.entitlement.lifecycle_transitioned",
            audit_extra={"lifecycle_status": normalized_status},
            event_factory=self._transition_module_lifecycle_event,
        )

    # -- shared transaction/audit plumbing (transaction-owning; internal only) -----------------

    def _run_module_transition(
        self,
        organization_id: str,
        module_code: str,
        *,
        transition: _Transition,
        audit_action: str,
        event_factory: _EventFactory,
        audit_extra: dict | None = None,
    ) -> ModuleEntitlement:
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
            entitlement = self._apply_module_transition_using(
                uow.entitlements,
                uow,
                organization_id=normalized_organization_id,
                module_code=module_code,
                transition=transition,
                audit_action=audit_action,
                audit_extra=audit_extra,
                event_factory=event_factory,
            )
            uow.commit()
        domain_events.modules_changed.emit(module_code)
        return entitlement

    def _apply_module_transition_using(
        self,
        entitlement_repo,
        uow,
        *,
        organization_id: str,
        module_code: str,
        transition: _Transition,
        audit_action: str,
        audit_extra: dict | None,
        event_factory: _EventFactory,
    ) -> ModuleEntitlement:
        """Transaction-agnostic: does not open or commit a transaction itself -- that remains the
        caller's responsibility. `uow` is duck-typed against `_enterprise_audit_service`
        (`record_audit_entry`'s existing contract) plus the canonical `record_event` (P5B-2),
        never a concrete UoW class import. Always persists (even a value-for-value no-op call) --
        this is what normalizes a legacy storage code (e.g. `payroll` -> `hr_management`) onto any
        real mutation, exactly as the retired generic `set_module_state` did -- but records a
        DomainEvent only when the transition actually changed persisted state (P5B-2: no event on
        a no-op), using authoritative before/after state from the transition function itself, not
        a guess from caller input."""
        module = self._require_module(module_code)
        current_record = entitlement_repo.get_for_organization_in_tenant(organization_id, module.code)
        current = self._build_entitlement(
            module, {current_record.module_code: current_record} if current_record is not None else {}
        )

        next_licensed, next_enabled, next_status = transition(module, current)
        changed = (next_licensed, next_enabled, next_status) != (
            current.licensed,
            current.enabled,
            current.lifecycle_status,
        )

        record = ModuleEntitlementRecord(
            module_code=module.code,
            licensed=next_licensed,
            enabled=next_enabled,
            lifecycle_status=next_status,
        )
        entitlement_repo.upsert_for_organization_in_tenant(organization_id, record)
        metadata = {
            "action": audit_action,
            "organization_id": organization_id,
            "module_code": module.code,
            "licensed": str(next_licensed),
            "enabled": str(next_enabled),
            "lifecycle_status": next_status,
            "stage": module.stage,
        }
        if audit_extra:
            metadata.update(audit_extra)
        # P5B prerequisite fix (preserved): staged in the SAME transaction as the entitlement
        # write (ADR-003) -- calling `record_audit_entry` after `uow.commit()` would hit an
        # already-closed Session.
        record_audit_entry(
            uow,
            operation="update",
            entity_type="module_entitlement",
            entity_id=module.code,
            module="platform",
            severity="low",
            metadata=metadata,
            commit=False,
        )
        if changed:
            if self._clock is None:
                raise RuntimeError("Module entitlement Clock is not configured.")
            # Recorded before `uow.commit()` (P5B-2, ADR-005 Section 6's application-authored
            # escape hatch -- ModuleEntitlement has no aggregate transition methods to record
            # itself on) so it participates in the canonical UoW event lifecycle: transactional
            # dispatch, then only-on-successful-commit post-commit publication. `tenant_id` comes
            # from the caller's own authenticated tenant (never the active organization).
            uow.record_event(
                event_factory(
                    tenant_id=self._active_tenant_id(),
                    organization_id=organization_id,
                    module_code=module.code,
                    current=current,
                    next_status=next_status,
                    occurred_at=self._clock.now(),
                )
            )
        return self._build_entitlement(module, {record.module_code: record})

    @staticmethod
    def _license_module_event(*, tenant_id, organization_id, module_code, current, next_status, occurred_at):
        return ModuleLicensed(
            tenant_id=tenant_id,
            organization_id=organization_id,
            module_code=module_code,
            occurred_at=occurred_at,
        )

    @staticmethod
    def _revoke_module_license_event(*, tenant_id, organization_id, module_code, current, next_status, occurred_at):
        return ModuleLicenseRevoked(
            tenant_id=tenant_id,
            organization_id=organization_id,
            module_code=module_code,
            occurred_at=occurred_at,
        )

    @staticmethod
    def _enable_module_event(*, tenant_id, organization_id, module_code, current, next_status, occurred_at):
        return ModuleEnabled(
            tenant_id=tenant_id,
            organization_id=organization_id,
            module_code=module_code,
            occurred_at=occurred_at,
        )

    @staticmethod
    def _disable_module_event(*, tenant_id, organization_id, module_code, current, next_status, occurred_at):
        return ModuleDisabled(
            tenant_id=tenant_id,
            organization_id=organization_id,
            module_code=module_code,
            occurred_at=occurred_at,
        )

    @staticmethod
    def _transition_module_lifecycle_event(*, tenant_id, organization_id, module_code, current, next_status, occurred_at):
        return ModuleLifecycleTransitioned(
            tenant_id=tenant_id,
            organization_id=organization_id,
            module_code=module_code,
            previous_lifecycle_status=current.lifecycle_status,
            lifecycle_status=next_status,
            occurred_at=occurred_at,
        )

    # -- individual business transitions (pure -- no I/O, no transaction) ----------------------

    @staticmethod
    def _license_module_transition(
        module: EnterpriseModule, current: ModuleEntitlement
    ) -> tuple[bool, bool, str]:
        if module.stage == "planned":
            raise ValidationError(
                f"{module.label} is planned and cannot be licensed yet.",
                code="MODULE_NOT_AVAILABLE",
            )
        if current.licensed:
            return current.licensed, current.enabled, current.lifecycle_status
        return True, False, default_lifecycle_status(True)

    @staticmethod
    def _revoke_module_license_transition(
        _module: EnterpriseModule, _current: ModuleEntitlement
    ) -> tuple[bool, bool, str]:
        return False, False, MODULE_LIFECYCLE_INACTIVE

    @staticmethod
    def _enable_module_transition(
        module: EnterpriseModule, current: ModuleEntitlement
    ) -> tuple[bool, bool, str]:
        if not current.licensed:
            raise ValidationError(
                "A module must be licensed before it can be enabled.",
                code="MODULE_NOT_LICENSED",
            )
        if current.lifecycle_status not in MODULE_RUNTIME_ACCESS_STATUSES:
            raise ValidationError(
                f"{module.label} is {current.lifecycle_label.lower()}. "
                "Change its lifecycle status before enabling it.",
                code="MODULE_STATUS_BLOCKS_ENABLEMENT",
            )
        return current.licensed, True, current.lifecycle_status

    @staticmethod
    def _disable_module_transition(
        _module: EnterpriseModule, current: ModuleEntitlement
    ) -> tuple[bool, bool, str]:
        return current.licensed, False, current.lifecycle_status

    @staticmethod
    def _transition_module_lifecycle_transition(
        module: EnterpriseModule, current: ModuleEntitlement, target_status: str
    ) -> tuple[bool, bool, str]:
        if module.stage == "planned":
            raise ValidationError(
                f"{module.label} is planned and does not have an active lifecycle yet.",
                code="MODULE_NOT_AVAILABLE",
            )
        if not current.licensed:
            raise ValidationError(
                f"{module.label} must be licensed before its lifecycle can change.",
                code="MODULE_NOT_LICENSED",
            )
        next_enabled = current.enabled if target_status in MODULE_RUNTIME_ACCESS_STATUSES else False
        return True, next_enabled, target_status

    def provision_organization_entitlements(
        self,
        organization_id: str,
        *,
        licensed_module_codes: Iterable[str],
        enabled_module_codes: Iterable[str] | None = None,
        commit: bool = True,
    ) -> list[ModuleEntitlementRecord]:
        # P5B-SEM: this remains a separate bootstrap/materialization operation, deliberately not
        # decomposed into per-module `license_module` calls -- provisioning writes rows (most
        # unlicensed) for every catalog module on a brand-new organization, which is not the same
        # business fact as an administrator licensing one module. See the P5B-SEM design report.
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
        # (the semantic commands, above) keep using the active-organization-only
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
