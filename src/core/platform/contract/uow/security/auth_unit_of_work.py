from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session

from src.core.shared.events.domain_event_publisher import (
    PostCommitEventPublisher,
    TransactionalEventDispatcher,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork


class AuthUnitOfWorkFactory(Protocol):
    def create(
        self,
        *,
        session: Session,
        transactional_dispatcher: TransactionalEventDispatcher | None,
        post_commit_bus: PostCommitEventPublisher | None,
    ) -> UnitOfWork: ...
