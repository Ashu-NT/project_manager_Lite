from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, call

import pytest
from sqlalchemy.exc import IntegrityError

from src.core.platform.api.desktop.platform_runtime.runtime import (
    PlatformRuntimeDesktopApi,
)
from src.core.platform.application.master_data.org.commands import (
    organization_provisioning,
)
from src.core.platform.application.master_data.org.commands.organization_provisioning import (
    OrganizationProvisioningCommandHandler,
)
from src.core.platform.application.master_data.org.dto import (
    OrganizationProvisionCommand,
)
from src.core.platform.application.platform_runtime import PlatformRuntimeQueryHandler
from src.core.platform.application.tenant.modules import build_default_module_catalog
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError


@pytest.mark.parametrize("permissions,accessible", [
    (None, False), (frozenset(), False), (frozenset({"audit.read"}), False),
    (frozenset({"task.read"}), True),
])
def test_runtime_queries_combine_catalog_and_current_session(permissions, accessible):
    catalog = build_default_module_catalog()
    session = SimpleNamespace(principal=(
        SimpleNamespace(permissions=permissions) if permissions is not None else None
    ))
    handler = PlatformRuntimeQueryHandler(module_catalog_service=catalog, user_session=session)
    assert handler.get_current_permissions() == (permissions or frozenset())
    assert bool(handler.list_accessible_modules()) is accessible
    snapshot = handler.snapshot()
    assert snapshot.context_label == catalog.current_context_label()
    assert snapshot.module_snapshot.enabled_modules[0].code == "project_management"
    session.principal = None
    assert handler.list_accessible_modules() == ()


def test_runtime_handler_has_no_organization_or_catalog_passthroughs():
    handler = PlatformRuntimeQueryHandler(module_catalog_service=build_default_module_catalog())
    assert handler.get_current_permissions() == frozenset()
    for retired_method in (
        "provision_organization", "get_active_organization", "list_organizations",
        "create_organization", "update_organization", "activate_organization",
        "list_modules", "is_enabled", "get_entitlement",
    ):
        assert not hasattr(handler, retired_method)


@pytest.fixture
def provisioning_dependencies(monkeypatch):
    permission = Mock()
    monkeypatch.setattr(organization_provisioning, "require_permission", permission)
    manager = MagicMock()
    uow = manager.__enter__.return_value
    factory = Mock()
    factory.create.return_value = manager
    commands = Mock()
    organization = SimpleNamespace(id="new-organization")
    commands.create_organization_using.return_value = organization
    query = Mock()
    query.require_current_tenant_id.return_value = "tenant"
    catalog = Mock()
    catalog.list_modules.return_value = (
        SimpleNamespace(code="default", default_enabled=True, stage="live"),
        SimpleNamespace(code="planned", default_enabled=True, stage="planned"),
        SimpleNamespace(code="optional", default_enabled=False, stage="live"),
    )
    tenant_context = Mock()
    entitlements = Mock()
    user = Mock()
    handler = OrganizationProvisioningCommandHandler(
        module_catalog_service=catalog, module_entitlement_provisioning=entitlements,
        organization_query=query, organization_commands=commands,
        tenant_context_service=tenant_context, user_session=user,
        provisioning_uow_factory=factory,
    )
    return SimpleNamespace(
        permission=permission, manager=manager, uow=uow, factory=factory, user=user,
        commands=commands, query=query, catalog=catalog, tenant_context=tenant_context,
        entitlements=entitlements, organization=organization, handler=handler,
    )


@pytest.mark.parametrize("initial,expected", [
    (None, {"default"}), ((), set()), (("optional", "optional"), {"optional"}),
])
def test_provisioning_shares_uow_and_switches_context_after_commit(
    provisioning_dependencies, initial, expected
):
    dependencies = provisioning_dependencies
    order = Mock()
    order.attach_mock(dependencies.commands.create_organization_using, "create")
    order.attach_mock(dependencies.entitlements.provision_organization_entitlements_using, "entitle")
    order.attach_mock(dependencies.uow.commit, "commit")
    order.attach_mock(dependencies.tenant_context.set_active_organization, "switch")
    order.attach_mock(dependencies.entitlements.notify_module_entitlements_stale, "notify")
    command = OrganizationProvisionCommand(
        organization_code="NEW", display_name="New", timezone_name="UTC",
        base_currency="EUR", initial_module_codes=initial, legal_name="Legal name",
        tax_id="tax", address_line_1="address", email="contact@example.test",
    )
    assert dependencies.handler.provision_organization(command) is dependencies.organization
    assert [entry[0] for entry in order.mock_calls] == ["create", "entitle", "commit", "switch", "notify"]
    create_call = dependencies.commands.create_organization_using.call_args
    assert create_call.args == (dependencies.uow.organizations, dependencies.uow)
    assert create_call.kwargs["tenant_id"] == "tenant"
    assert create_call.kwargs["legal_name"] == command.legal_name
    assert create_call.kwargs["tax_id"] == command.tax_id
    assert create_call.kwargs["address_line_1"] == command.address_line_1
    assert create_call.kwargs["email"] == command.email
    dependencies.entitlements.provision_organization_entitlements_using.assert_called_once_with(
        dependencies.uow, "new-organization",
        licensed_module_codes=expected, enabled_module_codes=expected,
    )
    dependencies.permission.assert_has_calls([
        call(dependencies.user, "settings.manage", operation_label="provision organization"),
        call(dependencies.user, "settings.manage", operation_label="set active organization context"),
    ])
    dependencies.query.require_current_tenant_id.assert_called_once_with(
        operation_label="provision organization"
    )
    dependencies.factory.create.assert_called_once()
    assert dependencies.factory.create.call_args.kwargs["context"].correlation_id
    dependencies.manager.__exit__.assert_called_once_with(None, None, None)


