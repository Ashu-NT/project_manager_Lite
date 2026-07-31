from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from inspect import signature

import pytest

from src.core.platform.auth import AuthService
from src.core.platform.auth.domain import (
    ROLE_SCOPE_PLATFORM,
    RoleBinding,
    UserAccount,
)
from src.core.platform.auth.domain.session import UserSessionContext
from src.core.platform.auth.passwords import hash_password
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.infrastructure.persistence.orm.access import (
    ScopedAccessGrantORM,
)
from src.core.platform.infrastructure.persistence.repositories.org import (
    SqlAlchemyOrganizationRepository,
)
from src.core.platform.org.domain import Organization
from src.core.platform.tenancy.domain.tenant import Tenant
from src.core.platform.tenancy.domain.user_tenant_membership import (
    UserTenantMembership,
)


def _customer_auth_service(
    services,
    *,
    username: str,
) -> tuple[AuthService, object, str]:
    auth = services["auth_service"]
    tenant_id = services["tenant_context_service"].get_active_tenant_id()
    organization_id = (
        services["tenant_context_service"].get_active_organization_id()
    )
    assert tenant_id is not None
    actor = auth.register_user(
        username,
        "StrongPass123!",
        role_names=["tenant_admin"],
        tenant_id=tenant_id,
    )
    principal = auth.build_principal_for_context(
        actor,
        tenant_id=tenant_id,
        organization_id=organization_id,
    )
    context = UserSessionContext()
    context.set_principal(principal)
    return (
        AuthService(
            session=services["session"],
            user_repo=auth._user_repo,
            role_repo=auth._role_repo,
            permission_repo=auth._permission_repo,
            role_permission_repo=auth._role_permission_repo,
            role_binding_repo=auth._role_binding_repo,
            auth_session_repo=auth._auth_session_repo,
            scoped_access_repo=auth._scoped_access_repo,
            project_membership_repo=auth._project_membership_repo,
            user_session=context,
            security_audit_repo=auth._security_audit_repo,
            user_tenant_repo=auth._user_tenant_repo,
            tenant_context_service=services["tenant_context_service"],
        ),
        actor,
        tenant_id,
    )


def _cross_tenant_user(services, *, username: str):
    auth = services["auth_service"]
    tenant = Tenant.create(
        tenant_code=f"X-{username}",
        display_name=f"Cross {username}",
    )
    services["tenant_admin_service"]._tenant_repo.add(tenant)
    services["session"].flush()
    user = auth.register_user(
        username,
        "StrongPass123!",
        tenant_id=tenant.id,
    )
    return user


@pytest.mark.parametrize(
    "operation",
    [
        lambda service, user, _session_id: service.force_user_password_reset(
            user.id
        ),
        lambda service, user, _session_id: service.reset_user_password(
            user.id,
            "ChangedPass123!",
        ),
        lambda service, user, _session_id: service.provision_mfa_secret(user.id),
        lambda service, user, _session_id: service.enable_user_mfa(
            user.id,
            "000000",
        ),
        lambda service, user, _session_id: service.disable_user_mfa(user.id),
        lambda service, user, _session_id: service.link_federated_identity(
            user.id,
            identity_provider="oidc",
            federated_subject=f"subject-{user.id}",
        ),
        lambda service, user, _session_id: service.set_user_session_policy(
            user.id,
            session_timeout_minutes_override=30,
        ),
        lambda service, user, _session_id: service.revoke_user_sessions(
            user.id
        ),
        lambda service, user, _session_id: service.list_user_sessions(user.id),
        lambda service, _user, session_id: service.revoke_session(session_id),
    ],
)
def test_customer_admin_sensitive_operations_deny_cross_tenant_target(
    services,
    operation,
) -> None:
    customer_auth, _, _ = _customer_auth_service(
        services,
        username=f"containment-admin-{abs(id(operation))}",
    )
    target = _cross_tenant_user(
        services,
        username=f"containment-target-{abs(id(operation))}",
    )
    authenticated_target = services["auth_service"].authenticate(
        target.username,
        "StrongPass123!",
    )
    assert authenticated_target.active_session_id is not None

    with pytest.raises(
        BusinessRuleError,
        match="outside the active tenant",
    ) as exc_info:
        operation(
            customer_auth,
            target,
            authenticated_target.active_session_id,
        )

    assert exc_info.value.code == "USER_CROSS_TENANT_DENIED"


def test_change_password_rejects_a_different_target_user(services) -> None:
    customer_auth, _, tenant_id = _customer_auth_service(
        services,
        username="containment-self-admin",
    )
    target = services["auth_service"].register_user(
        "containment-self-target",
        "StrongPass123!",
        tenant_id=tenant_id,
    )

    with pytest.raises(BusinessRuleError) as exc_info:
        customer_auth.change_password(
            target.id,
            "StrongPass123!",
            "ChangedPass123!",
        )

    assert exc_info.value.code == "AUTH_SELF_SERVICE_REQUIRED"


