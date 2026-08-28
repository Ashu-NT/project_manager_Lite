"""P5B prerequisite (Module Entitlement Transaction Convergence):
`SqlAlchemyModuleEntitlementUnitOfWork` -- the Module Entitlement capability's own thin, concrete
subclass of the P3 `SqlAlchemyUnitOfWorkBase`, adding exactly the one named accessor
`ModuleEntitlementUnitOfWork` declares (`entitlements`) plus `_enterprise_audit_service`, both
bound to this instance's own fresh `Session` -- never the shared, process-lifetime one
`ModuleCatalogService`'s other, not-yet-migrated methods (the lazy default-entitlement seeding
inside `_ensure_context_defaults`, out of this prerequisite pass's scope -- see the P5B report)
still use. Mirrors `SqlAlchemyOrganizationUnitOfWork`/`SqlAlchemyPlatformUnitOfWork` exactly.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.platform.contract.uow.module_entitlement_unit_of_work import (
    ModuleEntitlementUnitOfWork,
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


class SqlAlchemyModuleEntitlementUnitOfWork(SqlAlchemyUnitOfWorkBase, ModuleEntitlementUnitOfWork):
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


class SqlAlchemyModuleEntitlementUnitOfWorkFactory(SqlAlchemyUnitOfWorkFactoryBase):
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

    def create(self, *, context: DomainEventContext) -> SqlAlchemyModuleEntitlementUnitOfWork:
        return SqlAlchemyModuleEntitlementUnitOfWork(
            session=self._session_factory(),
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
            context=context,
            tenant_context_service=self._tenant_context_service,
            user_session=self._user_session,
        )


__all__ = [
    "SqlAlchemyModuleEntitlementUnitOfWork",
    "SqlAlchemyModuleEntitlementUnitOfWorkFactory",
]