@pytest.mark.parametrize("failure", ["create", "entitle", "commit", "integrity"])
def test_provisioning_failures_do_not_switch_context_or_emit_stale_hint(
    provisioning_dependencies, failure
):
    dependencies = provisioning_dependencies
    targets = {
        "create": dependencies.commands.create_organization_using,
        "entitle": dependencies.entitlements.provision_organization_entitlements_using,
        "commit": dependencies.uow.commit, "integrity": dependencies.uow.commit,
    }
    error = (IntegrityError("statement", {}, ValueError("duplicate"))
             if failure == "integrity" else RuntimeError("injected"))
    targets[failure].side_effect = error
    command = OrganizationProvisionCommand(
        organization_code="NEW", display_name="New", timezone_name="UTC", base_currency="EUR",
    )
    with pytest.raises(ValidationError if failure == "integrity" else RuntimeError) as caught:
        dependencies.handler.provision_organization(command)
    if failure == "integrity":
        assert caught.value.code == "ORGANIZATION_CODE_EXISTS"
        assert caught.value.__cause__ is error
    dependencies.tenant_context.set_active_organization.assert_not_called()
    dependencies.entitlements.notify_module_entitlements_stale.assert_not_called()
    dependencies.manager.__exit__.assert_called_once()
    if failure in {"create", "entitle"}:
        dependencies.uow.commit.assert_not_called()


@pytest.mark.parametrize("permission_gate", [1, 2])
def test_provisioning_checks_permission_before_opening_uow(
    provisioning_dependencies, permission_gate
):
    dependencies = provisioning_dependencies
    dependencies.permission.side_effect = (
        [None] * (permission_gate - 1) + [BusinessRuleError("denied")]
    )
    command = OrganizationProvisionCommand(
        organization_code="NEW", display_name="New", timezone_name="UTC", base_currency="EUR",
    )
    with pytest.raises(BusinessRuleError, match="denied"):
        dependencies.handler.provision_organization(command)
    if permission_gate == 1:
        dependencies.query.require_current_tenant_id.assert_not_called()
    else:
        dependencies.query.require_current_tenant_id.assert_called_once()
    dependencies.factory.create.assert_not_called()
    dependencies.tenant_context.set_active_organization.assert_not_called()


@pytest.mark.parametrize("method,dependency,arguments", [
    ("provision_organization", "organization_provisioning_commands", (object(),)),
    ("update_organization", "organization_commands", (object(),)),
    ("activate_organization", "organization_lifecycle", ("organization",)),
    ("deactivate_organization", "organization_lifecycle", ("organization",)),
    ("archive_organization", "organization_lifecycle", ("organization",)),
])
def test_desktop_api_routes_to_injected_narrow_commands(method, dependency, arguments):
    collaborators = {name: Mock() for name in (
        "platform_runtime_query", "module_catalog_service", "organization_query",
        "organization_commands", "organization_lifecycle", "organization_provisioning_commands",
        "tenant_context_service", "module_entitlement_commands",
    )}
    api = PlatformRuntimeDesktopApi(**collaborators)
    api._serialize_organization = Mock(side_effect=lambda organization: organization)
    result = getattr(api, method)(*arguments)
    assert result.ok
    target = getattr(collaborators[dependency], method)
    target.assert_called_once_with(*arguments)
    assert result.data is target.return_value
    assert collaborators["platform_runtime_query"].mock_calls == []


def test_desktop_api_routes_reads_to_organization_and_catalog_handlers():
    collaborators = {name: Mock() for name in (
        "platform_runtime_query", "module_catalog_service", "organization_query",
        "organization_commands", "organization_lifecycle", "organization_provisioning_commands",
        "tenant_context_service", "module_entitlement_commands",
    )}
    collaborators["organization_query"].get_organization_count.return_value = 7
    collaborators["module_catalog_service"].list_modules.return_value = ()
    api = PlatformRuntimeDesktopApi(**collaborators)
    assert api.get_organization_count().data == 7
    assert api.list_modules().data == ()
    collaborators["organization_query"].get_organization_count.assert_called_once_with()
    collaborators["module_catalog_service"].list_modules.assert_called_once_with()
