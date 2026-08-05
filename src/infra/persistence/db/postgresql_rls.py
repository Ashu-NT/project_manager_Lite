from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator

from sqlalchemy import event, text
from sqlalchemy.orm import Session

from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.common.exceptions import BusinessRuleError


@dataclass(frozen=True)
class WorkerTenantScope:
    tenant_id: str
    organization_id: str | None = None
    actor_user_id: str | None = None

    def __post_init__(self) -> None:
        if not str(self.tenant_id or "").strip():
            raise ValueError("Worker tenant scope requires tenant_id.")


_WORKER_SCOPE: ContextVar[WorkerTenantScope | None] = ContextVar(
    "pm_worker_tenant_scope",
    default=None,
)


@contextmanager
def worker_tenant_scope(
    *,
    tenant_id: str,
    organization_id: str | None = None,
    actor_user_id: str | None = None,
) -> Iterator[WorkerTenantScope]:
    """Install scope only after a worker has revalidated its execution payload."""
    scope = WorkerTenantScope(
        tenant_id=str(tenant_id or "").strip(),
        organization_id=str(organization_id or "").strip() or None,
        actor_user_id=str(actor_user_id or "").strip() or None,
    )
    token = _WORKER_SCOPE.set(scope)
    try:
        yield scope
    finally:
        _WORKER_SCOPE.reset(token)


def configure_session_rls_context(
    session: Session,
    *,
    user_session: UserSessionContext,
) -> None:
    """Set verified request/worker identity at every PostgreSQL transaction start."""
    if session.info.get("pm_rls_context_configured"):
        return

    def _after_begin(_session: Session, _transaction, connection) -> None:
        if connection.dialect.name != "postgresql":
            return
        tenant_id, organization_id, user_id = _resolve_context(user_session)
        connection.execute(
            text(
                "SELECT "
                "set_config('app.tenant_id', :tenant_id, true), "
                "set_config('app.organization_id', :organization_id, true), "
                "set_config('app.user_id', :user_id, true)"
            ),
            {
                "tenant_id": tenant_id or "",
                "organization_id": organization_id or "",
                "user_id": user_id or "",
            },
        )

    event.listen(session, "after_begin", _after_begin)
    session.info["pm_rls_context_configured"] = True
    session.info["pm_rls_context_listener"] = _after_begin


def validate_postgresql_execution_role(session: Session) -> None:
    bind = session.get_bind()
    if bind.dialect.name != "postgresql":
        return
    with bind.connect() as connection:
        row = connection.execute(
            text(
                "SELECT rolsuper, rolbypassrls "
                "FROM pg_roles WHERE rolname = current_user"
            )
        ).one()
        if bool(row.rolsuper) or bool(row.rolbypassrls):
            raise BusinessRuleError(
                "The application database role must not be superuser or BYPASSRLS.",
                code="POSTGRES_RLS_ROLE_UNSAFE",
            )


def _resolve_context(
    user_session: UserSessionContext,
) -> tuple[str | None, str | None, str | None]:
    worker_scope = _WORKER_SCOPE.get()
    if worker_scope is not None:
        return (
            worker_scope.tenant_id,
            worker_scope.organization_id,
            worker_scope.actor_user_id,
        )
    principal = user_session.principal
    return (
        user_session.stored_active_tenant_id(),
        user_session.stored_active_organization_id(),
        str(getattr(principal, "user_id", "") or "").strip() or None,
    )


__all__ = [
    "WorkerTenantScope",
    "configure_session_rls_context",
    "validate_postgresql_execution_role",
    "worker_tenant_scope",
]
