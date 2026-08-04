from __future__ import annotations

from dataclasses import replace
import json

import pytest
from sqlalchemy import select

from src.core.platform.auth.domain import (
    ROLE_SCOPE_TENANT,
    Role,
    RoleBinding,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry import (
    AuditEntryORM,
)
from src.core.platform.domain.tenant.tenancy import Tenant


_PASSWORD = "StrongPass123!"


def _tenant_id(services) -> str:
    tenant_id = services[
        "tenant_context_service"
    ].require_active_tenant_id(
        operation_label="test tenant custom roles"
    )
    return tenant_id


def _set_tenant_admin(services, *, username: str = "custom-role-admin"):
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        username,
        _PASSWORD,
        role_names=["tenant_admin"],
        tenant_id=tenant_id,
    )
    principal = auth.build_principal_for_context(
        actor,
        tenant_id=tenant_id,
        organization_id=services[
            "tenant_context_service"
        ].get_active_organization_id(),
    )
    assert {"auth.manage", "auth.role.assign"} <= principal.permissions
    services["user_session"].set_principal(principal)
    return actor


def _permission_codes(services, role_id: str) -> set[str]:
    service = services["tenant_role_administration_service"]
    return service._permission_codes(role_id)


def _audit_actions(services, role_id: str) -> list[str]:
    rows = services["session"].execute(
        select(AuditEntryORM)
        .where(AuditEntryORM.entity_type == "custom_role")
        .where(AuditEntryORM.entity_id == role_id)
        .order_by(AuditEntryORM.timestamp)
    ).scalars()
    return [
        str(json.loads(row.metadata_json).get("action") or "")
        for row in rows
    ]


def test_custom_role_creation_is_tenant_scoped_and_atomically_audited(
    services,
) -> None:
    _set_tenant_admin(services)
    service = services["tenant_role_administration_service"]

    role = service.create_custom_role(
        name="project_coordinator",
        display_name="Project Coordinator",
        description="Coordinates tenant projects.",
        permission_codes={"project.read", "project.manage"},
    )

    assert role.tenant_id == _tenant_id(services)
    assert role.is_system is False
    assert role.allowed_scope_type == ROLE_SCOPE_TENANT
    assert role.policy_version == 1
    assert _permission_codes(services, role.id) == {
        "project.read",
        "project.manage",
    }
    assert [listed.id for listed in service.list_custom_roles()] == [role.id]
    assert _audit_actions(services, role.id) == [
        "auth.custom_role.created"
    ]


@pytest.mark.parametrize(
    ("name", "permission_codes", "expected_code"),
    [
        ("admin", {"project.read"}, "CUSTOM_ROLE_NAME_RESERVED"),
        (
            "platform_shadow",
            {"platform.admin"},
            "CUSTOM_ROLE_PERMISSION_DENIED",
        ),
    ],
)
def test_custom_role_creation_blocks_system_impersonation_and_escalation(
    services,
    name: str,
    permission_codes: set[str],
    expected_code: str,
) -> None:
    _set_tenant_admin(services)

    with pytest.raises(BusinessRuleError) as exc_info:
        services[
            "tenant_role_administration_service"
        ].create_custom_role(
            name=name,
            display_name=name.replace("_", " ").title(),
            permission_codes=permission_codes,
        )

    assert exc_info.value.code == expected_code


def test_custom_role_administration_requires_policy_v2_permission(
    services,
) -> None:
    _set_tenant_admin(services)
    principal = services["user_session"].principal
    assert principal is not None
    services["user_session"].set_principal(
        replace(
            principal,
            permissions=frozenset(
                permission
                for permission in principal.permissions
                if permission != "auth.role.assign"
            ),
        )
    )

    with pytest.raises(BusinessRuleError) as exc_info:
        services[
            "tenant_role_administration_service"
        ].create_custom_role(
            name="policy_v2_required",
            display_name="Policy V2 Required",
            permission_codes={"project.read"},
        )

    assert exc_info.value.code == "PERMISSION_DENIED"


def test_platform_operator_cannot_use_customer_custom_role_path(
    services,
) -> None:
    with pytest.raises(BusinessRuleError) as exc_info:
        services[
            "tenant_role_administration_service"
        ].create_custom_role(
            name="platform_created_customer_role",
            display_name="Platform Created Customer Role",
            permission_codes={"project.read"},
        )

    assert exc_info.value.code == "PLATFORM_CUSTOMER_OPERATION_DENIED"