def test_sensitive_operation_denies_missing_tenant_context(services) -> None:
    customer_auth, actor, tenant_id = _customer_auth_service(
        services,
        username="containment-no-context-admin",
    )
    target = services["auth_service"].register_user(
        "containment-no-context-target",
        "StrongPass123!",
        tenant_id=tenant_id,
    )
    principal = customer_auth._user_session.principal
    assert principal is not None
    customer_auth._user_session.clear()
    customer_auth._user_session.set_principal(
        replace(
            principal,
            active_tenant_id=None,
            active_organization_id=None,
        )
    )

    with pytest.raises(BusinessRuleError) as exc_info:
        customer_auth.force_user_password_reset(target.id)

    assert actor.id == principal.user_id
    assert exc_info.value.code == "TENANT_CONTEXT_REQUIRED"


def test_registration_has_no_public_permission_bypass() -> None:
    assert "bypass_permission" not in signature(AuthService.register_user).parameters


def test_customer_onboarding_creates_active_membership_and_safe_default_role(
    services,
) -> None:
    customer_auth, _, tenant_id = _customer_auth_service(
        services,
        username="containment-onboarding-admin",
    )

    user = customer_auth.onboard_tenant_user(
        username="containment-onboarded-user",
        raw_password="StrongPass123!",
        display_name="Onboarded User",
    )

    assert customer_auth._user_tenant_repo.is_active_member(user.id, tenant_id)
    assert customer_auth.get_user_role_names(user.id) == {"viewer"}
    assert user.must_change_password is True


def test_customer_user_catalog_is_tenant_scoped_and_hides_platform_users(
    services,
) -> None:
    customer_auth, actor, tenant_id = _customer_auth_service(
        services,
        username="containment-catalog-admin",
    )
    same_tenant_user = services["auth_service"].register_user(
        "containment-catalog-member",
        "StrongPass123!",
        tenant_id=tenant_id,
    )
    platform_support = UserAccount.create(
        username="containment-catalog-support",
        password_hash=hash_password("StrongPass123!"),
    )
    customer_auth._user_repo.add(platform_support)
    services["session"].flush()
    support_role = customer_auth._role_repo.get_by_name("support_admin")
    assert support_role is not None
    customer_auth._role_binding_repo.add(
        RoleBinding.create(
            principal_id=platform_support.id,
            role_id=support_role.id,
            actual_scope_type=ROLE_SCOPE_PLATFORM,
        )
    )
    services["session"].commit()
    cross_tenant_user = _cross_tenant_user(
        services,
        username="containment-catalog-cross",
    )

    listed_user_ids = {user.id for user in customer_auth.list_users()}

    assert actor.id in listed_user_ids
    assert same_tenant_user.id in listed_user_ids
    assert cross_tenant_user.id not in listed_user_ids
    assert platform_support.id not in listed_user_ids
    assert services["user_session"].principal.user_id not in listed_user_ids


def test_customer_role_catalog_excludes_platform_and_explicit_scope_roles(
    services,
) -> None:
    customer_auth, _, _ = _customer_auth_service(
        services,
        username="containment-role-catalog-admin",
    )

    role_names = {
        role.name for role in customer_auth.list_customer_assignable_roles()
    }

    assert "viewer" in role_names
    assert "planner" in role_names
    assert "tenant_admin" in role_names
    assert "admin" not in role_names
    assert "support_admin" not in role_names
    assert "org_admin" not in role_names


@pytest.mark.parametrize(
    ("role_name", "expected_code"),
    [
        ("admin", "PLATFORM_ROLE_ASSIGNMENT_DENIED"),
        ("support_admin", "PLATFORM_ROLE_ASSIGNMENT_DENIED"),
        ("org_admin", "ROLE_SCOPE_REQUIRED"),
    ],
)
def test_customer_role_api_rejects_non_tenant_assignable_roles(
    services,
    role_name: str,
    expected_code: str,
) -> None:
    customer_auth, _, tenant_id = _customer_auth_service(
        services,
        username=f"containment-role-denial-{role_name}",
    )
    target = services["auth_service"].register_user(
        f"containment-role-target-{role_name}",
        "StrongPass123!",
        tenant_id=tenant_id,
    )

    for operation in (
        customer_auth.assign_customer_role,
        customer_auth.revoke_customer_role,
    ):
        with pytest.raises(BusinessRuleError) as exc_info:
            operation(target.id, role_name)
        assert exc_info.value.code == expected_code
    assert role_name not in customer_auth.get_user_role_names(target.id)


