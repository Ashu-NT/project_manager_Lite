"""Build the shared Platform session and tenant context."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.core.platform.application.tenant.tenancy import (
    TenantContextService,
    build_tenant_context_policy,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.infra.composition.persistence.repositories import RepositoryBundle
from src.infra.platform.operational_support import current_trace_id
from src.infra.platform.security_audit_recorder import DurableSecurityDenialRecorder
from src.infra.platform.security_config import RuntimeSecurityConfiguration


@dataclass(frozen=True)
class TenancyDependencies:
    user_session: UserSessionContext
    tenant_context_service: TenantContextService


def build_tenancy_dependencies(
    *,
    session: Session,
    repositories: RepositoryBundle,
    security_configuration: RuntimeSecurityConfiguration,
) -> TenancyDependencies:
    user_session = UserSessionContext()
    denial_recorder = DurableSecurityDenialRecorder.for_session(
        session,
        trace_id_provider=current_trace_id,
    )
    user_session.set_security_denial_listener(denial_recorder.record)
    tenant_context_service = TenantContextService(
        tenant_repo=repositories.tenant_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        user_tenant_repo=repositories.user_tenant_repo,
        context_policy=build_tenant_context_policy(security_configuration.tenancy_mode),
    )
    for field_name in repositories.__dataclass_fields__:
        repo = getattr(repositories, field_name)
        if hasattr(repo, "_tenant_context_service"):
            repo._tenant_context_service = tenant_context_service
    return TenancyDependencies(
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
