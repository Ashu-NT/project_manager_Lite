"""Compose optional integration eligibility without importing any Accounting module."""

from src.core.platform.application.integration.accounting.capability import AccountingIntegrationCapabilityService
from src.core.platform.application.tenant.modules.module_catalog_service import ModuleCatalogService
from src.core.platform.domain.tenant.modules import DEFAULT_ENTERPRISE_MODULES
from src.core.platform.infrastructure.persistence.read.tenant.modules.module_entitlement_reader import SqlAlchemyModuleEntitlementReader
from src.core.platform.infrastructure.persistence.repositories.integration.accounting_connector import SqlAlchemyAccountingConnectorRepository
from src.core.platform.infrastructure.persistence.repositories.tenant.modules.modules import SqlAlchemyModuleEntitlementRepository
from src.core.platform.integration.module_registry import ModuleRegistry


def build_accounting_capability(*, session, tenant_context_service, user_session, installed_adapters):
    repository = SqlAlchemyAccountingConnectorRepository(session)
    repository._tenant_context_service = tenant_context_service
    catalog = ModuleCatalogService(
        modules=DEFAULT_ENTERPRISE_MODULES, enabled_codes=(), licensed_codes=(),
        entitlement_repo=SqlAlchemyModuleEntitlementRepository(session, tenant_context_service=tenant_context_service),
        entitlement_reader=SqlAlchemyModuleEntitlementReader(session), user_session=user_session,
    )
    return AccountingIntegrationCapabilityService(
        module_registry=ModuleRegistry(catalog), connector_repository=repository,
        installed_adapters=installed_adapters,
    )
