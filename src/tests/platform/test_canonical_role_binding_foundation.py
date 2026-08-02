from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from src.core.platform.auth.domain import (
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_TENANT,
    Role,
    RoleBinding,
    UserAccount,
)
from src.core.platform.auth.passwords import hash_password
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.tenancy import Tenant
from src.infra.composition.repositories import build_repository_bundle


@pytest.mark.parametrize(
    "scope_type,tenant_id,scope_id",
    (
        (ROLE_SCOPE_PLATFORM, "tenant-a", None),
        (ROLE_SCOPE_TENANT, None, None),
        (ROLE_SCOPE_TENANT, "tenant-a", "resource-a"),
        ("organization", "tenant-a", None),
    ),
)
def test_role_binding_domain_rejects_invalid_scope_shapes(
    scope_type: str,
    tenant_id: str | None,
    scope_id: str | None,
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        RoleBinding.create(
            principal_id="user-a",
            role_id="role-a",
            actual_scope_type=scope_type,
            tenant_id=tenant_id,
            actual_scope_id=scope_id,
        )

    assert exc_info.value.code == "AUTH_ROLE_BINDING_SCOPE_INVALID"


def test_role_binding_domain_accepts_platform_tenant_and_resource_scopes() -> None:
    platform = RoleBinding.create(
        principal_id="user-a",
        role_id="platform-role",
        actual_scope_type=ROLE_SCOPE_PLATFORM,
    )
    tenant = RoleBinding.create(
        principal_id="user-a",
        role_id="tenant-role",
        actual_scope_type=ROLE_SCOPE_TENANT,
        tenant_id="tenant-a",
    )
    organization = RoleBinding.create(
        principal_id="user-a",
        role_id="org-role",
        actual_scope_type="organization",
        tenant_id="tenant-a",
        actual_scope_id="org-a",
    )

    assert platform.tenant_id is None
    assert tenant.actual_scope_id is None
    assert organization.actual_scope_id == "org-a"


def test_system_role_catalog_persists_explicit_scope_metadata(services) -> None:
    auth = services["auth_service"]

    platform_admin = auth._role_repo.get_by_name("admin")
    tenant_admin = auth._role_repo.get_by_name("tenant_admin")
    organization_admin = auth._role_repo.get_by_name("org_admin")

    assert platform_admin is not None
    assert platform_admin.allowed_scope_type == ROLE_SCOPE_PLATFORM
    assert platform_admin.is_assignable is False
    assert tenant_admin is not None
    assert tenant_admin.allowed_scope_type == ROLE_SCOPE_TENANT
    assert tenant_admin.is_assignable is True
    assert organization_admin is not None
    assert organization_admin.allowed_scope_type == "organization"


def test_role_binding_repository_reads_only_active_exact_tenant_rows(session) -> None:
    repositories = build_repository_bundle(session)
    user = UserAccount.create(
        username="canonical-user",
        password_hash=hash_password("CanonicalUser123!"),
    )
    tenant = Tenant.create(
        tenant_code="CANONICAL",
        display_name="Canonical Tenant",
    )
    role = Role.create(
        name="canonical_viewer",
        allowed_scope_type=ROLE_SCOPE_TENANT,
    )
    expired_role = Role.create(
        name="canonical_expired",
        allowed_scope_type=ROLE_SCOPE_TENANT,
    )
    repositories.user_repo.add(user)
    repositories.tenant_repo.add(tenant)
    repositories.role_repo.add(role)
    repositories.role_repo.add(expired_role)
    session.flush()

    active = RoleBinding.create(
        principal_id=user.id,
        role_id=expired_role.id,
        tenant_id=tenant.id,
        actual_scope_type=ROLE_SCOPE_TENANT,
    )
    expired = RoleBinding(
        id="expired-binding",
        principal_type="user",
        principal_id=user.id,
        role_id=role.id,
        tenant_id=tenant.id,
        actual_scope_type=ROLE_SCOPE_TENANT,
        actual_scope_id=None,
        assigned_by=None,
        assigned_at=datetime.now(timezone.utc) - timedelta(days=2),
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        revoked_at=None,
        version=1,
    )
    repositories.role_binding_repo.add(active)
    repositories.role_binding_repo.add(expired)
    session.commit()

    persisted = repositories.role_binding_repo.get(active.id)
    rows = repositories.role_binding_repo.list_active_for_principal(
        user.id,
        tenant_id=tenant.id,
    )

    assert persisted == active
    assert [row.id for row in rows] == [active.id]
    assert repositories.role_binding_repo.list_active_for_principal(
        user.id,
        tenant_id=None,
    ) == []


def test_database_rejects_duplicate_active_tenant_role_binding(session) -> None:
    repositories = build_repository_bundle(session)
    user = UserAccount.create(
        username="duplicate-binding-user",
        password_hash=hash_password("DuplicateBinding123!"),
    )
    tenant = Tenant.create(
        tenant_code="DUPLICATE",
        display_name="Duplicate Tenant",
    )
    role = Role.create(
        name="duplicate_binding_role",
        allowed_scope_type=ROLE_SCOPE_TENANT,
    )
    repositories.user_repo.add(user)
    repositories.tenant_repo.add(tenant)
    repositories.role_repo.add(role)
    session.flush()
    repositories.role_binding_repo.add(
        RoleBinding.create(
            principal_id=user.id,
            role_id=role.id,
            tenant_id=tenant.id,
            actual_scope_type=ROLE_SCOPE_TENANT,
        )
    )
    session.commit()

    repositories.role_binding_repo.add(
        RoleBinding.create(
            principal_id=user.id,
            role_id=role.id,
            tenant_id=tenant.id,
            actual_scope_type=ROLE_SCOPE_TENANT,
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
