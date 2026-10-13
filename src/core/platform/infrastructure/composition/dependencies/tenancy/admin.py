"""Build Platform tenant administration on the shared session."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.platform.application.tenant.tenancy import TenantAdminService
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.composition.dependencies.repositories import (
    PlatformRepositories,
)


def build_tenant_admin_service(
    *,
    session: Session,
    repositories: PlatformRepositories,
    user_session: UserSessionContext,
) -> TenantAdminService:
    return TenantAdminService(
        session=session,
        tenant_repo=repositories.tenant_repo,
        user_tenant_repo=repositories.user_tenant_repo,
        user_session=user_session,
        platform_event_repo=repositories.platform_event_repo,
    )
