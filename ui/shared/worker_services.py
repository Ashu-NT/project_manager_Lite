from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from core.services.auth.session import UserSessionContext
from infra.db.base import SessionLocal
from infra.services import build_service_dict


def _copy_principal(
    source: UserSessionContext | None,
    target: UserSessionContext | None,
) -> None:
    if source is None or target is None:
        return
    principal = source.principal
    if principal is None:
        target.clear()
        return
    target.set_principal(principal)


@contextmanager
def worker_service_scope(user_session: UserSessionContext | None = None):
    session = SessionLocal()
    try:
        services: dict[str, Any] = build_service_dict(session)
        _copy_principal(user_session, services.get("user_session"))
        yield services
    finally:
        session.close()


__all__ = ["worker_service_scope"]
