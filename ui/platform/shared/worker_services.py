from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from core.platform.auth.session import UserSessionContext
from infra.platform.db.base import SessionLocal
from src.infra.composition.app_container import build_service_dict


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


def service_uses_in_memory_sqlite(service: object) -> bool:
    session = getattr(service, "_session", None)
    if session is None:
        return False
    try:
        bind = session.get_bind()
    except Exception:
        return False
    url = getattr(bind, "url", None)
    if url is None:
        return False
    drivername = str(getattr(url, "drivername", "") or "")
    database = str(getattr(url, "database", "") or "")
    return drivername.startswith("sqlite") and database == ":memory:"


__all__ = ["service_uses_in_memory_sqlite", "worker_service_scope"]
