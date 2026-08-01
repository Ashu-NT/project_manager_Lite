from __future__ import annotations

import json

import pytest
from sqlalchemy import func, select

from src.core.platform.auth.application import AuthService
from src.core.platform.auth.domain import (
    ROLE_SCOPE_PLATFORM,
    RoleBinding,
    UserAccount,
)
from src.core.platform.auth.passwords import hash_password
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.platform.infrastructure.persistence.orm.audit_entry import AuditEntryORM
from src.core.platform.infrastructure.persistence.orm.auth import UserORM
from src.infra.composition.repositories import RepositoryBundle, build_repository_bundle


class _FailingPlatformAuditWriter:
    def add_platform(self, entry) -> None:
        raise RuntimeError("audit unavailable")


def _build_auth_service(session) -> tuple[AuthService, RepositoryBundle]:
    repositories = build_repository_bundle(session)
    return (
        AuthService(
            session=session,
            user_repo=repositories.user_repo,
            role_repo=repositories.role_repo,
            permission_repo=repositories.permission_repo,
            role_permission_repo=repositories.role_permission_repo,
            role_binding_repo=repositories.role_binding_repo,
            auth_session_repo=repositories.auth_session_repo,
            user_tenant_repo=repositories.user_tenant_repo,
        ),
        repositories,
    )


def test_provision_platform_owner_creates_audited_owner_without_membership(session) -> None:
    auth_service, repositories = _build_auth_service(session)

    result = auth_service.provision_platform_owner(
        username="platform-owner",
        raw_password="OwnerStrong123!",
        audit_writer=repositories.audit_entry_repo,
        display_name="Platform Owner",
        email="owner@example.com",
        provisioning_actor="deployment-test",
    )

    assert result.created is True
    assert result.username == "platform-owner"
    assert auth_service.get_user_role_names(result.user_id) == {"admin"}
    assert repositories.user_tenant_repo.list_tenant_ids_for_user(result.user_id) == []
    owner_role = repositories.role_repo.get_by_name("admin")
    bootstrap_permission = repositories.permission_repo.get_by_code(
        "platform.admin"
    )
    assert owner_role is not None
    assert bootstrap_permission is not None
    assert repositories.role_permission_repo.list_permission_ids(
        owner_role.id
    ) == [bootstrap_permission.id]
    assert auth_service.build_principal(
        repositories.user_repo.get(result.user_id)
    ).permissions == frozenset({"platform.admin"})

    audit_row = session.execute(
        select(AuditEntryORM).where(
            AuditEntryORM.operation == "platform_owner.provision"
        )
    ).scalar_one()
    assert audit_row.tenant_id is None
    assert audit_row.organization_id is None
    assert audit_row.actor_type == "deployment"
    assert audit_row.actor_username == "deployment-test"
    assert audit_row.severity == "critical"
    audit_metadata = json.loads(audit_row.metadata_json)
    assert audit_metadata["username"] == "platform-owner"
    assert audit_metadata["bootstrap_permission_code"] == "platform.admin"
    assert {"password", "raw_password", "password_hash"}.isdisjoint(audit_metadata)


def test_provision_platform_owner_is_idempotent_for_same_username(session) -> None:
    auth_service, repositories = _build_auth_service(session)
    first = auth_service.provision_platform_owner(
        username="platform-owner",
        raw_password="OwnerStrong123!",
        audit_writer=repositories.audit_entry_repo,
    )

    second = auth_service.provision_platform_owner(
        username="platform-owner",
        raw_password="UnusedStrong123!",
        audit_writer=repositories.audit_entry_repo,
    )

    assert first.created is True
    assert second.created is False
    assert second.user_id == first.user_id
    assert session.scalar(select(func.count()).select_from(UserORM)) == 1
    assert (
        session.scalar(
            select(func.count())
            .select_from(AuditEntryORM)
            .where(AuditEntryORM.operation == "platform_owner.provision")
        )
        == 1
    )


def test_existing_owner_missing_bootstrap_authority_requires_recovery(
    session,
) -> None:
    auth_service, repositories = _build_auth_service(session)
    result = auth_service.provision_platform_owner(
        username="platform-owner",
        raw_password="OwnerStrong123!",
        audit_writer=repositories.audit_entry_repo,
    )
    owner_role = repositories.role_repo.get_by_name("admin")
    bootstrap_permission = repositories.permission_repo.get_by_code(
        "platform.admin"
    )
    assert owner_role is not None
    assert bootstrap_permission is not None
    repositories.role_permission_repo.delete(
        owner_role.id,
        bootstrap_permission.id,
    )
    session.commit()

    with pytest.raises(BusinessRuleError) as exc_info:
        auth_service.provision_platform_owner(
            username=result.username,
            raw_password="UnusedStrong123!",
            audit_writer=repositories.audit_entry_repo,
        )

    assert exc_info.value.code == (
        "PLATFORM_OWNER_BOOTSTRAP_AUTHORITY_MISSING"
    )


