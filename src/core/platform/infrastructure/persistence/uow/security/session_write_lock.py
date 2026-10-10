from __future__ import annotations

from contextlib import AbstractContextManager

from sqlalchemy.orm import Session

from src.infra.persistence.db.unit_of_work import sqlite_write_lock


class SqlAlchemySessionWriteLock:
    def for_session(self, session: Session) -> AbstractContextManager:
        return sqlite_write_lock(session)
