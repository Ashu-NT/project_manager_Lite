"""Pure module-entitlement business transitions and their domain-event factories.

Each transition maps (module, current entitlement) to the next (licensed, enabled,
lifecycle_status) triple or raises a ValidationError; no I/O, no transaction."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.domain.tenant.modules.defaults import (
    MODULE_LIFECYCLE_INACTIVE,
    MODULE_RUNTIME_ACCESS_STATUSES,
    default_lifecycle_status,
)
from src.core.platform.domain.tenant.modules.events import (
    ModuleDisabled,
    ModuleEnabled,
    ModuleLicensed,
    ModuleLicenseRevoked,
    ModuleLifecycleTransitioned,
)
from src.core.platform.domain.tenant.modules.module_definition import EnterpriseModule
from src.core.platform.domain.tenant.modules.module_entitlement import ModuleEntitlement
from src.core.shared.events.domain_event import DomainEvent

USER_SELECTABLE_LIFECYCLE_STATUSES = frozenset(
    {"active", "trial", "suspended", "expired"}
)

Transition = Callable[[EnterpriseModule, ModuleEntitlement], tuple[bool, bool, str]]
EventFactory = Callable[..., DomainEvent]


def license_module_event(
    *,
    tenant_id: str,
    organization_id: str,
    module_code: str,
    current: ModuleEntitlement | None = None,
    next_status: str | None = None,
    occurred_at: datetime,
) -> DomainEvent:
    return ModuleLicensed(
        tenant_id=tenant_id,
        organization_id=organization_id,
        module_code=module_code,
        occurred_at=occurred_at,
    )


def revoke_module_license_event(
    *,
    tenant_id: str,
    organization_id: str,
    module_code: str,
    current: ModuleEntitlement | None = None,
    next_status: str | None = None,
    occurred_at: datetime,
) -> DomainEvent:
    return ModuleLicenseRevoked(
        tenant_id=tenant_id,
        organization_id=organization_id,
        module_code=module_code,
        occurred_at=occurred_at,
    )


def enable_module_event(
    *,
    tenant_id: str,
    organization_id: str,
    module_code: str,
    current: ModuleEntitlement | None = None,
    next_status: str | None = None,
    occurred_at: datetime,
) -> DomainEvent:
    return ModuleEnabled(
        tenant_id=tenant_id,
        organization_id=organization_id,
        module_code=module_code,
        occurred_at=occurred_at,
    )


def disable_module_event(
    *,
    tenant_id: str,
    organization_id: str,
    module_code: str,
    current: ModuleEntitlement | None = None,
    next_status: str | None = None,
    occurred_at: datetime,
) -> DomainEvent:
    return ModuleDisabled(
        tenant_id=tenant_id,
        organization_id=organization_id,
        module_code=module_code,
        occurred_at=occurred_at,
    )


def transition_module_lifecycle_event(
    *,
    tenant_id: str,
    organization_id: str,
    module_code: str,
    current: ModuleEntitlement,
    next_status: str,
    occurred_at: datetime,
) -> DomainEvent:
    return ModuleLifecycleTransitioned(
        tenant_id=tenant_id,
        organization_id=organization_id,
        module_code=module_code,
        previous_lifecycle_status=current.lifecycle_status,
        lifecycle_status=next_status,
        occurred_at=occurred_at,
    )


def license_module_transition(
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


def revoke_module_license_transition(
    _module: EnterpriseModule, _current: ModuleEntitlement
) -> tuple[bool, bool, str]:
    return False, False, MODULE_LIFECYCLE_INACTIVE


def enable_module_transition(
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


def disable_module_transition(
    _module: EnterpriseModule, current: ModuleEntitlement
) -> tuple[bool, bool, str]:
    return current.licensed, False, current.lifecycle_status


def transition_module_lifecycle_transition(
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
    next_enabled = (
        current.enabled if target_status in MODULE_RUNTIME_ACCESS_STATUSES else False
    )
    return True, next_enabled, target_status


__all__ = [
    "USER_SELECTABLE_LIFECYCLE_STATUSES",
    "EventFactory",
    "Transition",
    "disable_module_event",
    "disable_module_transition",
    "enable_module_event",
    "enable_module_transition",
    "license_module_event",
    "license_module_transition",
    "revoke_module_license_event",
    "revoke_module_license_transition",
    "transition_module_lifecycle_event",
    "transition_module_lifecycle_transition",
]
