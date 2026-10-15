"""`OrganizationProvisioningCommandHandler.provision_organization` runs inside a fresh-session
`PlatformProvisioningUnitOfWork`, mirroring `test_organization_service_unit_of_work_cutover.py`/
`test_approval_commands_unit_of_work_cutover.py`'s own equivalents."""

from __future__ import annotations

import inspect

import pytest

from src.core.platform.application.master_data.org.commands import (
    organization_provisioning as organization_provisioning_module,
)
from src.core.platform.application.master_data.org.dto.commands.org import (
    OrganizationProvisionCommand,
)
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.infrastructure.persistence.uow.provisioning.platform_provisioning_unit_of_work import (
    SqlAlchemyPlatformProvisioningUnitOfWork,
)

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def test_successful_provisioning_persists_organization_and_entitlements_atomically_via_fresh_uow(
    services,
):
    provisioning = services["organization_provisioning_commands"]

    code = _unique_code("SUCCESS-PROV")
    organization = provisioning.provision_organization(OrganizationProvisionCommand(organization_code=code, display_name="Success Provisioned Org", timezone_name="UTC", base_currency="EUR", initial_module_codes=["project_management"]))

    reloaded = services["organization_query"]._organization_repo.get(organization.id)
    assert reloaded is not None
    assert reloaded.organization_code == code
    # Entitlement rows proven durable via the service surface: the provisioned organization
    # (always created ACTIVE and switched into) must reflect the module it was provisioned with.
    module_catalog = services["module_catalog_service"]
    assert module_catalog.is_enabled("project_management") is True


def test_fresh_session_per_provisioning_call(services, monkeypatch):
    provisioning = services["organization_provisioning_commands"]
    seen_sessions = []
    original_create = type(provisioning._provisioning_uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(provisioning._provisioning_uow_factory), "create", _spy_create)

    provisioning.provision_organization(OrganizationProvisionCommand(organization_code=_unique_code("FRESH-A"), display_name="Fresh A", timezone_name="UTC", base_currency="EUR", initial_module_codes=[]))
    provisioning.provision_organization(OrganizationProvisionCommand(organization_code=_unique_code("FRESH-B"), display_name="Fresh B", timezone_name="UTC", base_currency="EUR", initial_module_codes=[]))

    assert len(seen_sessions) == 2
    assert seen_sessions[0] is not seen_sessions[1]


def test_provisioning_participants_share_the_same_uow_session(services, monkeypatch):
    provisioning = services["organization_provisioning_commands"]
    seen = {}
    original_create = type(provisioning._provisioning_uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        seen["organizations_repo_session"] = uow.organizations.session
        seen["entitlements_repo_session"] = uow.entitlements.session
        seen["audit_session"] = uow._enterprise_audit_service._session
        return uow

    monkeypatch.setattr(type(provisioning._provisioning_uow_factory), "create", _spy_create)

    provisioning.provision_organization(OrganizationProvisionCommand(organization_code=_unique_code("SHARE-PROV"), display_name="Shared Session Prov", timezone_name="UTC", base_currency="EUR", initial_module_codes=["project_management"]))

    assert seen["uow_session"] is seen["organizations_repo_session"]
    assert seen["uow_session"] is seen["entitlements_repo_session"]
    assert seen["uow_session"] is seen["audit_session"]


def test_no_global_session_touch_during_provisioning(services):
    provisioning = services["organization_provisioning_commands"]
    legacy_session = services["session"]
    legacy_session.commit()  # settle any pending fixture-setup state

    provisioning.provision_organization(OrganizationProvisionCommand(organization_code=_unique_code("ISOLATED-PROV"), display_name="Isolated Prov", timezone_name="UTC", base_currency="EUR", initial_module_codes=[]))

    assert len(legacy_session.new) == 0
    assert len(legacy_session.dirty) == 0


def test_late_step_failure_rolls_back_organization_and_entitlements_together(services):
    """A failure in a later provisioning step (an unknown module code, raised from module
    entitlement provisioning) must roll back the ALREADY-staged organization row too -- proving
    the two writes share one transaction, not two."""
    provisioning = services["organization_provisioning_commands"]
    code = _unique_code("LATEFAIL")

    with pytest.raises(NotFoundError):
        provisioning.provision_organization(OrganizationProvisionCommand(organization_code=code, display_name="Late Failure Org", timezone_name="UTC", base_currency="EUR", initial_module_codes=["definitely-not-a-real-module-code"]))

    assert services["organization_query"]._organization_repo.get_by_code(code) is None


def test_commit_failure_leaves_no_partial_provisioning_state(services, monkeypatch):
    provisioning = services["organization_provisioning_commands"]

    captured_uow = {}
    original_create = type(provisioning._provisioning_uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(provisioning._provisioning_uow_factory), "create", _spy_create)

    def _fail_commit(self):
        raise RuntimeError("simulated provisioning commit failure")

    monkeypatch.setattr(SqlAlchemyPlatformProvisioningUnitOfWork, "commit", _fail_commit)

    code = _unique_code("COMMITFAIL-PROV")
    with pytest.raises(RuntimeError, match="simulated provisioning commit failure"):
        provisioning.provision_organization(OrganizationProvisionCommand(organization_code=code, display_name="Commit Fail Prov", timezone_name="UTC", base_currency="EUR", initial_module_codes=[]))

    uow = captured_uow["uow"]
    assert uow._committed is False
    assert uow._closed is True
    assert services["organization_query"]._organization_repo.get_by_code(code) is None


def test_runtime_active_organization_context_changes_only_after_successful_commit(services):
    provisioning = services["organization_provisioning_commands"]
    tenant_context_service = services["tenant_context_service"]
    default_active_id = tenant_context_service.get_active_organization().id

    code = _unique_code("ACTIVATE-PROV")
    organization = provisioning.provision_organization(OrganizationProvisionCommand(organization_code=code, display_name="Activate Prov Org", timezone_name="UTC", base_currency="EUR", initial_module_codes=[]))

    assert tenant_context_service.get_active_organization().id == organization.id
    assert organization.id != default_active_id


def test_provisioning_remains_tenant_scoped(services):
    provisioning = services["organization_provisioning_commands"]
    tenant_context_service = services["tenant_context_service"]
    tenant_id = tenant_context_service.get_active_tenant_id()

    code = _unique_code("TENANT-PROV")
    organization = provisioning.provision_organization(OrganizationProvisionCommand(organization_code=code, display_name="Tenant Prov Org", timezone_name="UTC", base_currency="EUR", initial_module_codes=[]))

    reloaded = services["organization_query"]._organization_repo.get_for_tenant(organization.id, tenant_id)
    assert reloaded is not None


def test_provisioning_never_gains_module_or_authorization_event_vocabulary():
    """`OrganizationCreated` is recorded elsewhere (end-to-end, including through provisioning) --
    no module-entitlement or authorization event vocabulary belongs in this module."""
    source = inspect.getsource(organization_provisioning_module)
    for forbidden in (
        "ModuleLicensed",
        "ModuleEnabled",
        "ModuleDisabled",
        "ScopeAccessGranted",
        "ScopeAccessRevoked",
        "RoleAssignmentGranted",
        "RoleAssignmentRevoked",
        "ApprovalRequested",
        "ApprovalApproved",
        "ApprovalRejected",
    ):
        assert forbidden not in source
