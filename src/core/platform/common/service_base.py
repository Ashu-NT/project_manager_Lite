from __future__ import annotations

from sqlalchemy.orm import Session


class ServiceBase:
    def __init__(self, session: Session):
        self._session: Session = session

    def commit(self):
        try:
            self._session.commit()
        except Exception as exc:
            self._session.rollback()
            raise exc


__all__ = ["ServiceBase"]
