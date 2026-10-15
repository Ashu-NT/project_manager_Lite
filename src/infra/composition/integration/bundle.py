from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core.platform.application.integration import IntegrationOutboxService
from src.core.platform.application.integration.accounting.commands import (
    AccountingConnectorConfigurationCommandHandler,
)
from src.core.platform.integration.module_registry import ModuleRegistry
from src.core.platform.integration.resolver import IntegrationResolver
from src.infra.integration.approved_time_dispatcher import (
    ApprovedTimeFinancialDispatcher,
)
from src.infra.integration.procurement_financial_dispatcher import (
    ProcurementFinancialDispatcher,
)


@dataclass(frozen=True)
class IntegrationRuntimeBundle:
    """Application-owned cross-boundary runtime; module bundles stay independent."""

    module_registry: ModuleRegistry
    integration_resolver: IntegrationResolver
    time_financial_outbox_service: IntegrationOutboxService
    procurement_financial_outbox_service: IntegrationOutboxService
    approved_time_financial_dispatcher: ApprovedTimeFinancialDispatcher
    procurement_financial_dispatcher: ProcurementFinancialDispatcher
    accounting_connector_commands: AccountingConnectorConfigurationCommandHandler

    def runtime_bindings(self) -> dict[str, Any]:
        """Export existing composed capabilities for application runtime assembly."""
        return {
            'module_registry': self.module_registry,
            'integration_resolver': self.integration_resolver,
            'time_financial_outbox_service': self.time_financial_outbox_service,
            'procurement_financial_outbox_service': self.procurement_financial_outbox_service,
            'approved_time_financial_dispatcher': self.approved_time_financial_dispatcher,
            'procurement_financial_dispatcher': self.procurement_financial_dispatcher,
            'accounting_connector_commands': self.accounting_connector_commands,
        }
