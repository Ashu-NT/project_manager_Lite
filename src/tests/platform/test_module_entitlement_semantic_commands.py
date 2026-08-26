"""P5B-SEM/P5B-1: the generic `set_module_state(licensed=..., enabled=..., lifecycle_status=...)`
patch API is retired. Every module-entitlement mutation is now one of five explicit business
commands on `ModuleCatalogService`: `license_module`, `revoke_module_license`, `enable_module`,
`disable_module`, `transition_module_lifecycle`. This file exercises the full state machine each
command enforces -- see `platform_domain_event_implementation_plan.md`'s `## P5B-SEM` section for
the design rationale.

No DomainEvent, no ViewInvalidation, no Qt migration in this phase --
`test_module_entitlement_transaction_convergence.py::test_module_entitlement_prerequisite_does_not_add_event_vocabulary`
enforces that boundary.
"""

from __future__ import annotations

import pytest

from src.core.platform.common.exceptions import ValidationError

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _non_active_organization(services):
    organization_service = services["organization_service"]
    active = services["tenant_context_service"].get_active_organization()
    other = organization_service.create_organization(
        organization_code=_unique_code("SEM"), display_name="Semantic Command Org", is_enabled=False
    )
    assert services["tenant_context_service"].get_active_organization().id == active.id
    return active, other


# -- license_module ---------------------------------------------------------------------------


def test_license_module_grants_license_active_and_disabled(services):
    catalog = services["module_catalog_service"]
    org = services["organization_service"].get_active_organization()
    catalog.revoke_module_license(org.id, "project_management")  # start from unlicensed/inactive

    entitlement = catalog.license_module(org.id, "project_management")

    assert entitlement.licensed is True
    assert entitlement.lifecycle_status == "active"
    assert entitlement.enabled is False


def test_license_module_on_already_licensed_module_is_idempotent_and_preserves_trial(services):
    catalog = services["module_catalog_service"]
    org = services["organization_service"].get_active_organization()
    catalog.transition_module_lifecycle(org.id, "project_management", "trial")

    entitlement = catalog.license_module(org.id, "project_management")

    assert entitlement.licensed is True
    assert entitlement.lifecycle_status == "trial"  # not reset to "active"


def test_license_module_rejects_planned_module(services):
    catalog = services["module_catalog_service"]
    org = services["organization_service"].get_active_organization()

    with pytest.raises(ValidationError, match="planned") as exc:
        catalog.license_module(org.id, "hr_management")
    assert exc.value.code == "MODULE_NOT_AVAILABLE"


def test_license_module_on_non_active_organization_affects_only_that_organization(services):
    catalog = services["module_catalog_service"]
    org_a1, org_a2 = _non_active_organization(services)
    catalog.revoke_module_license(org_a2.id, "project_management")

    catalog.license_module(org_a2.id, "project_management")

    # A1 (still active throughout -- never switched) must be completely unaffected.
    assert catalog.get_entitlement("project_management").licensed is True
    with catalog._uow_factory.create(context=catalog._new_context()) as uow:
        a2_record = uow.entitlements.get_for_organization_in_tenant(org_a2.id, "project_management")
    assert a2_record is not None
    assert a2_record.licensed is True


# -- revoke_module_license ---------------------------------------------------------------------


def test_revoke_module_license_forces_unlicensed_inactive_disabled(services):
    catalog = services["module_catalog_service"]
    org = services["organization_service"].get_active_organization()

    entitlement = catalog.revoke_module_license(org.id, "project_management")

    assert entitlement.licensed is False
    assert entitlement.lifecycle_status == "inactive"
    assert entitlement.enabled is False


def test_revoke_module_license_is_idempotent_on_already_unlicensed_module(services):
    catalog = services["module_catalog_service"]
    org = services["organization_service"].get_active_organization()
    catalog.revoke_module_license(org.id, "project_management")

    entitlement = catalog.revoke_module_license(org.id, "project_management")

    assert entitlement.licensed is False
    assert entitlement.lifecycle_status == "inactive"
    assert entitlement.enabled is False


def test_revoke_module_license_on_non_active_organization_affects_only_that_organization(services):
    catalog = services["module_catalog_service"]
    org_a1, org_a2 = _non_active_organization(services)

    catalog.revoke_module_license(org_a2.id, "project_management")

    assert catalog.get_entitlement("project_management").licensed is True  # A1 unaffected


# -- enable_module / disable_module ------------------------------------------------------------


def test_enable_module_from_active_and_from_trial(services):
    catalog = services["module_catalog_service"]
    org = services["organization_service"].get_active_organization()
    catalog.disable_module(org.id, "project_management")

    active_entitlement = catalog.enable_module(org.id, "project_management")
    assert active_entitlement.enabled is True

    catalog.disable_module(org.id, "project_management")
    catalog.transition_module_lifecycle(org.id, "project_management", "trial")
    trial_entitlement = catalog.enable_module(org.id, "project_management")
    assert trial_entitlement.enabled is True
    assert trial_entitlement.lifecycle_status == "trial"


def test_enable_module_rejects_unlicensed_module(services):
    catalog = services["module_catalog_service"]
    org = services["organization_service"].get_active_organization()
    catalog.revoke_module_license(org.id, "project_management")

    with pytest.raises(ValidationError, match="licensed") as exc:
        catalog.enable_module(org.id, "project_management")
    assert exc.value.code == "MODULE_NOT_LICENSED"