def test_customer_role_manager_requires_canonical_tenant_scope(
    services,
) -> None:
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        "organization-scoped-role-manager",
        _PASSWORD,
        role_names=[],
        tenant_id=tenant_id,
    )
    principal = auth.build_principal_for_context(
        actor,
        tenant_id=tenant_id,
        organization_id=services[
            "tenant_context_service"
        ].get_active_organization_id(),
    )
    services["user_session"].set_principal(
        replace(
            principal,
            permissions=frozenset(
                {*principal.permissions, "auth.manage", "auth.role.assign"}
            ),
        )
    )

    with pytest.raises(BusinessRuleError) as exc_info:
        services[
            "tenant_role_administration_service"
        ].create_custom_role(
            name="scope_escape_role",
            display_name="Scope Escape Role",
            permission_codes={"project.read"},
        )

    assert exc_info.value.code == "CUSTOM_ROLE_TENANT_SCOPE_REQUIRED"


def test_custom_role_update_is_full_replacement_and_optimistic(
    services,
) -> None:
    _set_tenant_admin(services)
    service = services["tenant_role_administration_service"]
    role = service.create_custom_role(
        name="project_observer",
        display_name="Project Observer",
        permission_codes={"project.read"},
    )

    updated = service.update_custom_role(
        role.id,
        expected_policy_version=role.policy_version,
        display_name="Project Coordinator",
        description="Coordinates delivery.",
        permission_codes={"project.read", "project.manage"},
        is_assignable=True,
    )

    assert updated.name == role.name
    assert updated.policy_version == 2
    assert _permission_codes(services, role.id) == {
        "project.read",
        "project.manage",
    }
    with pytest.raises(ConcurrencyError) as exc_info:
        service.update_custom_role(
            role.id,
            expected_policy_version=role.policy_version,
            display_name="Stale Update",
            permission_codes={"project.read"},
        )
    assert exc_info.value.code == "CUSTOM_ROLE_STALE"
    assert _audit_actions(services, role.id) == [
        "auth.custom_role.created",
        "auth.custom_role.updated",
    ]


def test_custom_role_permissions_enforce_separation_of_duties(
    services,
) -> None:
    _set_tenant_admin(services)

    with pytest.raises(ValidationError) as exc_info:
        services[
            "tenant_role_administration_service"
        ].create_custom_role(
            name="conflicted_approver",
            display_name="Conflicted Approver",
            permission_codes={"approval.request", "approval.decide"},
        )

    assert exc_info.value.code == "CUSTOM_ROLE_PERMISSION_CONFLICT"


def test_custom_role_cannot_be_updated_across_tenants(services) -> None:
    _set_tenant_admin(services)
    service = services["tenant_role_administration_service"]
    other_tenant = Tenant.create(
        tenant_code="CUSTOM-ROLE-OTHER",
        display_name="Other Custom Role Tenant",
    )
    service._tenant_repo.add(other_tenant)
    services["session"].flush()
    other_role = Role.create(
        name="other_tenant_role",
        display_name="Other Tenant Role",
        is_system=False,
        tenant_id=other_tenant.id,
    )
    service._role_repo.add(other_role)
    services["session"].commit()

    with pytest.raises(NotFoundError) as exc_info:
        service.update_custom_role(
            other_role.id,
            expected_policy_version=other_role.policy_version,
            display_name="Cross Tenant Update",
            permission_codes={"project.read"},
        )

    assert exc_info.value.code == "CUSTOM_ROLE_NOT_FOUND"


