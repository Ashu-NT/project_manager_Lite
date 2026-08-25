"""Shared fixtures for SqlAlchemyUnitOfWorkBase tests.

Uses a real, file-backed SQLite database (not `sqlite:///:memory:`) specifically so that
multiple `Session` objects genuinely share one persistent database with standard,
well-understood per-connection transaction isolation -- in-memory SQLite's default
single-connection pooling behavior would make "two independent sessions" and "genuine
transaction isolation between them" ambiguous to prove.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.infra.events.in_process_post_commit_event_bus import InProcessPostCommitEventBus
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkFactoryBase


@pytest.fixture()
def session_factory(tmp_path) -> Callable[[], Session]:
    engine = create_engine(f"sqlite:///{tmp_path}/uow_test.db", future=True)
    return sessionmaker(bind=engine, future=True)


@pytest.fixture()
def transactional_dispatcher() -> InProcessTransactionalEventDispatcher:
    return InProcessTransactionalEventDispatcher()


@pytest.fixture()
def post_commit_bus() -> InProcessPostCommitEventBus:
    return InProcessPostCommitEventBus()


@pytest.fixture()
def uow_factory(session_factory, transactional_dispatcher, post_commit_bus) -> SqlAlchemyUnitOfWorkFactoryBase:
    return SqlAlchemyUnitOfWorkFactoryBase(
        session_factory=session_factory,
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
    )
