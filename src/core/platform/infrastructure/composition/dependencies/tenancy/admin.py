"""Build tenant catalog queries and lifecycle commands on the shared session."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.core.platform.application.tenant.tenancy import (
    TenantAdminQueryHandler,
    TenantLifecycleCommandHandler,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.composition.dependencies.repositories import (
    PlatformRepositories,
)


@dataclass(frozen=True)
class TenantAdminDependencies:
    tenant_admin_queries: TenantAdminQueryHandler
    tenant_lifecycle_commands: TenantLifecycleCommandHandler


def build_tenant_admin_dependencies(
    *,
    session: Session,
    repositories: PlatformRepositories,
    user_session: UserSessionContext,
) -> TenantAdminDependencies:
    queries = TenantAdminQueryHandler(
        tenant_repo=repositories.tenant_repo,
        user_tenant_repo=repositories.user_tenant_repo,
        user_session=user_session,
    )
    commands = TenantLifecycleCommandHandler(
        session=session,
        tenant_repo=repositories.tenant_repo,
        tenant_queries=queries,
        user_session=user_session,
        platform_event_repo=repositories.platform_event_repo,
    )
    return TenantAdminDependencies(
        tenant_admin_queries=queries,
        tenant_lifecycle_commands=commands,
    )
