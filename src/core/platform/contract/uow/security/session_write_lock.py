from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Protocol

from sqlalchemy.orm import Session


class SessionWriteLock(Protocol):
    def for_session(self, session: Session) -> AbstractContextManager: ...
