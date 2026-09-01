from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from src.core.modules.inventory_procurement.contracts.uow.inventory.inventory_foundation_unit_of_work import (
    InventoryFoundationUnitOfWork,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.inventory import (
    SqlAlchemyStorageLocationRepository,
    SqlAlchemyStoreroomRepository,
)
from src.core.platform.application.history.activity.activity_service import ActivityService
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.infrastructure.persistence.repositories.history.activity.activity import (
    SqlAlchemyActivityRepository,
)
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import (
    SqlAlchemyAuditRepository,
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


class SqlAlchemyInventoryFoundationUnitOfWork(
    SqlAlchemyUnitOfWorkBase, InventoryFoundationUnitOfWork
):
    def __init__(
        self,
        *,
        session: Session,
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
        context: DomainEventContext,
        tenant_context_service,
        user_session,
    ) -> None:
        super().__init__(
            session=session,
            transactional_dispatcher=transactional_dispatcher,
            post_commit_bus=post_commit_bus,
            context=context,
        )
        self.storerooms = SqlAlchemyStoreroomRepository(
            session, tenant_context_service=tenant_context_service
        )
        self.locations = SqlAlchemyStorageLocationRepository(
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
        # Storeroom/Location activity recording was previously silent dead code (P20 finding):
        # `InventoryService`/`InventoryFoundationService` were never wired with an
        # `_activity_service` at all, so `record_activity(self, ...)` always no-opped. Bound
        # to this same fresh transaction, mirroring Resource's P18A activity-atomicity fix.
        activity_repo = SqlAlchemyActivityRepository(session)
        activity_repo._tenant_context_service = tenant_context_service
        self._activity_service = ActivityService(
            session=session,
            activity_repo=activity_repo,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
        )


class SqlAlchemyInventoryFoundationUnitOfWorkFactory(SqlAlchemyUnitOfWorkFactoryBase):
    """Closes over a session *factory* -- every `create()` call opens a genuinely fresh
    `Session`, matching every other Platform/module canonical UoW factory's own convention."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
        tenant_context_service,
        user_session,
    ) -> None:
        super().__init__(
            session_factory=session_factory,
            transactional_dispatcher=transactional_dispatcher,
            post_commit_bus=post_commit_bus,
        )
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session

    def create(self, *, context: DomainEventContext) -> SqlAlchemyInventoryFoundationUnitOfWork:
        return SqlAlchemyInventoryFoundationUnitOfWork(
            session=self._session_factory(),
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
            context=context,
            tenant_context_service=self._tenant_context_service,
            user_session=self._user_session,
        )


__all__ = [
    "SqlAlchemyInventoryFoundationUnitOfWork",
    "SqlAlchemyInventoryFoundationUnitOfWorkFactory",
]
