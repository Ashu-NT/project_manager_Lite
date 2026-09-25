from uuid import uuid4

from src.core.platform.application.integration.accounting.configuration_service import AccountingConnectorConfigurationService
from src.core.platform.contract.uow.integration.accounting_connector import AccountingConnectorUnitOfWorkFactory
from src.core.platform.domain.integration.accounting.connector import AccountingConnectorConfiguration
from src.core.shared.events.domain_event_context import DomainEventContext


class AccountingConnectorConfigurationCommands:
    """Outward external-connector administration boundary; no delivery or secret reads."""

    def __init__(self, *, uow_factory: AccountingConnectorUnitOfWorkFactory, tenant_context_service, user_session, installed_adapters, prepare_command):
        self._uow_factory = uow_factory
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._installed_adapters = frozenset(installed_adapters)
        self._prepare_command = prepare_command

    def configure(self, *, adapter_id: str, connection_id: str, secret_reference: str, enabled: bool, expected_version: int | None) -> AccountingConnectorConfiguration:
        self._prepare_command()
        with self._uow_factory.create(context=DomainEventContext(correlation_id=str(uuid4()))) as uow:
            service = AccountingConnectorConfigurationService(
                repository=uow.accounting_connectors, tenant_context_service=self._tenant_context_service,
                user_session=self._user_session, enterprise_audit_service=uow._enterprise_audit_service,
                installed_adapters=self._installed_adapters,
            )
            result = service.configure(adapter_id=adapter_id, connection_id=connection_id,
                                       secret_reference=secret_reference, enabled=enabled, expected_version=expected_version)
            uow.commit()
        return result
