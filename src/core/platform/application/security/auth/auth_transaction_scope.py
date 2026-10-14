from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from src.core.platform.contract.uow.security.auth_unit_of_work import (
    AuthUnitOfWorkFactory,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork

if TYPE_CHECKING:
    from src.core.platform.application.tenant.tenancy.tenant_context import (
        TenantContextService,
    )
    from src.core.shared.events.domain_event_publisher import (
        PostCommitEventPublisher,
        TransactionalEventDispatcher,
    )


class AuthTransactionScope:
    """One Auth operation's transaction: a UoW over the shared Session with the
    Platform dispatchers, plus the tenant id stamped on Auth domain events."""

    def __init__(
        self,
        *,
        session: Session,
        uow_factory: AuthUnitOfWorkFactory,
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
        tenant_context_service: TenantContextService | None,
    ) -> None:
        self._session = session
        self._uow_factory = uow_factory
        self._transactional_dispatcher = transactional_dispatcher
        self._post_commit_bus = post_commit_bus
        self._tenant_context_service = tenant_context_service

    @property
    def session(self) -> Session:
        return self._session

    def uow(self) -> UnitOfWork:
        return self._uow_factory.create(
            session=self._session,
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
        )

    def active_tenant_id_for_event(self) -> str | None:
        if self._tenant_context_service is None:
            return None
        return str(self._tenant_context_service.get_active_tenant_id() or "").strip() or None


__all__ = ["AuthTransactionScope"]
