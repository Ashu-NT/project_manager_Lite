from src.core.platform.domain.integration.accounting.connector import (
    AccountingHandoffCapability,
    AccountingHandoffDenial,
)


class AccountingIntegrationCapabilityService:
    """Installed adapters come from trusted composition, never organization data."""

    def __init__(self, *, module_registry, connector_repository, installed_adapters=frozenset()):
        self._registry = module_registry
        self._connectors = connector_repository
        self._installed = frozenset(installed_adapters)

    def evaluate(self, *, authorized: bool, eligible: bool, for_update=False):
        reason = None
        if not authorized:
            reason = AccountingHandoffDenial.PERMISSION_DENIED
        elif not self._installed:
            reason = AccountingHandoffDenial.ADAPTER_NOT_INSTALLED
        elif not self._registry.has_capability("accounting.handoff"):
            reason = AccountingHandoffDenial.MODULE_NOT_ENABLED
        else:
            connector = self._connectors.get(for_update=for_update)
            if connector is None or not connector.enabled:
                reason = AccountingHandoffDenial.INTEGRATION_NOT_CONFIGURED
            elif connector.adapter_id not in self._installed:
                reason = AccountingHandoffDenial.ADAPTER_NOT_INSTALLED
            elif not eligible:
                reason = AccountingHandoffDenial.BUSINESS_PRECONDITION_FAILED
        return AccountingHandoffCapability(allowed=reason is None, reason=reason)
