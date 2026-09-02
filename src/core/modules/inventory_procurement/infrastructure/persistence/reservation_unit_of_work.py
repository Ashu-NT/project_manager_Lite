from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from src.core.modules.inventory_procurement.application.catalog import ItemMasterService
from src.core.modules.inventory_procurement.application.inventory.service import InventoryService
from src.core.modules.inventory_procurement.application.inventory.stock_control_service import (
    StockControlService,
)
from src.core.modules.inventory_procurement.contracts.persistence.reservation_unit_of_work import (
    InventoryReservationUnitOfWork,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.inventory import (
    SqlAlchemyStockBalanceRepository,
    SqlAlchemyStockReservationRepository,
    SqlAlchemyStockTransactionRepository,
)
from src.core.platform.application.history.activity.activity_service import ActivityService
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.contract.repositories.master_data.org.contracts import OrganizationRepository
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


class SqlAlchemyInventoryReservationUnitOfWork(
    SqlAlchemyUnitOfWorkBase, InventoryReservationUnitOfWork
):
    def __init__(
        self,
        *,
        session: Session,
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
        context: DomainEventContext,
        organization_repo: OrganizationRepository,
        item_service: ItemMasterService,
        inventory_service: InventoryService,
        tenant_context_service,
        user_session,
    ) -> None:
        super().__init__(
            session=session,
            transactional_dispatcher=transactional_dispatcher,
            post_commit_bus=post_commit_bus,
            context=context,
        )
        self.reservations = SqlAlchemyStockReservationRepository(
            session, tenant_context_service=tenant_context_service
        )
        self.balances = SqlAlchemyStockBalanceRepository(
            session, tenant_context_service=tenant_context_service
        )
        self.stock_transactions = SqlAlchemyStockTransactionRepository(
            session, tenant_context_service=tenant_context_service
        )

        self.stock_service = StockControlService(
            session,
            self.balances,
            self.stock_transactions,
            organization_repo=organization_repo,
            item_service=item_service,
            inventory_service=inventory_service,
            tenant_context_service=tenant_context_service,
            user_session=user_session,
        )

        audit_repo = SqlAlchemyAuditRepository(session)
        audit_repo._tenant_context_service = tenant_context_service
        self._enterprise_audit_service = EnterpriseAuditService(
            session=session,
            audit_repo=audit_repo,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
        )
        activity_repo = SqlAlchemyActivityRepository(session)
        activity_repo._tenant_context_service = tenant_context_service
        self._activity_service = ActivityService(
            session=session,
            activity_repo=activity_repo,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
        )


class SqlAlchemyInventoryReservationUnitOfWorkFactory(SqlAlchemyUnitOfWorkFactoryBase):
    """Closes over a session *factory* -- every `create()` call opens a genuinely fresh
    `Session`, matching every other Platform/module canonical UoW factory's own convention."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
        organization_repo: OrganizationRepository,
        item_service: ItemMasterService,
        inventory_service: InventoryService,
        tenant_context_service,
        user_session,
    ) -> None:
        super().__init__(
            session_factory=session_factory,
            transactional_dispatcher=transactional_dispatcher,
            post_commit_bus=post_commit_bus,
        )
        self._organization_repo = organization_repo
        self._item_service = item_service
        self._inventory_service = inventory_service
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session

    def create(self, *, context: DomainEventContext) -> SqlAlchemyInventoryReservationUnitOfWork:
        return SqlAlchemyInventoryReservationUnitOfWork(
            session=self._session_factory(),
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
            context=context,
            organization_repo=self._organization_repo,
            item_service=self._item_service,
            inventory_service=self._inventory_service,
            tenant_context_service=self._tenant_context_service,
            user_session=self._user_session,
        )


__all__ = [
    "SqlAlchemyInventoryReservationUnitOfWork",
    "SqlAlchemyInventoryReservationUnitOfWorkFactory",
]
