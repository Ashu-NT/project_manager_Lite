from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

from src.core.platform.application.integration.accounting.commands import (
    AccountingConnectorConfigurationCommandHandler,
    connector_configuration,
)
from src.core.platform.application.integration.accounting.queries import (
    AccountingIntegrationCapabilityQueryHandler,
)
from src.core.platform.common.exceptions import BusinessRuleError


@pytest.fixture
def configuration_dependencies(monkeypatch):
    permission = Mock()
    audit = Mock()
    monkeypatch.setattr(connector_configuration, "require_permission", permission)
    monkeypatch.setattr(connector_configuration, "record_audit_entry", audit)
    scope = Mock()
    scope.require_active_scope_ids.return_value = SimpleNamespace(
        tenant_id="tenant", organization_id="organization"
    )
    return SimpleNamespace(
        repository=Mock(), scope=scope, user=Mock(), audit_service=Mock(),
        permission=permission, audit=audit,
    )


def participant(dependencies):
    return AccountingConnectorConfigurationCommandHandler(
        repository=dependencies.repository,
        tenant_context_service=dependencies.scope,
        user_session=dependencies.user,
        enterprise_audit_service=dependencies.audit_service,
        installed_adapters={"installed"},
    )


def configure(handler, *, expected_version=None, adapter_id="installed"):
    return handler.configure(
        adapter_id=adapter_id, connection_id="connection", secret_reference="secret",
        enabled=True, expected_version=expected_version,
    )


@pytest.mark.parametrize("expected_version,version", [(None, 1), (4, 5)])
def test_configuration_participates_without_committing(
    configuration_dependencies, expected_version, version
):
    dependencies = configuration_dependencies
    handler = participant(dependencies)
    result = configure(handler, expected_version=expected_version)
    assert result.version == version
    assert (result.tenant_id, result.organization_id) == ("tenant", "organization")
    dependencies.repository.save.assert_called_once_with(
        result, expected_version=expected_version
    )
    dependencies.repository.commit.assert_not_called()
    dependencies.audit_service.commit.assert_not_called()
    dependencies.permission.assert_called_once_with(
        dependencies.user, "integration.accounting.configure",
        operation_label="configure Accounting integration",
    )
    audit_arguments = dependencies.audit.call_args.kwargs
    assert audit_arguments["commit"] is False
    assert audit_arguments["fail_closed"] is True
    assert audit_arguments["after_data"] == {"enabled": True, "version": version}


def test_configuration_authorization_precedes_adapter_and_scope(configuration_dependencies):
    dependencies = configuration_dependencies
    dependencies.permission.side_effect = BusinessRuleError("denied")
    with pytest.raises(BusinessRuleError, match="denied"):
        configure(participant(dependencies), adapter_id="unknown")
    dependencies.scope.require_active_scope_ids.assert_not_called()
    dependencies.repository.save.assert_not_called()


def test_configuration_rejects_uninstalled_adapter(configuration_dependencies):
    dependencies = configuration_dependencies
    with pytest.raises(BusinessRuleError) as error:
        configure(participant(dependencies), adapter_id="unknown")
    assert error.value.code == "adapter_not_installed"
    dependencies.scope.require_active_scope_ids.assert_not_called()
    dependencies.repository.save.assert_not_called()


@pytest.mark.parametrize("failure", [None, "audit", "save", "commit", "prepare"])
def test_composed_handler_owns_uow_only_after_preparation(
    configuration_dependencies, failure
):
    dependencies = configuration_dependencies
    factory = Mock()
    context_manager = MagicMock()
    uow = context_manager.__enter__.return_value
    factory.create.return_value = context_manager
    uow.accounting_connectors = dependencies.repository
    uow._enterprise_audit_service = dependencies.audit_service
    prepare = Mock()
    handler = AccountingConnectorConfigurationCommandHandler(
        uow_factory=factory, tenant_context_service=dependencies.scope,
        user_session=dependencies.user, installed_adapters={"installed"},
        prepare_command=prepare,
    )
    targets = {
        "audit": dependencies.audit, "save": dependencies.repository.save,
        "commit": uow.commit, "prepare": prepare,
    }
    if failure:
        targets[failure].side_effect = RuntimeError(failure)
        with pytest.raises(RuntimeError, match=failure):
            configure(handler)
    else:
        assert configure(handler).version == 1
    prepare.assert_called_once_with()
    if failure == "prepare":
        factory.create.assert_not_called()
    else:
        factory.create.assert_called_once()
        assert factory.create.call_args.kwargs["context"].correlation_id
        context_manager.__exit__.assert_called_once()
        if failure != "save":
            assert dependencies.audit.call_args.args[0]._enterprise_audit_service is (
                dependencies.audit_service
            )
    if failure in {"audit", "save", "prepare"}:
        uow.commit.assert_not_called()
    else:
        uow.commit.assert_called_once_with()


@pytest.mark.parametrize(
    "authorized,installed,module,connector,eligible,reason",
    [
        (False, False, False, None, False, "permission_denied"),
        (True, False, False, None, False, "adapter_not_installed"),
        (True, True, False, None, False, "module_not_enabled"),
        (True, True, True, None, False, "integration_not_configured"),
        (True, True, True, (False, "unknown"), False, "connection_disabled"),
        (True, True, True, (True, "unknown"), False, "adapter_not_installed"),
        (True, True, True, (True, "installed"), False, "business_precondition_failed"),
        (True, True, True, (True, "installed"), True, None),
    ],
)
def test_capability_preserves_denial_precedence_and_lock_forwarding(
    authorized, installed, module, connector, eligible, reason
):
    registry = Mock()
    registry.has_capability.return_value = module
    repository = Mock()
    repository.get.return_value = (
        SimpleNamespace(enabled=connector[0], adapter_id=connector[1])
        if connector else None
    )
    adapters = {"installed"} if installed else set()
    handler = AccountingIntegrationCapabilityQueryHandler(
        module_registry=registry, connector_repository=repository,
        installed_adapters=adapters,
    )
    adapters.clear()
    result = handler.evaluate(authorized=authorized, eligible=eligible, for_update=True)
    assert result.allowed is (reason is None)
    assert result.reason == reason
    assert bool(result.message) is (reason is not None)
    if authorized and installed and module:
        repository.get.assert_called_once_with(for_update=True)
    else:
        repository.get.assert_not_called()
