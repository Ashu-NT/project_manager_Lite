from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.core.platform.infrastructure.persistence.uow.security.auth_unit_of_work import (
    SqlAlchemyAuthUnitOfWorkFactory,
)


def test_auth_uow_factory_requires_both_event_dependencies() -> None:
    factory = SqlAlchemyAuthUnitOfWorkFactory()
    session = Mock()
    for dispatcher, bus in ((None, Mock()), (Mock(), None)):
        with pytest.raises(RuntimeError, match="there is no degraded fallback"):
            factory.create(
                session=session,
                transactional_dispatcher=dispatcher,
                post_commit_bus=bus,
            )


def test_auth_uow_factory_reuses_caller_session() -> None:
    session = Mock()
    uow = SqlAlchemyAuthUnitOfWorkFactory().create(
        session=session,
        transactional_dispatcher=Mock(),
        post_commit_bus=Mock(),
    )
    assert uow._session is session
    assert uow.context.correlation_id