def test_provision_platform_owner_never_promotes_existing_username(session) -> None:
    auth_service, repositories = _build_auth_service(session)
    ordinary_user = UserAccount.create(
        username="existing-user",
        password_hash=hash_password("ExistingStrong123!"),
    )
    repositories.user_repo.add(ordinary_user)
    session.commit()

    with pytest.raises(BusinessRuleError) as exc_info:
        auth_service.provision_platform_owner(
            username="existing-user",
            raw_password="OwnerStrong123!",
            audit_writer=repositories.audit_entry_repo,
        )

    assert exc_info.value.code == "PLATFORM_OWNER_USERNAME_EXISTS"
    assert auth_service.get_user_role_names(ordinary_user.id) == set()


def test_platform_principal_cannot_enter_customer_context(session) -> None:
    auth_service, repositories = _build_auth_service(session)
    result = auth_service.provision_platform_owner(
        username="platform-owner",
        raw_password="OwnerStrong123!",
        audit_writer=repositories.audit_entry_repo,
    )
    owner = repositories.user_repo.get(result.user_id)
    assert owner is not None

    with pytest.raises(BusinessRuleError) as exc_info:
        auth_service.build_principal_for_context(
            owner,
            tenant_id="customer-tenant",
            organization_id=None,
        )

    assert exc_info.value.code == "PLATFORM_CUSTOMER_CONTEXT_DENIED"


def test_ordinary_registration_cannot_create_platform_admin(services) -> None:
    auth_service = services["auth_service"]

    with pytest.raises(BusinessRuleError) as exc_info:
        auth_service.register_user(
            "second-platform-admin",
            "OwnerStrong123!",
            role_names=["admin"],
        )

    assert exc_info.value.code == "PLATFORM_ROLE_ASSIGNMENT_DENIED"
    assert (
        auth_service._user_repo.get_by_username("second-platform-admin")
        is None
    )


def test_provision_platform_owner_rejects_a_second_owner(session) -> None:
    auth_service, repositories = _build_auth_service(session)
    auth_service.provision_platform_owner(
        username="first-owner",
        raw_password="OwnerStrong123!",
        audit_writer=repositories.audit_entry_repo,
    )

    with pytest.raises(BusinessRuleError) as exc_info:
        auth_service.provision_platform_owner(
            username="second-owner",
            raw_password="OtherStrong123!",
            audit_writer=repositories.audit_entry_repo,
        )

    assert exc_info.value.code == "PLATFORM_OWNER_EXISTS"
    assert repositories.user_repo.get_by_username("second-owner") is None


def test_provision_platform_owner_rejects_ambiguous_existing_owners(session) -> None:
    auth_service, repositories = _build_auth_service(session)
    first = auth_service.provision_platform_owner(
        username="first-owner",
        raw_password="OwnerStrong123!",
        audit_writer=repositories.audit_entry_repo,
    )
    owner_role = repositories.role_repo.get_by_name("admin")
    second = UserAccount.create(
        username="second-owner",
        password_hash=hash_password("OtherStrong123!"),
    )
    repositories.user_repo.add(second)
    session.flush()
    repositories.role_binding_repo.add(
        RoleBinding.create(
            principal_id=second.id,
            role_id=owner_role.id,
            actual_scope_type=ROLE_SCOPE_PLATFORM,
        )
    )
    session.commit()

    with pytest.raises(BusinessRuleError) as exc_info:
        auth_service.provision_platform_owner(
            username=first.username,
            raw_password="OwnerStrong123!",
            audit_writer=repositories.audit_entry_repo,
        )

    assert exc_info.value.code == "PLATFORM_OWNER_AMBIGUOUS"


def test_provision_platform_owner_rolls_back_when_audit_write_fails(session) -> None:
    auth_service, repositories = _build_auth_service(session)

    with pytest.raises(RuntimeError, match="audit unavailable"):
        auth_service.provision_platform_owner(
            username="platform-owner",
            raw_password="OwnerStrong123!",
            audit_writer=_FailingPlatformAuditWriter(),
        )

    assert repositories.user_repo.get_by_username("platform-owner") is None
    assert session.scalar(select(func.count()).select_from(UserORM)) == 0


def test_provision_platform_owner_rejects_weak_password_without_side_effects(session) -> None:
    auth_service, repositories = _build_auth_service(session)

    with pytest.raises(ValidationError):
        auth_service.provision_platform_owner(
            username="platform-owner",
            raw_password="weak",
            audit_writer=repositories.audit_entry_repo,
        )

    assert repositories.user_repo.get_by_username("platform-owner") is None
    assert session.scalar(select(func.count()).select_from(AuditEntryORM)) == 0
