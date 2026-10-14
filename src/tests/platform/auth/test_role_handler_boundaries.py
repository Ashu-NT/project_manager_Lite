from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.core.platform.application.security.authorization.roles import (
    RoleGovernanceCommandHandler,
    RolePolicyReconciliationCommandHandler,
    RolePolicyReconciliationQueryHandler,
    ScopeDelegationProvisioningCommandHandler,
    ScopeDelegationProvisioningQueryHandler,
    TenantRoleCommandHandler,
    TenantRoleQueryHandler,
)
from src.core.platform.application.security.authorization.roles.tenant_role_authorization import (
    TenantRoleAuthorization,
)
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.platform.domain.security.auth import Permission, Role
from src.core.platform.domain.security.auth.session import (
    UserSessionContext,
    UserSessionPrincipal,
)
from src.core.platform.domain.security.authorization.enforcement.sod import (
    SeparationOfDutiesPolicy,
)


def _session(permissions=()):
    session = UserSessionContext()
    session.set_principal(
        UserSessionPrincipal(
            user_id="actor",
            username="actor",
            display_name=None,
            role_names=frozenset(),
            permissions=frozenset(permissions),
            active_tenant_id="tenant",
        )
    )
    return session


def _authorization(
    *, scope_type="tenant", permissions=("auth.manage", "auth.role.assign")
):
    permission_repo = MagicMock()
    permission_repo.list_all.return_value = [
        Permission.create(code=code, description=code)
        for code in (
            "auth.manage",
            "auth.role.assign",
            "project.read",
            "platform.admin",
            "approval.request",
            "approval.decide",
        )
    ]
    role_permissions = MagicMock()
    role_permissions.list_permission_ids.return_value = [
        permission.id
        for permission in permission_repo.list_all.return_value
        if permission.code in {"auth.manage", "auth.role.assign"}
    ]
    bindings = MagicMock()
    bindings.list_active_for_principal.return_value = [
        SimpleNamespace(
            actual_scope_type=scope_type, actual_scope_id=None, role_id="admin"
        )
    ]
    tenants = MagicMock()
    tenants.get.return_value = SimpleNamespace(is_active=True)
    memberships = MagicMock()
    memberships.is_active_member.return_value = True
    context = MagicMock()
    context.require_active_tenant_id.return_value = "tenant"
    authorization = TenantRoleAuthorization(
        role_binding_repo=bindings,
        permission_repo=permission_repo,
        role_permission_repo=role_permissions,
        tenant_repo=tenants,
        membership_repo=memberships,
        user_session=_session(permissions),
        tenant_context_service=context,
        sod_policy=SeparationOfDutiesPolicy(),
    )
    return authorization


@pytest.mark.parametrize(
    "handler, absent",
    [
        (RoleGovernanceCommandHandler, "preview"),
        (RolePolicyReconciliationCommandHandler, "preview"),
        (RolePolicyReconciliationQueryHandler, "apply"),
        (ScopeDelegationProvisioningCommandHandler, "preview"),
        (ScopeDelegationProvisioningQueryHandler, "apply"),
        (TenantRoleCommandHandler, "list_custom_roles"),
        (TenantRoleQueryHandler, "create_custom_role"),
    ],
)
def test_handlers_expose_only_their_command_or_query_surface(handler, absent):
    assert not hasattr(handler, absent)


def test_tenant_query_keeps_scope_and_excludes_retired_roles():
    roles = MagicMock()
    active = Role.create(name="custom", is_system=False, tenant_id="tenant")
    roles.list_for_tenant.return_value = [active, SimpleNamespace(status="retired")]
    queries = TenantRoleQueryHandler(role_repo=roles, authorization=_authorization())

    assert queries.list_custom_roles() == [active]
    roles.list_for_tenant.assert_called_once_with("tenant", include_system=False)
    roles.add.assert_not_called()


@pytest.mark.parametrize(
    "permissions, scope_type, code",
    [
        (("auth.manage",), "tenant", "PERMISSION_DENIED"),
        (
            ("auth.manage", "auth.role.assign", "platform.admin"),
            "tenant",
            "PLATFORM_CUSTOMER_OPERATION_DENIED",
        ),
        (
            ("auth.manage", "auth.role.assign"),
            "organization",
            "CUSTOM_ROLE_TENANT_SCOPE_REQUIRED",
        ),
    ],
)
def test_tenant_query_denies_before_reading_roles(permissions, scope_type, code):
    roles = MagicMock()
    queries = TenantRoleQueryHandler(
        role_repo=roles,
        authorization=_authorization(permissions=permissions, scope_type=scope_type),
    )
    with pytest.raises(BusinessRuleError) as error:
        queries.list_custom_roles()
    assert error.value.code == code
    roles.list_for_tenant.assert_not_called()


@pytest.mark.parametrize(
    "codes, error_type, code",
    [
        (("platform.admin",), BusinessRuleError, "CUSTOM_ROLE_PERMISSION_DENIED"),
        (
            ("approval.request", "approval.decide"),
            ValidationError,
            "CUSTOM_ROLE_PERMISSION_CONFLICT",
        ),
    ],
)
def test_shared_custom_role_policy_preserves_ceiling_and_sod(codes, error_type, code):
    with pytest.raises(error_type) as error:
        _authorization().validate_permissions(codes)
    assert error.value.code == code


def test_reconciliation_query_denies_before_repository_access():
    roles = MagicMock()
    queries = RolePolicyReconciliationQueryHandler(
        role_repo=roles,
        permission_repo=MagicMock(),
        role_permission_repo=MagicMock(),
        auth_session_repo=MagicMock(),
        reconciliation_repo=MagicMock(),
        role_binding_repo=MagicMock(),
        user_session=_session(),
    )
    with pytest.raises(BusinessRuleError):
        queries.preview()
    with pytest.raises(BusinessRuleError):
        queries.build_plan(lock_policy_state=True)
    roles.list_all.assert_not_called()


def test_scope_delegation_command_uses_reviewed_query_and_canonical_governance():
    roles = MagicMock()
    roles.get_by_name.side_effect = lambda name: SimpleNamespace(id=name)
    delegations = MagicMock()
    delegations.get_active_exact.return_value = None
    queries = ScopeDelegationProvisioningQueryHandler(
        role_repo=roles, delegation_repo=delegations
    )
    governance = MagicMock()
    commands = ScopeDelegationProvisioningCommandHandler(
        role_repo=roles,
        queries=queries,
        role_governance_commands=governance,
    )
    catalog = (("access_admin", "project_viewer", "project"),)
    plan = queries.preview(catalog)
    with pytest.raises(BusinessRuleError) as error:
        commands.apply(expected_catalog_hash="stale", catalog=catalog)
    assert error.value.code == "SCOPE_DELEGATION_CATALOG_HASH_MISMATCH"
    governance.create_delegation_policy.assert_not_called()

    result = commands.apply(expected_catalog_hash=plan.catalog_hash, catalog=catalog)
    assert result.created == plan.pending_entries
    governance.create_delegation_policy.assert_called_once_with(
        actor_role_id="access_admin",
        assignable_role_id="project_viewer",
        target_scope_type="project",
        tenant_id=None,
    )
