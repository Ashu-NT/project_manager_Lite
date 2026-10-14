from __future__ import annotations

from sqlalchemy.orm import Session


class ServiceBase:
    def __init__(self, session: Session):
        self._session: Session = session

    def commit(self) -> None:
        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise


__all__ = ["ServiceBase"]
