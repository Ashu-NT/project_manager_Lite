"""Governed module-entitlement commands.

`ModuleEntitlementCommandHandler` owns the five semantic entitlement commands
(license/revoke/enable/disable/lifecycle transition) and the bulk license action. Each command
keeps its permission check, transition, audit, activity and domain event inside ONE
UnitOfWork/commit boundary (`_run_module_transition` / `_apply_module_transition_using`); the
pure transitions and event factories live in `module_entitlement_transitions`."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.modules.module_catalog_context import (
    ModuleCatalogContext,
)
from src.core.platform.application.tenant.modules.module_entitlement_transitions import (
    USER_SELECTABLE_LIFECYCLE_STATUSES,
    EventFactory,
    Transition,
    disable_module_event,
    disable_module_transition,
    enable_module_event,
    enable_module_transition,
    license_module_event,
    license_module_transition,
    revoke_module_license_event,
    revoke_module_license_transition,
    transition_module_lifecycle_event,
    transition_module_lifecycle_transition,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.repositories.tenant.modules.contracts import (
    ModuleEntitlementRepository,
)
from src.core.platform.contract.uow.tenancy.module_entitlement_unit_of_work import (
    ModuleEntitlementUnitOfWork,
    ModuleEntitlementUnitOfWorkFactory,
)
from src.core.platform.domain.tenant.modules.defaults import normalize_lifecycle_status
from src.core.platform.domain.tenant.modules.module_entitlement import ModuleEntitlement
from src.core.platform.domain.tenant.modules.subscription import ModuleEntitlementRecord
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.time.clock import Clock


class ModuleEntitlementCommandHandler:
    def __init__(
        self,
        *,
        context: ModuleCatalogContext,
        user_session: Any = None,
        uow_factory: ModuleEntitlementUnitOfWorkFactory | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._context = context
        self._user_session = user_session
        self._uow_factory = uow_factory
        self._clock = clock

    def _new_context(self, *, causation_id: str | None = None) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)

    def license_module(self, organization_id: str, module_code: str) -> ModuleEntitlement:
        """LICENSE_MODULE: grants a license. Idempotent -- licensing an already-licensed module
        is a business no-op that preserves its current `enabled`/`lifecycle_status` (never resets
        an active trial back to `active`) and records no `ModuleLicensed` event."""
        return self._run_module_transition(
            organization_id,
            module_code,
            transition=license_module_transition,
            audit_action="module.entitlement.license_granted",
            event_factory=license_module_event,
        )

    def revoke_module_license(self, organization_id: str, module_code: str) -> ModuleEntitlement:
        return self._run_module_transition(
            organization_id,
            module_code,
            transition=revoke_module_license_transition,
            audit_action="module.entitlement.license_revoked",
            event_factory=revoke_module_license_event,
        )

    def bulk_set_module_license(
        self, organization_module_pairs: Iterable[tuple[str, str]], *, licensed: bool
    ) -> list[ModuleEntitlement]:
        """Grants or revokes a module license across many (organization_id,
        module_code) pairs -- e.g. Organizations' bulk "Assign Modules" action
        applying N modules to M selected organizations. One UnitOfWork/commit
        for every pair instead of one per pair, same reasoning as
        OrganizationLifecycleCommandHandler.bulk_activate_organizations()."""
        require_permission(
            self._user_session,
            "settings.manage",
            operation_label="manage module entitlements",
        )
        if self._uow_factory is None:
            raise RuntimeError("Module entitlement UnitOfWork factory is not configured.")
        transition = license_module_transition if licensed else revoke_module_license_transition
        audit_action = (
            "module.entitlement.license_granted" if licensed else "module.entitlement.license_revoked"
        )
        event_factory = license_module_event if licensed else revoke_module_license_event
        results: list[ModuleEntitlement] = []
        with self._uow_factory.create(context=self._new_context()) as uow:
            for organization_id, module_code in organization_module_pairs:
                normalized_organization_id = str(organization_id or "").strip()
                if not normalized_organization_id:
                    raise ValidationError(
                        "Organization context is required to manage module entitlements.",
                        code="ORGANIZATION_REQUIRED",
                    )
                results.append(
                    self._apply_module_transition_using(
                        uow.entitlements,
                        uow,
                        organization_id=normalized_organization_id,
                        module_code=module_code,
                        transition=transition,
                        audit_action=audit_action,
                        audit_extra=None,
                        event_factory=event_factory,
                    )
                )
            uow.commit()
        return results

    def enable_module(self, organization_id: str, module_code: str) -> ModuleEntitlement:
        """ENABLE_MODULE: pure runtime activation. Requires an existing license and a
        runtime-access lifecycle status (`active`/`trial`) -- never changes either itself."""
        return self._run_module_transition(
            organization_id,
            module_code,
            transition=enable_module_transition,
            audit_action="module.entitlement.enabled",
            event_factory=enable_module_event,
        )

    def disable_module(self, organization_id: str, module_code: str) -> ModuleEntitlement:
        """DISABLE_MODULE: pure runtime deactivation. Never revokes the license or changes
        lifecycle status -- kept distinct from `revoke_module_license`."""
        return self._run_module_transition(
            organization_id,
            module_code,
            transition=disable_module_transition,
            audit_action="module.entitlement.disabled",
            event_factory=disable_module_event,
        )

    def transition_module_lifecycle(
        self,
        organization_id: str,
        module_code: str,
        lifecycle_status: str,
    ) -> ModuleEntitlement:
        normalized_status = normalize_lifecycle_status(lifecycle_status)
        if normalized_status not in USER_SELECTABLE_LIFECYCLE_STATUSES:
            raise ValidationError(
                "Lifecycle status must be one of: active, trial, suspended, expired.",
                code="MODULE_LIFECYCLE_NOT_SELECTABLE",
            )
        return self._run_module_transition(
            organization_id,
            module_code,
            transition=lambda module, current: transition_module_lifecycle_transition(
                module, current, normalized_status
            ),
            audit_action="module.entitlement.lifecycle_transitioned",
            audit_extra={"lifecycle_status": normalized_status},
            event_factory=transition_module_lifecycle_event,
        )

    # -- shared transaction/audit plumbing (transaction-owning; internal only) -----------------

    def _run_module_transition(
        self,
        organization_id: str,
        module_code: str,
        *,
        transition: Transition,
        audit_action: str,
        event_factory: EventFactory,
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
        return entitlement

    def _apply_module_transition_using(
        self,
        entitlement_repo: ModuleEntitlementRepository,
        uow: ModuleEntitlementUnitOfWork,
        *,
        organization_id: str,
        module_code: str,
        transition: Transition,
        audit_action: str,
        audit_extra: dict | None,
        event_factory: EventFactory,
    ) -> ModuleEntitlement:
        module = self._context.require_module(module_code)
        current_record = entitlement_repo.get_for_organization_in_tenant(organization_id, module.code)
        current = self._context.build_entitlement(
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
        # Staged before uow.commit() -- calling record_audit_entry after commit would hit an
        # already-closed Session.
        record_audit_entry(
            uow,
            operation="update",
            entity_type="module_entitlement",
            entity_id=module.code,
            module="platform",
            category="PRIVILEGED_OPERATION",
            severity="low",
            organization_id=organization_id,
            changed_fields={
                "licensed": {"before": current.licensed, "after": next_licensed},
                "enabled": {"before": current.enabled, "after": next_enabled},
                "lifecycle_status": {"before": current.lifecycle_status, "after": next_status},
            },
            metadata=metadata,
            commit=False,
        )
        record_activity(
            uow,
            action=audit_action,
            entity_type="module_entitlement",
            entity_id=module.code,
            module="platform",
            organization_id=organization_id,
            details=metadata,
            commit=False,
        )
        if changed:
            if self._clock is None:
                raise RuntimeError("Module entitlement Clock is not configured.")
            uow.record_event(
                event_factory(
                    tenant_id=self._context.active_tenant_id(),
                    organization_id=organization_id,
                    module_code=module.code,
                    current=current,
                    next_status=next_status,
                    occurred_at=self._clock.now(),
                )
            )
        return self._context.build_entitlement(module, {record.module_code: record})


__all__ = ["ModuleEntitlementCommandHandler"]
