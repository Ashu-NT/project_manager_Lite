"""Assemble module entitlement and Platform runtime services."""

from __future__ import annotations

import os
from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from src.core.platform.application.data_operations.runtime_tracking import (
    RuntimeExecutionService,
)
from src.core.platform.application.history.audit import EnterpriseAuditService
from src.core.platform.application.master_data.org.organization_service import (
    OrganizationService,
)
from src.core.platform.application.platform_runtime import (
    PlatformRuntimeApplicationService,
)
from src.core.platform.application.tenant.modules import ModuleCatalogService
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.domain.tenant.modules import (
    DEFAULT_ENTERPRISE_MODULES,
    parse_enabled_module_codes,
    parse_licensed_module_codes,
)
from src.core.platform.infrastructure.persistence.read.tenant.modules.module_entitlement_reader import (
    SqlAlchemyModuleEntitlementReader,
)
from src.core.platform.infrastructure.persistence.repositories.data_operations.runtime_tracking.runtime_tracking import (
    SqlAlchemyRuntimeExecutionRepository,
)
from src.core.platform.infrastructure.persistence.repositories.tenant.modules.modules import (
    SqlAlchemyModuleEntitlementRepository,
)
from src.core.platform.infrastructure.persistence.uow.module_entitlement_unit_of_work import (
    SqlAlchemyModuleEntitlementUnitOfWorkFactory,
)
from src.core.platform.infrastructure.persistence.uow.platform_provisioning_unit_of_work import (
    SqlAlchemyPlatformProvisioningUnitOfWorkFactory,
)
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.events.in_process_view_invalidation_channel import (
    InProcessViewInvalidationChannel,
)
from src.infra.time.system_clock import SystemClock


@dataclass(frozen=True)
class ModuleDependencies:
    module_catalog_service: ModuleCatalogService
    platform_runtime_application_service: PlatformRuntimeApplicationService
    runtime_execution_service: RuntimeExecutionService


def build_module_dependencies(
    *,
    session: Session,
    user_session: UserSessionContext,
    tenant_context_service: TenantContextService,
    enterprise_audit_service: EnterpriseAuditService,
    organization_service: OrganizationService,
    view_invalidation_channel: InProcessViewInvalidationChannel,
    transactional_dispatcher: InProcessTransactionalEventDispatcher,
    post_commit_bus: InProcessPostCommitEventBus,
) -> ModuleDependencies:
    entitlement_repo = SqlAlchemyModuleEntitlementRepository(
        session, tenant_context_service=tenant_context_service
    )
    entitlement_reader = SqlAlchemyModuleEntitlementReader(session)
    entitlement_uow_factory = SqlAlchemyModuleEntitlementUnitOfWorkFactory(
        session_factory=sessionmaker(bind=session.bind, future=True),
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    module_catalog_service = ModuleCatalogService(
        modules=DEFAULT_ENTERPRISE_MODULES,
        enabled_codes=parse_enabled_module_codes(os.getenv("PM_ENABLED_MODULES")),
        licensed_codes=parse_licensed_module_codes(
            os.getenv("PM_LICENSED_MODULES")
            if os.getenv("PM_LICENSED_MODULES") is not None
            else os.getenv("PM_ENABLED_MODULES")
        ),
        entitlement_repo=entitlement_repo,
        entitlement_reader=entitlement_reader,
        session=session,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        organization_context_provider=tenant_context_service.get_active_organization,
        uow_factory=entitlement_uow_factory,
        clock=SystemClock(),
        view_invalidation_channel=view_invalidation_channel,
    )
    module_catalog_service.bootstrap_defaults()
    provisioning_uow_factory = SqlAlchemyPlatformProvisioningUnitOfWorkFactory(
        session_factory=sessionmaker(bind=session.bind, future=True),
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    platform_runtime_application_service = PlatformRuntimeApplicationService(
        module_catalog_service=module_catalog_service,
        organization_service=organization_service,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
        provisioning_uow_factory=provisioning_uow_factory,
    )
    runtime_execution_service = RuntimeExecutionService(
        runtime_execution_repo=SqlAlchemyRuntimeExecutionRepository(
            session, tenant_context_service=tenant_context_service
        ),
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    return ModuleDependencies(
        module_catalog_service=module_catalog_service,
        platform_runtime_application_service=platform_runtime_application_service,
        runtime_execution_service=runtime_execution_service,
    )
