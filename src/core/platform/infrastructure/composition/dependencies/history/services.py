"""Build shared Platform audit and activity services."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.platform.application.history.activity import ActivityService
from src.core.platform.application.history.audit import EnterpriseAuditService
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.persistence.read.history.activity_actor_reader import (
    SqlAlchemyActivityActorReader,
)
from src.infra.composition.persistence.repositories import RepositoryBundle


def build_enterprise_audit_service(
    *,
    session: Session,
    repositories: RepositoryBundle,
    user_session: UserSessionContext,
    tenant_context_service: TenantContextService,
) -> EnterpriseAuditService:
    return EnterpriseAuditService(
        session=session,
        audit_repo=repositories.audit_entry_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )


def build_activity_service(
    *,
    session: Session,
    repositories: RepositoryBundle,
    user_session: UserSessionContext,
    tenant_context_service: TenantContextService,
) -> ActivityService:
    return ActivityService(
        session=session,
        activity_repo=repositories.activity_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        actor_reader=SqlAlchemyActivityActorReader(session),
    )