def test_custom_role_creation_rolls_back_when_audit_fails(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_tenant_admin(services)
    service = services["tenant_role_administration_service"]

    def _fail_audit(*_args, **_kwargs) -> None:
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(
        service._audit_repo,
        "add_for_tenant",
        _fail_audit,
    )

    with pytest.raises(RuntimeError, match="audit unavailable"):
        service.create_custom_role(
            name="rolled_back_role",
            display_name="Rolled Back Role",
            permission_codes={"project.read"},
        )

    assert (
        service._role_repo.get_for_tenant_by_name(
            _tenant_id(services),
            "rolled_back_role",
            include_system=False,
        )
        is None
    )


def test_custom_role_update_rolls_back_definition_when_audit_fails(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_tenant_admin(services)
    service = services["tenant_role_administration_service"]
    role = service.create_custom_role(
        name="audit_guarded_role",
        display_name="Audit Guarded Role",
        permission_codes={"project.read"},
    )

    def _fail_audit(*_args, **_kwargs) -> None:
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(
        service._audit_repo,
        "add_for_tenant",
        _fail_audit,
    )

    with pytest.raises(RuntimeError, match="audit unavailable"):
        service.update_custom_role(
            role.id,
            expected_policy_version=role.policy_version,
            display_name="Should Roll Back",
            permission_codes={"project.manage"},
        )

    persisted = service._role_repo.get(role.id)
    assert persisted is not None
    assert persisted.display_name == role.display_name
    assert persisted.policy_version == role.policy_version
    assert _permission_codes(services, role.id) == {"project.read"}


def test_permission_update_revokes_current_tenant_holder_session(
    services,
) -> None:
    actor = _set_tenant_admin(services)
    service = services["tenant_role_administration_service"]
    tenant_id = _tenant_id(services)
    role = service.create_custom_role(
        name="session_guarded_role",
        display_name="Session Guarded Role",
        permission_codes={"project.read"},
    )
    target = services["auth_service"].register_user(
        "custom-role-update-holder",
        _PASSWORD,
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    service._role_binding_repo.add(
        RoleBinding.create(
            principal_id=target.id,
            role_id=role.id,
            tenant_id=tenant_id,
            actual_scope_type=ROLE_SCOPE_TENANT,
            assigned_by=actor.id,
        )
    )
    services["session"].commit()
    authenticated = services["auth_service"].authenticate(
        target.username,
        _PASSWORD,
    )
    assert authenticated.active_session_id is not None

    updated = service.update_custom_role(
        role.id,
        expected_policy_version=role.policy_version,
        display_name=role.display_name,
        permission_codes={"project.read", "project.manage"},
    )

    assert updated.policy_version == role.policy_version + 1
    assert service._role_binding_repo.list_active_for_role(
        role.id,
        tenant_id=tenant_id,
    )
    revoked_session = service._auth_session_repo.get(
        authenticated.active_session_id
    )
    assert revoked_session is not None
    assert revoked_session.revoked_at is not None


def test_custom_role_update_invalidates_reviewed_delegation(
    services,
) -> None:
    platform_principal = services["user_session"].principal
    assert platform_principal is not None
    _set_tenant_admin(services)
    tenant_principal = services["user_session"].principal
    assert tenant_principal is not None
    service = services["tenant_role_administration_service"]
    governance = services["role_governance_service"]
    tenant_id = _tenant_id(services)
    role = service.create_custom_role(
        name="delegated_coordinator",
        display_name="Delegated Coordinator",
        permission_codes={"project.read"},
    )
    target = services["auth_service"].register_user(
        "delegated-custom-role-target",
        _PASSWORD,
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    actor_role = services["auth_service"]._role_repo.get_by_name(
        "tenant_admin"
    )
    assert actor_role is not None
    services["user_session"].set_principal(platform_principal)
    governance.create_delegation_policy(
        actor_role_id=actor_role.id,
        assignable_role_id=role.id,
        target_scope_type=ROLE_SCOPE_TENANT,
        tenant_id=tenant_id,
    )
    services["user_session"].set_principal(tenant_principal)
    service.update_custom_role(
        role.id,
        expected_policy_version=role.policy_version,
        display_name=role.display_name,
        permission_codes={"project.read", "project.manage"},
    )

    with pytest.raises(BusinessRuleError) as exc_info:
        governance.assign_role(
            target_user_id=target.id,
            role_id=role.id,
        )

    assert exc_info.value.code == "ROLE_DELEGATION_POLICY_STALE"


def test_retiring_custom_role_revokes_bindings_and_tenant_sessions(
    services,
) -> None:
    actor = _set_tenant_admin(services)
    service = services["tenant_role_administration_service"]
    tenant_id = _tenant_id(services)
    role = service.create_custom_role(
        name="temporary_coordinator",
        display_name="Temporary Coordinator",
        permission_codes={"project.read"},
    )
    target = services["auth_service"].register_user(
        "custom-role-holder",
        _PASSWORD,
        role_names=["viewer"],
        tenant_id=tenant_id,
    )
    service._role_binding_repo.add(
        RoleBinding.create(
            principal_id=target.id,
            role_id=role.id,
            tenant_id=tenant_id,
            actual_scope_type=ROLE_SCOPE_TENANT,
            assigned_by=actor.id,
        )
    )
    services["session"].commit()
    authenticated = services["auth_service"].authenticate(
        target.username,
        _PASSWORD,
    )
    assert authenticated.active_session_id is not None
    active_session = service._auth_session_repo.get(
        authenticated.active_session_id
    )
    assert active_session is not None
    assert active_session.last_active_tenant_id == tenant_id

    retired = service.retire_custom_role(
        role.id,
        expected_policy_version=role.policy_version,
    )

    assert retired.status == "retired"
    assert retired.is_assignable is False
    assert retired.policy_version == 2
    assert service._role_binding_repo.list_active_for_role(
        role.id,
        tenant_id=tenant_id,
    ) == []
    revoked_session = service._auth_session_repo.get(
        authenticated.active_session_id
    )
    assert revoked_session is not None
    assert revoked_session.revoked_at is not None
    assert service.list_custom_roles() == []
    assert _audit_actions(services, role.id) == [
        "auth.custom_role.created",
        "auth.custom_role.retired",
    ]
