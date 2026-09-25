from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.integration.accounting.connector import (
    AccountingConnectorConfiguration,
)
from src.core.shared.audit import record_audit_entry


class AccountingConnectorConfigurationService:
    """Transaction participant; the caller's UoW owns configuration and audit commit."""

    def __init__(
        self,
        *,
        repository,
        tenant_context_service,
        user_session,
        enterprise_audit_service,
        installed_adapters,
    ):
        self._repository = repository
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._installed = frozenset(installed_adapters)

    def configure(
        self, *, adapter_id, connection_id, secret_reference, enabled, expected_version
    ):
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
