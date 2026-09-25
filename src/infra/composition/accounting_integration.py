"""Compose optional integration eligibility without importing any Accounting module."""

from sqlalchemy.orm import sessionmaker
from src.core.platform.application.integration.accounting.commands import AccountingConnectorConfigurationCommands
from src.core.platform.infrastructure.persistence.uow.integration.accounting_connector import SqlAlchemyAccountingConnectorUnitOfWorkFactory

from src.core.platform.application.integration.accounting.capability import (
    AccountingIntegrationCapabilityService,
)
from src.core.platform.application.tenant.modules.module_catalog_service import (
    ModuleCatalogService,
)
from src.core.platform.domain.tenant.modules import DEFAULT_ENTERPRISE_MODULES
from src.core.platform.infrastructure.persistence.read.tenant.modules.module_entitlement_reader import (
    SqlAlchemyModuleEntitlementReader,
)
from src.core.platform.infrastructure.persistence.repositories.integration.accounting_connector import (
    SqlAlchemyAccountingConnectorRepository,
)
from src.core.platform.infrastructure.persistence.repositories.tenant.modules.modules import (
    SqlAlchemyModuleEntitlementRepository,
)
from src.core.platform.integration.module_registry import ModuleRegistry


def build_accounting_capability(
    *, session, tenant_context_service, user_session, installed_adapters
):
    repository = SqlAlchemyAccountingConnectorRepository(session)
    repository._tenant_context_service = tenant_context_service
    catalog = ModuleCatalogService(
        modules=DEFAULT_ENTERPRISE_MODULES,
        enabled_codes=(),
        licensed_codes=(),
        read_only=True,
        entitlement_repo=SqlAlchemyModuleEntitlementRepository(
            session, tenant_context_service=tenant_context_service
        ),
        entitlement_reader=SqlAlchemyModuleEntitlementReader(session),
        user_session=user_session,
    )
    return AccountingIntegrationCapabilityService(
        module_registry=ModuleRegistry(catalog),
        connector_repository=repository,
        installed_adapters=installed_adapters,
    )


def build_accounting_configuration_commands(*, session, platform_services, installed_adapters):
    def release_read_transaction():
        if session.new or session.dirty or session.deleted:
            raise RuntimeError("Cannot configure Accounting with pending shared-session writes.")
        if session.in_transaction():
            session.rollback()
    return AccountingConnectorConfigurationCommands(
        uow_factory=SqlAlchemyAccountingConnectorUnitOfWorkFactory(
            session_factory=sessionmaker(bind=session.bind, expire_on_commit=False),
            transactional_dispatcher=platform_services.platform_transactional_dispatcher,
            post_commit_bus=platform_services.platform_post_commit_bus,
            tenant_context_service=platform_services.tenant_context_service,
            user_session=platform_services.user_session,
        ),
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session, installed_adapters=installed_adapters,
        prepare_command=release_read_transaction,
    )
