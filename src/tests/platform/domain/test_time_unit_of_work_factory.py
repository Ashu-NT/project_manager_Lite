from __future__ import annotations

from unittest.mock import Mock

from src.core.platform.infrastructure.persistence.uow.time_unit_of_work import (
    SqlAlchemyTimeUnitOfWorkFactory,
)
from src.core.shared.events.domain_event_context import DomainEventContext


def test_time_uow_factory_reuses_session_and_preserves_operation_context() -> None:
    session = Mock()
    context = DomainEventContext(correlation_id="time-operation-1")
    uow = SqlAlchemyTimeUnitOfWorkFactory().create(
        session=session,
        transactional_dispatcher=Mock(),
        post_commit_bus=Mock(),
        context=context,
    )

    assert uow._session is session
    assert uow.context.correlation_id == "time-operation-1"
    assert uow.context is not context
