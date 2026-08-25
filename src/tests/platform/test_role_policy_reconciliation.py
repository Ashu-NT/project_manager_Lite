from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from src.core.platform.application.security.authorization.roles import RolePolicyReconciliationService
from src.core.platform.domain.security.authorization.roles import AuthPolicyReconciliation
from src.core.platform.domain.security.auth import (
    Role,
    RolePermissionBinding,
)
from src.core.platform.domain.security.authorization.roles.role_permission_catalog import (
    DEFAULT_ROLE_PERMISSIONS,
    SYSTEM_ROLE_POLICY_NAME,
    SYSTEM_ROLE_POLICY_VERSION,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.common.ids import generate_id
from src.core.platform.infrastructure.persistence.repositories.security.auth.auth import (
    SqlAlchemyAuthPolicyReconciliationRepository,
    SqlAlchemyRoleBindingRepository,
)


_REMOVED_TENANT_ADMIN_PERMISSIONS = {
    "tenant.create",
    "tenant.manage",
    "tenant.read",
}


def _reconciliation_service(services) -> RolePolicyReconciliationService:
    # P5C-1: RoleGovernanceService no longer holds its own `_role_binding_repo` (it opens a
    # fresh UoW-bound one per mutation) -- a freshly-constructed repository bound to the same
    # shared test `session` reads/writes the identical underlying data.
    auth = services["auth_service"]
    return RolePolicyReconciliationService(
        session=services["session"],
        role_repo=auth._role_repo,
        permission_repo=auth._permission_repo,
        role_permission_repo=auth._role_permission_repo,
        user_repo=auth._user_repo,
        auth_session_repo=auth._auth_session_repo,
        reconciliation_repo=SqlAlchemyAuthPolicyReconciliationRepository(
            services["session"]
        ),
        user_session=services["user_session"],
        role_binding_repo=SqlAlchemyRoleBindingRepository(services["session"]),
    )


def _seed_stale_tenant_admin_policy(services, *, username: str):
    auth = services["auth_service"]
    tenant_id = services["tenant_context_service"].get_active_tenant_id()
    assert tenant_id is not None
    user = auth.register_user(
        username,
        "StrongPass123!",
        role_names=["tenant_admin"],
        tenant_id=tenant_id,
    )
    authenticated = auth.authenticate(username, "StrongPass123!")
    assert authenticated.active_session_id is not None

    role = auth._role_repo.get_by_name("tenant_admin")
    assert role is not None
    permission_by_code = {
        permission.code: permission
        for permission in auth._permission_repo.list_all()
    }
    for code in _REMOVED_TENANT_ADMIN_PERMISSIONS:
        permission = permission_by_code[code]
        if not auth._role_permission_repo.exists(role.id, permission.id):
            auth._role_permission_repo.add(
                RolePermissionBinding.create(
                    role_id=role.id,
                    permission_id=permission.id,
                )
            )
    services["session"].commit()
    return user, authenticated.active_session_id, role, permission_by_code


def test_reconciliation_preview_is_deterministic_and_startup_is_non_destructive(
    services,
) -> None:
    user, session_id, role, permission_by_code = _seed_stale_tenant_admin_policy(
        services,
        username="policy-preview-tenant-admin",
    )

    services["auth_service"].bootstrap_defaults()
    for code in _REMOVED_TENANT_ADMIN_PERMISSIONS:
        assert services["auth_service"]._role_permission_repo.exists(
            role.id,
            permission_by_code[code].id,
        )

    service = _reconciliation_service(services)
    first = service.preview()
    second = service.preview()

    assert first.current_version == 0
    assert first.target_version == SYSTEM_ROLE_POLICY_VERSION
    assert first.change_set_hash == second.change_set_hash
    assert {
        (change.role_name, change.permission_code)
        for change in first.removals
    } == {
        ("tenant_admin", code)
        for code in _REMOVED_TENANT_ADMIN_PERMISSIONS
    }
    assert first.additions == ()
    assert user.id in first.affected_user_ids
    assert session_id in first.active_session_ids
    rollback = json.loads(first.rollback_json)
    assert {
        tuple(change) for change in rollback["additions"]
    } == {
        ("tenant_admin", code)
        for code in _REMOVED_TENANT_ADMIN_PERMISSIONS
    }


@pytest.mark.parametrize(
    ("version_delta", "hash_override", "expected_code"),
    [
        (1, None, "ROLE_POLICY_VERSION_MISMATCH"),
        (0, "0" * 64, "ROLE_POLICY_CHANGE_SET_MISMATCH"),
    ],
)
def test_reconciliation_apply_rejects_unreviewed_drift(
    services,
    version_delta: int,
    hash_override: str | None,
    expected_code: str,
) -> None:
    _, _, role, permission_by_code = _seed_stale_tenant_admin_policy(
        services,
        username=f"policy-guard-{expected_code.lower()}",
    )
    service = _reconciliation_service(services)
    plan = service.preview()

    with pytest.raises(BusinessRuleError) as exc_info:
        service.apply(
            expected_version=plan.current_version + version_delta,
            expected_change_set_hash=hash_override or plan.change_set_hash,
        )

    assert exc_info.value.code == expected_code
    for code in _REMOVED_TENANT_ADMIN_PERMISSIONS:
        assert services["auth_service"]._role_permission_repo.exists(
            role.id,
            permission_by_code[code].id,
        )


def test_reconciliation_apply_removes_drift_records_rollback_and_revokes_sessions(
    services,
) -> None:
    user, session_id, role, permission_by_code = _seed_stale_tenant_admin_policy(
        services,
        username="policy-apply-tenant-admin",
    )
    auth = services["auth_service"]
    unmanaged_role = Role.create(
        name="integration_admin",
        description="Owned by a separate platform policy.",
    )
    auth._role_repo.add(unmanaged_role)
    services["session"].commit()
    before_revision = auth._user_repo.get(user.id).session_revision
    service = _reconciliation_service(services)
    plan = service.preview()

    result = service.apply(
        expected_version=plan.current_version,
        expected_change_set_hash=plan.change_set_hash,
    )

    assert result.applied is True
    assert result.revoked_session_count >= 1
    for code in _REMOVED_TENANT_ADMIN_PERMISSIONS:
        assert not auth._role_permission_repo.exists(
            role.id,
            permission_by_code[code].id,
        )
    updated_user = auth._user_repo.get(user.id)
    assert updated_user.session_revision == before_revision + 1
    assert all(
        managed_role.policy_version == SYSTEM_ROLE_POLICY_VERSION
        for managed_role in auth._role_repo.list_all()
        if (
            managed_role.is_system
            and managed_role.name in DEFAULT_ROLE_PERMISSIONS
        )
    )
    assert auth._role_repo.get(unmanaged_role.id).policy_version == 1
    assert auth._auth_session_repo.get(session_id).revoked_at is not None
    assert _REMOVED_TENANT_ADMIN_PERMISSIONS.isdisjoint(
        auth.build_principal(updated_user).permissions
    )

    latest = SqlAlchemyAuthPolicyReconciliationRepository(
        services["session"]
    ).get_latest(plan.policy_name)
    assert latest is not None
    assert latest.from_version == 0
    assert latest.to_version == SYSTEM_ROLE_POLICY_VERSION
    assert latest.change_set_hash == plan.change_set_hash
    assert json.loads(latest.rollback_json)["forward_change_set_hash"] == (
        plan.change_set_hash
    )

    no_op_plan = service.preview()
    no_op_result = service.apply(
        expected_version=no_op_plan.current_version,
        expected_change_set_hash=no_op_plan.change_set_hash,
    )
    assert no_op_result.applied is False
    assert no_op_result.revoked_session_count == 0


def test_tenant_admin_cannot_preview_platform_policy_reconciliation(
    services,
) -> None:
    auth = services["auth_service"]
    tenant_id = services["tenant_context_service"].get_active_tenant_id()
    organization_id = (
        services["tenant_context_service"].get_active_organization_id()
    )
    assert tenant_id is not None
    user = auth.register_user(
        "policy-denied-tenant-admin",
        "StrongPass123!",
        role_names=["tenant_admin"],
        tenant_id=tenant_id,
    )
    services["user_session"].set_principal(
        auth.build_principal_for_context(
            user,
            tenant_id=tenant_id,
            organization_id=organization_id,
        )
    )

    with pytest.raises(BusinessRuleError) as exc_info:
        _reconciliation_service(services).preview()

    assert exc_info.value.code == "PERMISSION_DENIED"


def test_policy_v1_preview_requires_reviewed_role_assignment_additions(
    services,
) -> None:
    auth = services["auth_service"]
    permission = auth._permission_repo.get_by_code("auth.role.assign")
    assert permission is not None
    expected_role_names = {"admin", "tenant_admin", "org_admin"}
    role_map = {
        role.name: role
        for role in auth._role_repo.list_all()
        if role.name in expected_role_names
    }
    for role in role_map.values():
        auth._role_permission_repo.delete(role.id, permission.id)

    reconciliation_repo = SqlAlchemyAuthPolicyReconciliationRepository(
        services["session"]
    )
    reconciliation_repo.add(
        AuthPolicyReconciliation(
            id=generate_id(),
            policy_name=SYSTEM_ROLE_POLICY_NAME,
            from_version=0,
            to_version=1,
            change_set_hash="a" * 64,
            applied_at=datetime.now(timezone.utc),
            applied_by_user_id=services["user_session"].principal.user_id,
            rollback_json="{}",
        )
    )
    services["session"].commit()

    plan = _reconciliation_service(services).preview()

    assert plan.current_version == 1
    assert plan.target_version == SYSTEM_ROLE_POLICY_VERSION
    assert {
        (change.role_name, change.permission_code)
        for change in plan.additions
    } == {
        (role_name, "auth.role.assign")
        for role_name in expected_role_names
    }
