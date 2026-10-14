from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.integration.accounting.connector import (
    AccountingConnectorConfiguration,
)
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext

if TYPE_CHECKING:
    from src.core.platform.contract.uow.integration.accounting_connector import (
        AccountingConnectorUnitOfWorkFactory,
    )


class AccountingConnectorConfigurationCommandHandler:
    """Configure in a caller-owned transaction or an explicitly supplied UoW."""

    def __init__(
        self,
        *,
        repository=None,
        tenant_context_service,
        user_session,
        enterprise_audit_service=None,
        installed_adapters,
        uow_factory: AccountingConnectorUnitOfWorkFactory | None = None,
        prepare_command=None,
    ):
        self._repository = repository
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._installed = frozenset(installed_adapters)
        self._uow_factory = uow_factory
        self._prepare_command = prepare_command

    def configure(
        self,
        *,
        adapter_id: str,
        connection_id: str,
        secret_reference: str,
        enabled: bool,
        expected_version: int | None,
    ) -> AccountingConnectorConfiguration:
        if self._uow_factory is not None:
            if self._prepare_command is not None:
                self._prepare_command()
            with self._uow_factory.create(
                context=DomainEventContext(correlation_id=str(uuid4()))
            ) as uow:
                participant = AccountingConnectorConfigurationCommandHandler(
                    repository=uow.accounting_connectors,
                    tenant_context_service=self._tenant_context_service,
                    user_session=self._user_session,
                    enterprise_audit_service=uow._enterprise_audit_service,
                    installed_adapters=self._installed,
                )
                result = participant.configure(
                    adapter_id=adapter_id,
                    connection_id=connection_id,
                    secret_reference=secret_reference,
                    enabled=enabled,
                    expected_version=expected_version,
                )
                uow.commit()
            return result

        require_permission(
            self._user_session,
            "integration.accounting.configure",
            operation_label="configure Accounting integration",
        )
        if adapter_id not in self._installed:
            raise BusinessRuleError(
                "Accounting integration is not installed.", code="adapter_not_installed"
            )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="configure Accounting integration"
        )
        configuration = AccountingConnectorConfiguration(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            adapter_id=adapter_id,
            connection_id=connection_id,
            secret_reference=secret_reference,
            enabled=enabled,
            version=1 if expected_version is None else expected_version + 1,
        )
        self._repository.save(configuration, expected_version=expected_version)
        record_audit_entry(
            self,
            operation="accounting_connector.configure",
            entity_type="AccountingConnector",
            entity_id=scope.organization_id,
            module="platform",
            category="SECURITY",
            after_data={
                "enabled": configuration.enabled,
                "version": configuration.version,
            },
            commit=False,
            fail_closed=True,
        )
        return configuration