def test_enable_module_rejects_suspended_and_expired(services):
    catalog = services["module_catalog_service"]
    org = services["organization_service"].get_active_organization()

    catalog.transition_module_lifecycle(org.id, "project_management", "suspended")
    with pytest.raises(ValidationError, match="suspended") as suspended_exc:
        catalog.enable_module(org.id, "project_management")
    assert suspended_exc.value.code == "MODULE_STATUS_BLOCKS_ENABLEMENT"

    catalog.transition_module_lifecycle(org.id, "project_management", "expired")
    with pytest.raises(ValidationError, match="expired") as expired_exc:
        catalog.enable_module(org.id, "project_management")
    assert expired_exc.value.code == "MODULE_STATUS_BLOCKS_ENABLEMENT"


def test_enable_module_rejects_inactive_module(services):
    """`inactive` is only reachable via `revoke_module_license` (licensed=False), so this is the
    same rejection path as `test_enable_module_rejects_unlicensed_module`, documented explicitly
    for the `inactive` lifecycle value named in P5B-SEM's own test list."""
    catalog = services["module_catalog_service"]
    org = services["organization_service"].get_active_organization()
    catalog.revoke_module_license(org.id, "project_management")
    entitlement = catalog.get_entitlement("project_management")
    assert entitlement.lifecycle_status == "inactive"

    with pytest.raises(ValidationError) as exc:
        catalog.enable_module(org.id, "project_management")
    assert exc.value.code == "MODULE_NOT_LICENSED"


def test_enable_module_is_idempotent_on_already_enabled_module(services):
    catalog = services["module_catalog_service"]
    org = services["organization_service"].get_active_organization()

    entitlement = catalog.enable_module(org.id, "project_management")

    assert entitlement.enabled is True
    assert entitlement.licensed is True
    assert entitlement.lifecycle_status == "active"


def test_disable_module_leaves_license_and_lifecycle_unchanged(services):
    catalog = services["module_catalog_service"]
    org = services["organization_service"].get_active_organization()
    catalog.transition_module_lifecycle(org.id, "project_management", "trial")

    entitlement = catalog.disable_module(org.id, "project_management")

    assert entitlement.enabled is False
    assert entitlement.licensed is True
    assert entitlement.lifecycle_status == "trial"


def test_disable_module_is_idempotent_on_already_disabled_module(services):
    catalog = services["module_catalog_service"]
    org = services["organization_service"].get_active_organization()
    catalog.disable_module(org.id, "project_management")

    entitlement = catalog.disable_module(org.id, "project_management")

    assert entitlement.enabled is False
    assert entitlement.licensed is True


def test_enable_module_on_non_active_organization_affects_only_that_organization(services):
    catalog = services["module_catalog_service"]
    org_a1, org_a2 = _non_active_organization(services)
    catalog.disable_module(org_a2.id, "project_management")

    catalog.enable_module(org_a2.id, "project_management")

    assert catalog.get_entitlement("project_management").enabled is True  # A1 unaffected


# -- transition_module_lifecycle ----------------------------------------------------------------


def test_transition_module_lifecycle_active_to_trial_and_back(services):
    catalog = services["module_catalog_service"]
    org = services["organization_service"].get_active_organization()

    trial = catalog.transition_module_lifecycle(org.id, "project_management", "trial")
    assert trial.lifecycle_status == "trial"
    assert trial.enabled is True  # runtime-access status -> enable_module is untouched

    active = catalog.transition_module_lifecycle(org.id, "project_management", "active")
    assert active.lifecycle_status == "active"
    assert active.enabled is True


def test_transition_module_lifecycle_to_suspended_and_expired_forces_disabled(services):
    catalog = services["module_catalog_service"]
    org = services["organization_service"].get_active_organization()

    suspended = catalog.transition_module_lifecycle(org.id, "project_management", "suspended")
    assert suspended.lifecycle_status == "suspended"
    assert suspended.enabled is False

    catalog.transition_module_lifecycle(org.id, "project_management", "active")
    catalog.enable_module(org.id, "project_management")
    expired = catalog.transition_module_lifecycle(org.id, "project_management", "expired")
    assert expired.lifecycle_status == "expired"
    assert expired.enabled is False


def test_transition_module_lifecycle_active_to_active_is_idempotent(services):
    catalog = services["module_catalog_service"]
    org = services["organization_service"].get_active_organization()

    entitlement = catalog.transition_module_lifecycle(org.id, "project_management", "active")

    assert entitlement.lifecycle_status == "active"
    assert entitlement.enabled is True


def test_transition_module_lifecycle_rejects_inactive_as_explicit_target(services):
    catalog = services["module_catalog_service"]
    org = services["organization_service"].get_active_organization()

    with pytest.raises(ValidationError) as exc:
        catalog.transition_module_lifecycle(org.id, "project_management", "inactive")
    assert exc.value.code == "MODULE_LIFECYCLE_NOT_SELECTABLE"


def test_transition_module_lifecycle_rejects_unlicensed_module(services):
    catalog = services["module_catalog_service"]
    org = services["organization_service"].get_active_organization()
    catalog.revoke_module_license(org.id, "project_management")

    with pytest.raises(ValidationError, match="licensed") as exc:
        catalog.transition_module_lifecycle(org.id, "project_management", "trial")
    assert exc.value.code == "MODULE_NOT_LICENSED"


def test_transition_module_lifecycle_rejects_planned_module(services):
    catalog = services["module_catalog_service"]
    org = services["organization_service"].get_active_organization()

    with pytest.raises(ValidationError, match="planned") as exc:
        catalog.transition_module_lifecycle(org.id, "hr_management", "trial")
    assert exc.value.code == "MODULE_NOT_AVAILABLE"


def test_transition_module_lifecycle_on_non_active_organization_affects_only_that_organization(services):
    catalog = services["module_catalog_service"]
    org_a1, org_a2 = _non_active_organization(services)

    catalog.transition_module_lifecycle(org_a2.id, "project_management", "suspended")

    assert catalog.get_entitlement("project_management").lifecycle_status == "active"  # A1 unaffected