def test_customer_onboarding_denies_missing_explicit_tenant_context(
    services,
) -> None:
    customer_auth, _, _ = _customer_auth_service(
        services,
        username="containment-onboarding-no-context",
    )
    principal = customer_auth._user_session.principal
    assert principal is not None
    customer_auth._user_session.clear()
    customer_auth._user_session.set_principal(
        replace(
            principal,
            active_tenant_id=None,
            active_organization_id=None,
        )
    )

    with pytest.raises(BusinessRuleError) as exc_info:
        customer_auth.onboard_tenant_user(
            username="containment-onboarding-denied",
            raw_password="StrongPass123!",
        )

    assert exc_info.value.code == "TENANT_CONTEXT_REQUIRED"
    assert (
        services["auth_service"]._user_repo.get_by_username(
            "containment-onboarding-denied"
        )
        is None
    )


def test_customer_onboarding_denies_missing_context_authorization_service(
    services,
) -> None:
    customer_auth, _, _ = _customer_auth_service(
        services,
        username="containment-onboarding-no-policy",
    )
    customer_auth._tenant_context_service = None

    with pytest.raises(BusinessRuleError) as exc_info:
        customer_auth.onboard_tenant_user(
            username="containment-onboarding-no-policy-target",
            raw_password="StrongPass123!",
        )

    assert exc_info.value.code == "AUTHORIZATION_CONTEXT_REQUIRED"


def test_tenant_switch_rebuilds_only_target_tenant_grants(services) -> None:
    session = services["session"]
    auth = services["auth_service"]
    user_session = services["user_session"]
    tenant_context = services["tenant_context_service"]
    current_tenant_id = tenant_context.get_active_tenant_id()
    current_organization_id = tenant_context.get_active_organization_id()
    assert current_tenant_id is not None

    target_tenant = services["tenant_admin_service"].create_tenant(
        "CONTAIN-SWITCH",
        "Containment Switch",
    )
    target_organization = Organization.create(
        "CONTAIN-SWITCH-ORG",
        "Containment Switch Organization",
        tenant_id=target_tenant.id,
    )
    SqlAlchemyOrganizationRepository(session).add(target_organization)
    now = datetime.now(timezone.utc)
    current_user_id = user_session.principal.user_id
    session.add_all(
        [
            ScopedAccessGrantORM(
                id="containment-grant-current",
                tenant_id=current_tenant_id,
                scope_type="site",
                scope_id="site-current",
                user_id=current_user_id,
                scope_role="viewer",
                permission_codes_json='["site.read"]',
                created_at=now,
            ),
            ScopedAccessGrantORM(
                id="containment-grant-target",
                tenant_id=target_tenant.id,
                scope_type="site",
                scope_id="site-target",
                user_id=current_user_id,
                scope_role="viewer",
                permission_codes_json='["site.read"]',
                created_at=now,
            ),
        ]
    )
    session.flush()
    current_user = auth._require_user(current_user_id)
    user_session.set_principal(
        auth.build_principal_for_context(
            current_user,
            tenant_id=current_tenant_id,
            organization_id=current_organization_id,
            session_id=user_session.principal.session_id,
        )
    )
    assert "site-current" in user_session.principal.scoped_access["site"]

    tenant_context.switch_to_tenant(target_tenant.id)

    switched = user_session.principal
    assert switched is not None
    assert switched.active_tenant_id == target_tenant.id
    assert switched.active_organization_id == target_organization.id
    assert "site-target" in switched.scoped_access["site"]
    assert "site-current" not in switched.scoped_access["site"]


def test_tenant_switch_does_not_leak_canonical_tenant_admin_authority(
    services,
) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    tenant_context = services["tenant_context_service"]
    current_tenant_id = tenant_context.get_active_tenant_id()
    current_organization_id = tenant_context.get_active_organization_id()
    assert current_tenant_id is not None
    actor = auth.register_user(
        "containment-ambiguous-admin",
        "StrongPass123!",
        role_names=["tenant_admin"],
        tenant_id=current_tenant_id,
    )
    original = auth.build_principal_for_context(
        actor,
        tenant_id=current_tenant_id,
        organization_id=current_organization_id,
    )
    user_session.set_principal(original)
    target_tenant = Tenant.create(
        tenant_code="CONTAIN-AMBIG",
        display_name="Containment Ambiguous",
    )
    services["tenant_admin_service"]._tenant_repo.add(target_tenant)
    auth._user_tenant_repo.add(
        UserTenantMembership.create(
            user_id=actor.id,
            tenant_id=target_tenant.id,
            tenant_role="tenant_admin",
        )
    )
    services["session"].flush()

    tenant_context.switch_to_tenant(target_tenant.id)

    switched = user_session.principal
    assert switched is not None
    assert switched.active_tenant_id == target_tenant.id
    assert "tenant_admin" not in switched.role_names
    assert "auth.manage" not in switched.permissions
