from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.common.ids import generate_id
from src.core.shared.events.domain_event_context import DomainEventContext

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from src.core.shared.events.domain_event_publisher import (
        PostCommitEventPublisher,
        TransactionalEventDispatcher,
    )
    from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkBase


def auth_unit_of_work(
    *,
    session: "Session",
    transactional_dispatcher: "TransactionalEventDispatcher | None",
    post_commit_bus: "PostCommitEventPublisher | None",
) -> "SqlAlchemyUnitOfWorkBase":
    """One physical transaction for an Auth/Security mutation: a bare, canonical
    `SqlAlchemyUnitOfWorkBase` wrapping the caller's own already-shared Session (same
    precedent as Project's `delete_project`, Timesheet's own `_persist_timesheet_transition`,
    and TimeEntry's `_time_entry_unit_of_work`) -- every Auth mutation function already holds
    its own repositories directly (`service._user_repo`, `self._role_repo`, etc.), so this
    deliberately does NOT introduce a second, named-accessor UnitOfWork class that would force
    every call site to route through `uow.users`/`uow.roles` instead; it only adds the
    transactional-dispatch/postcommit-publish machinery those repositories were always missing.
    `uow.record_event(...)` stages the typed fact PRECOMMIT; transactional (FAIL_FAST) handlers
    run inside `uow.commit()` before the physical `session.commit()`, and postcommit delivery
    happens only after that commit actually succeeds. Fails loudly (no degraded fallback) if
    either dependency is missing -- every real Auth service construction site wires both."""
    if transactional_dispatcher is None or post_commit_bus is None:
        raise RuntimeError(
            "Auth service is missing its transactional dispatcher / post-commit bus -- "
            "durable Auth/Security mutations require both to be wired; there is no "
            "degraded fallback."
        )
    from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkBase

    return SqlAlchemyUnitOfWorkBase(
        session=session,
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
        context=DomainEventContext(correlation_id=generate_id()),
    )


__all__ = ["auth_unit_of_work"]
