"""Assemble the Platform authentication service and session hooks."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.platform.application.history.audit import EnterpriseAuditService
from src.core.platform.application.security.auth import AuthService
from src.core.platform.application.tenant.tenancy import (
    TenancyMode,
    TenantContextService,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.composition.dependencies.repositories import (
    PlatformRepositories,
)
from src.core.platform.infrastructure.persistence.read.overview.platform_overview_rollup_reader import (
    SqlAlchemyPlatformOverviewRollupReader,
)
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.platform.operational_support import current_trace_id
from src.infra.platform.security_config import RuntimeSecurityConfiguration


def build_auth_service(
    *,
    session: Session,
    repositories: PlatformRepositories,
    user_session: UserSessionContext,
    tenant_context_service: TenantContextService,
    enterprise_audit_service: EnterpriseAuditService,
    overview_rollup_reader: SqlAlchemyPlatformOverviewRollupReader,
    security_configuration: RuntimeSecurityConfiguration,
    transactional_dispatcher: InProcessTransactionalEventDispatcher,
    post_commit_bus: InProcessPostCommitEventBus,
) -> AuthService:
    auth_service = AuthService(
        session=session,
        user_repo=repositories.user_repo,
        role_repo=repositories.role_repo,
        permission_repo=repositories.permission_repo,
        role_permission_repo=repositories.role_permission_repo,
        auth_session_repo=repositories.auth_session_repo,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        security_audit_repo=repositories.audit_entry_repo,
        user_tenant_repo=repositories.user_tenant_repo,
        tenant_context_service=tenant_context_service,
        request_id_provider=current_trace_id,
        role_binding_repo=repositories.role_binding_repo,
        overview_rollup_reader=overview_rollup_reader,
        canonical_scope_tenant_resolvers={
            "organization": lambda tenant_id, organization_id: (
                repositories.organization_repo.get_for_tenant(organization_id, tenant_id)
                is not None
            ),
            "site": lambda tenant_id, site_id: (
                tenant_context_service.require_active_tenant_id(
                    operation_label="validate site access scope"
                )
                == tenant_id
                and repositories.site_repo.get(site_id) is not None
            ),
        },
        allow_platform_customer_context=(
            security_configuration.tenancy_mode is TenancyMode.LOCAL_SINGLE_TENANT
        ),
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
    )
    tenant_context_service.set_principal_rebuilder(
        auth_service.rebuild_current_principal_for_context
    )
    tenant_context_service.set_context_switch_committer(auth_service.commit_context_switch)
    user_session.set_validator(auth_service.validate_session_principal)
    user_session.set_context_listener(auth_service.persist_session_context)
    if security_configuration.tenancy_mode is TenancyMode.LOCAL_SINGLE_TENANT:
        auth_service.bootstrap_defaults()
    else:
        auth_service.bootstrap_policy_catalog()
    return auth_service
