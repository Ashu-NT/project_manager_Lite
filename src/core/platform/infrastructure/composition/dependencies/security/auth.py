"""Assemble the Platform Auth handlers and session hooks."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.core.platform.application.security.auth import (
    AuthBootstrapHandler,
    AuthenticationHandler,
    AuthQueryHandler,
    AuthSessionCommandHandler,
    AuthSessionQueryHandler,
    AuthTransactionScope,
    AuthValidationPolicy,
    ContextSwitchCommandHandler,
    FederatedIdentityCommandHandler,
    MfaCommandHandler,
    PasswordCommandHandler,
    PlatformOwnerProvisioningHandler,
    UserAdministrationCommandHandler,
    UserDirectoryQueryHandler,
    UserRegistrationHandler,
)
from src.core.platform.application.security.auth.audit.security_audit import (
    SecurityAuditRecorder,
)
from src.core.platform.application.security.auth.credentials.authentication_transactions import (
    AuthenticationTransactions,
)
from src.core.platform.application.security.auth.provisioning.default_seed_service import (
    AuthPolicySeeder,
)
from src.core.platform.application.security.auth.session.principal_builder import (
    PrincipalBuilder,
)
from src.core.platform.application.security.auth.session.session_lifecycle import (
    AuthSessionLifecycle,
)
from src.core.platform.application.security.authorization.enforcement.sod_enforcer import (
    SeparationOfDutiesEnforcer,
)
from src.core.platform.application.security.authorization.enforcement.target_user_authorization import (
    TargetUserAuthorization,
)
from src.core.platform.application.security.authorization.roles.canonical_role_resolver import (
    CanonicalRoleResolver,
    ScopeTenantResolver,
)
from src.core.platform.application.tenant.tenancy import (
    TenancyMode,
    TenantContextService,
)
from src.core.platform.contract.repositories.security.auth import (
    PermissionRepository,
    RoleBindingRepository,
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.domain.security.authorization.enforcement.sod import (
    SeparationOfDutiesPolicy,
)
from src.core.platform.infrastructure.composition.dependencies.repositories import (
    PlatformRepositories,
)
from src.core.platform.infrastructure.persistence.read.overview.platform_overview_rollup_reader import (
    SqlAlchemyPlatformOverviewRollupReader,
)
from src.core.platform.infrastructure.persistence.uow.security.auth_unit_of_work import (
    SqlAlchemyAuthUnitOfWorkFactory,
)
from src.core.platform.infrastructure.persistence.uow.security.session_write_lock import (
    SqlAlchemySessionWriteLock,
)
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.platform.operational_support import current_trace_id
from src.infra.platform.security_config import RuntimeSecurityConfiguration
from src.infra.time.system_clock import SystemClock


def build_auth_query_handler(
    *,
    user_repo: UserRepository,
    role_repo: RoleRepository,
    permission_repo: PermissionRepository,
    role_permission_repo: RolePermissionRepository,
    role_binding_repo: RoleBindingRepository | None,
    tenant_context_service: TenantContextService | None = None,
    canonical_scope_tenant_resolvers: Mapping[str, ScopeTenantResolver] | None = None,
    allow_platform_customer_context: bool = False,
) -> AuthQueryHandler:
    """Canonical role-binding authority is only available when role-binding persistence is
    wired; without it the handler raises AUTHORIZATION_CANONICAL_REPOSITORY_REQUIRED on use."""
    canonical_role_resolver = (
        CanonicalRoleResolver(
            role_binding_repo=role_binding_repo,
            role_repo=role_repo,
            role_permission_repo=role_permission_repo,
            permission_repo=permission_repo,
            scope_tenant_resolvers=(canonical_scope_tenant_resolvers or {}),
            allow_platform_customer_context=bool(allow_platform_customer_context),
        )
        if role_binding_repo is not None
        else None
    )
    return AuthQueryHandler(
        user_repo=user_repo,
        role_repo=role_repo,
        canonical_role_resolver=canonical_role_resolver,
        tenant_context_service=tenant_context_service,
    )


@dataclass(frozen=True)
class AuthComposition:
    """Session-scoped Auth handlers, plus the shared collaborators that other
    Platform compositions reuse so each exists exactly once."""

    queries: AuthQueryHandler
    authentication: AuthenticationHandler
    passwords: PasswordCommandHandler
    mfa: MfaCommandHandler
    federated_identities: FederatedIdentityCommandHandler
    registration: UserRegistrationHandler
    user_administration: UserAdministrationCommandHandler
    user_directory: UserDirectoryQueryHandler
    session_commands: AuthSessionCommandHandler
    session_queries: AuthSessionQueryHandler
    context_switch: ContextSwitchCommandHandler
    bootstrap: AuthBootstrapHandler
    platform_owner: PlatformOwnerProvisioningHandler
    principals: PrincipalBuilder
    session_lifecycle: AuthSessionLifecycle
    target_users: TargetUserAuthorization


def build_auth_capabilities(
    *,
    session: Session,
    repositories: PlatformRepositories,
    user_session: UserSessionContext,
    tenant_context_service: TenantContextService,
    overview_rollup_reader: SqlAlchemyPlatformOverviewRollupReader,
    security_configuration: RuntimeSecurityConfiguration,
    transactional_dispatcher: InProcessTransactionalEventDispatcher,
    post_commit_bus: InProcessPostCommitEventBus,
) -> AuthComposition:
    """Runtime Auth: builds the handlers, installs the session/context hooks
    and bootstraps the policy catalog for the configured tenancy mode."""
    local_single_tenant = security_configuration.tenancy_mode is TenancyMode.LOCAL_SINGLE_TENANT
    auth = build_auth_handlers(
        session=session,
        repositories=repositories,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        overview_rollup_reader=overview_rollup_reader,
        allow_platform_customer_context=local_single_tenant,
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
    )
    tenant_context_service.set_principal_rebuilder(auth.session_lifecycle.rebuild_current_for_context)
    tenant_context_service.set_context_switch_committer(auth.context_switch.commit_context_switch)
    user_session.set_validator(auth.session_commands.validate_session_principal)
    user_session.set_context_listener(auth.session_commands.persist_session_context)
    if local_single_tenant:
        auth.bootstrap.bootstrap_defaults()
    else:
        auth.bootstrap.bootstrap_policy_catalog()
    return auth


def build_auth_handlers(
    *,
    session: Session,
    repositories: PlatformRepositories,
    transactional_dispatcher: InProcessTransactionalEventDispatcher,
    post_commit_bus: InProcessPostCommitEventBus,
    user_session: UserSessionContext | None = None,
    tenant_context_service: TenantContextService | None = None,
    overview_rollup_reader: SqlAlchemyPlatformOverviewRollupReader | None = None,
    allow_platform_customer_context: bool = False,
) -> AuthComposition:
    """Side-effect-free construction of the Auth handler graph over one Session."""
    auth_queries = build_auth_query_handler(
        user_repo=repositories.user_repo,
        role_repo=repositories.role_repo,
        permission_repo=repositories.permission_repo,
        role_permission_repo=repositories.role_permission_repo,
        role_binding_repo=repositories.role_binding_repo,
        tenant_context_service=tenant_context_service,
        canonical_scope_tenant_resolvers={
            "organization": lambda tenant_id, organization_id: (
                repositories.organization_repo.get_for_tenant(organization_id, tenant_id)
                is not None
            ),
            "site": lambda tenant_id, site_id: (
                tenant_context_service is not None
                and tenant_context_service.require_active_tenant_id(
                    operation_label="validate site access scope"
                )
                == tenant_id
                and repositories.site_repo.get(site_id) is not None
            ),
        },
        allow_platform_customer_context=allow_platform_customer_context,
    )
    user_repo = repositories.user_repo
    role_repo = repositories.role_repo
    auth_session_repo = repositories.auth_session_repo
    security_audit_repo = repositories.audit_entry_repo
    clock = SystemClock()
    validation_policy = AuthValidationPolicy()
    tx = AuthTransactionScope(
        session=session,
        uow_factory=SqlAlchemyAuthUnitOfWorkFactory(),
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
        tenant_context_service=tenant_context_service,
    )
    target_users = TargetUserAuthorization(
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        user_tenant_repo=repositories.user_tenant_repo,
    )
    audit = SecurityAuditRecorder(
        security_audit_repo=security_audit_repo,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
        target_users=target_users,
    )
    principals = PrincipalBuilder(
        auth_queries=auth_queries,
        auth_session_repo=auth_session_repo,
        tenant_context_service=tenant_context_service,
        allow_platform_customer_context=allow_platform_customer_context,
    )
    lifecycle = AuthSessionLifecycle(
        user_repo=user_repo,
        auth_session_repo=auth_session_repo,
        user_session=user_session,
        principals=principals,
    )
    seeder = AuthPolicySeeder(
        session=session,
        role_repo=role_repo,
        permission_repo=repositories.permission_repo,
        role_permission_repo=repositories.role_permission_repo,
    )
    registration = UserRegistrationHandler(
        tx=tx,
        clock=clock,
        auth_queries=auth_queries,
        user_repo=user_repo,
        role_repo=role_repo,
        role_binding_repo=repositories.role_binding_repo,
        security_audit_repo=security_audit_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        user_tenant_repo=repositories.user_tenant_repo,
        validation_policy=validation_policy,
        audit=audit,
        sod=SeparationOfDutiesEnforcer(
            auth_queries=auth_queries,
            sod_policy=SeparationOfDutiesPolicy(),
            user_session=user_session,
        ),
        target_users=target_users,
    )
    session_commands = AuthSessionCommandHandler(
        tx=tx,
        auth_queries=auth_queries,
        user_repo=user_repo,
        auth_session_repo=auth_session_repo,
        user_session=user_session,
        target_users=target_users,
        audit=audit,
        lifecycle=lifecycle,
        principals=principals,
    )
    context_switch = ContextSwitchCommandHandler(
        session=session,
        auth_session_repo=auth_session_repo,
        request_id_provider=current_trace_id,
        security_audit_repo=security_audit_repo,
        session_write_lock=SqlAlchemySessionWriteLock(),
        user_session=user_session,
    )
    bootstrap = AuthBootstrapHandler(
        tx=tx,
        clock=clock,
        user_repo=user_repo,
        role_binding_repo=repositories.role_binding_repo,
        security_audit_repo=security_audit_repo,
        seeder=seeder,
        registration=registration,
    )
    capabilities = AuthComposition(
        queries=auth_queries,
        authentication=AuthenticationHandler(
            user_repo=user_repo,
            transactions=AuthenticationTransactions(
                tx=tx,
                user_repo=user_repo,
                auth_session_repo=auth_session_repo,
                user_session=user_session,
                tenant_context_service=tenant_context_service,
                principals=principals,
                lifecycle=lifecycle,
                audit=audit,
            ),
        ),
        passwords=PasswordCommandHandler(
            tx=tx,
            auth_queries=auth_queries,
            user_repo=user_repo,
            user_session=user_session,
            validation_policy=validation_policy,
            target_users=target_users,
            audit=audit,
            lifecycle=lifecycle,
        ),
        mfa=MfaCommandHandler(
            tx=tx,
            auth_queries=auth_queries,
            user_repo=user_repo,
            user_session=user_session,
            target_users=target_users,
            audit=audit,
            lifecycle=lifecycle,
        ),
        federated_identities=FederatedIdentityCommandHandler(
            tx=tx,
            auth_queries=auth_queries,
            user_repo=user_repo,
            user_session=user_session,
            target_users=target_users,
            audit=audit,
            lifecycle=lifecycle,
        ),
        registration=registration,
        user_administration=UserAdministrationCommandHandler(
            tx=tx,
            auth_queries=auth_queries,
            user_repo=user_repo,
            user_session=user_session,
            target_users=target_users,
            audit=audit,
            lifecycle=lifecycle,
        ),
        user_directory=UserDirectoryQueryHandler(
            auth_queries=auth_queries,
            user_repo=user_repo,
            role_repo=role_repo,
            user_session=user_session,
            overview_rollup_reader=overview_rollup_reader,
            target_users=target_users,
        ),
        session_commands=session_commands,
        session_queries=AuthSessionQueryHandler(
            auth_queries=auth_queries,
            auth_session_repo=auth_session_repo,
            user_session=user_session,
            target_users=target_users,
        ),
        context_switch=context_switch,
        bootstrap=bootstrap,
        platform_owner=PlatformOwnerProvisioningHandler(
            session=session,
            user_repo=user_repo,
            permission_repo=repositories.permission_repo,
            role_permission_repo=repositories.role_permission_repo,
            role_binding_repo=repositories.role_binding_repo,
            validation_policy=validation_policy,
            seeder=seeder,
        ),
        principals=principals,
        session_lifecycle=lifecycle,
        target_users=target_users,
    )
    return capabilities


__all__ = [
    "AuthComposition",
    "build_auth_capabilities",
    "build_auth_handlers",
    "build_auth_query_handler",
]
