"""P4C (Platform Runtime Organization Provisioning Transaction Convergence):
`SqlAlchemyPlatformProvisioningUnitOfWork` -- provisioning's own thin, concrete subclass of the P3
`SqlAlchemyUnitOfWorkBase`, adding exactly the two named accessors
`PlatformProvisioningUnitOfWork` declares (`organizations`, `entitlements`) plus
`_enterprise_audit_service`, all bound to this instance's own fresh `Session` -- never the shared,
process-lifetime one `PlatformRuntimeApplicationService`'s other, not-yet-migrated collaborators
still use. Mirrors `SqlAlchemyOrganizationUnitOfWork`/`SqlAlchemyPlatformUnitOfWork` exactly.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.platform.contract.persistence.platform_provisioning_unit_of_work import (
    PlatformProvisioningUnitOfWork,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.org.org import (
    SqlAlchemyOrganizationRepository,
)
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import (
    SqlAlchemyAuditRepository,
)
from src.core.platform.infrastructure.persistence.repositories.tenant.modules.modules import (
    SqlAlchemyModuleEntitlementRepository,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_event_publisher import (
    PostCommitEventPublisher,
    TransactionalEventDispatcher,
)
from src.infra.persistence.db.unit_of_work import (
    SqlAlchemyUnitOfWorkBase,
    SqlAlchemyUnitOfWorkFactoryBase,
)


class SqlAlchemyPlatformProvisioningUnitOfWork(SqlAlchemyUnitOfWorkBase, PlatformProvisioningUnitOfWork):
    def __init__(
        self,
        *,
        session: Session,
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
        context: DomainEventContext,
        tenant_context_service: TenantContextService,
        user_session,
    ) -> None:
        super().__init__(
            session=session,
            transactional_dispatcher=transactional_dispatcher,
            post_commit_bus=post_commit_bus,
            context=context,
        )
        self.organizations = SqlAlchemyOrganizationRepository(session)
        self.entitlements = SqlAlchemyModuleEntitlementRepository(
            session, tenant_context_service=tenant_context_service
        )

        audit_repo = SqlAlchemyAuditRepository(session)
        audit_repo._tenant_context_service = tenant_context_service
        self._enterprise_audit_service = EnterpriseAuditService(
            session=session,
            audit_repo=audit_repo,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
        )


class SqlAlchemyPlatformProvisioningUnitOfWorkFactory(SqlAlchemyUnitOfWorkFactoryBase):
    """Closes over a session *factory* (per ADR-005 Section 6.1) plus the ambient collaborators
    (`tenant_context_service`, `user_session`) needed to build this UoW's fresh, session-bound
    accessors on every `create()` call."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
        tenant_context_service: TenantContextService,
        user_session,
    ) -> None:
        super().__init__(
            session_factory=session_factory,
            transactional_dispatcher=transactional_dispatcher,
            post_commit_bus=post_commit_bus,
        )
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session

    def create(self, *, context: DomainEventContext) -> SqlAlchemyPlatformProvisioningUnitOfWork:
        return SqlAlchemyPlatformProvisioningUnitOfWork(
            session=self._session_factory(),
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
            context=context,
            tenant_context_service=self._tenant_context_service,
            user_session=self._user_session,
        )


__all__ = [
    "SqlAlchemyPlatformProvisioningUnitOfWork",
    "SqlAlchemyPlatformProvisioningUnitOfWorkFactory",
]
