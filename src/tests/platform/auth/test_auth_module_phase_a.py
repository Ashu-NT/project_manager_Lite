from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.domain.security.auth import (
    UserSessionContext,
    UserSessionPrincipal,
)
from src.core.platform.domain.security.auth.credentials.mfa import generate_totp_code
from src.core.platform.domain.security.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.infrastructure.persistence.orm.security.auth.auth import (
    AuthSessionORM,
)
from src.infra.composition.app_container import build_service_dict


def test_session_principal_validation_lease_avoids_repeated_authority_rebuilds() -> None:
    calls: list[str] = []
    principal = UserSessionPrincipal(
        user_id="user-1",
        username="planner",
        display_name="Planner",
        role_names=frozenset({"planner"}),
        permissions=frozenset({"project.read"}),
        session_id="session-1",
    )

    def _validate(current: UserSessionPrincipal) -> UserSessionPrincipal:
        calls.append(current.session_id or "")
        return current

    context = UserSessionContext(
        principal_validator=_validate,
        validation_interval_seconds=30.0,
    )
    context.set_principal(principal)

    assert context.has_permission("project.read") is True
    assert context.has_permission("project.read") is True
    assert calls == []

    assert context.revalidate_principal() is True
    assert context.has_permission("project.read") is True
    assert calls == ["session-1"]


def test_session_principal_forced_revalidation_clears_revoked_session() -> None:
    context = UserSessionContext(
        validation_interval_seconds=30.0,
    )
    context.set_principal(
        UserSessionPrincipal(
            user_id="user-1",
            username="planner",
            display_name="Planner",
            role_names=frozenset({"planner"}),
            permissions=frozenset({"project.read"}),
            session_id="session-1",
        )
    )
    context.set_validator(lambda _principal: None)

    assert context.revalidate_principal() is False
    assert context.principal is None


def test_bootstrap_creates_admin_and_permissions(services):

    admin = services["authentication"].authenticate("admin", "ChangeMe123!")
    permissions = services["auth_queries"].get_user_permissions(admin.id)

    assert admin.must_change_password is True
    assert "auth.manage" in permissions
    assert "project.manage" in permissions
    assert "report.export" in permissions
    assert "approval.request" in permissions
    assert "approval.decide" in permissions


def test_bootstrap_requires_explicit_admin_password(session, monkeypatch):
    monkeypatch.delenv("PM_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("PM_ALLOW_DEFAULT_ADMIN_PASSWORD", raising=False)

    with pytest.raises(ValidationError, match="PM_ADMIN_PASSWORD must be set"):
        build_service_dict(session)


def test_register_user_creates_identity_without_customer_authority(services):

    user = services["user_registration"].register_user("alice", "StrongPass123")
    authenticated = services["authentication"].authenticate("alice", "StrongPass123")
    permissions = services["auth_queries"].get_user_permissions(user.id)

    assert authenticated.id == user.id
    assert "project.read" not in permissions
    assert "project.manage" not in permissions


def test_assign_role_elevates_permissions(services):
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="test canonical role assignment"
    )
    user = services["user_registration"].register_user(
        "planner-user",
        "StrongPass123",
        role_names=[],
        tenant_id=tenant_id,
    )

    services["role_assignment_commands"].assign_role(user.id, "planner")
    permissions = services["auth_queries"].get_user_permissions(user.id)

    assert "task.manage" in permissions
    assert "baseline.manage" in permissions


def test_register_user_rejects_weak_password(services):

    with pytest.raises(ValidationError):
        services["user_registration"].register_user("weak-pass-user", "123")

    with pytest.raises(ValidationError, match="uppercase"):
        services["user_registration"].register_user("weak-pass-user-2", "alllowercase123")

    with pytest.raises(ValidationError, match="digit"):
        services["user_registration"].register_user("weak-pass-user-3", "NoDigitsHere")


def test_register_user_rejects_invalid_email(services):

    with pytest.raises(ValidationError, match="Invalid email format"):
        services["user_registration"].register_user(
            "email-invalid-user",
            "StrongPass123",
            email="not-an-email",
        )


def test_register_user_normalizes_email(services):

    user = services["user_registration"].register_user(
        "email-normalized-user",
        "StrongPass123",
        email="  USER.Name@Example.COM  ",
    )

    assert user.email == "user.name@example.com"


def test_register_user_rolls_back_when_role_is_invalid(services):

    with pytest.raises(NotFoundError):
        services["user_registration"].register_user(
            "transient-user",
            "StrongPass123",
            role_names=["missing-role"],
        )

    created = services["user_registration"].register_user("transient-user", "StrongPass123")
    assert created.username == "transient-user"


def test_admin_can_reset_other_user_password(services):
    user = services["user_registration"].register_user("reset-target", "StrongPass123")

    services["password_commands"].reset_user_password(user.id, "NewStrongPass123")

    authenticated = services["authentication"].authenticate("reset-target", "NewStrongPass123")
    assert authenticated.id == user.id
    assert authenticated.must_change_password is True
    with pytest.raises(ValidationError, match="Invalid credentials"):
        services["authentication"].authenticate("reset-target", "StrongPass123")


def test_admin_can_edit_user_profile_without_touching_password(services):
    user = services["user_registration"].register_user(
        "profile-target",
        "StrongPass123",
        display_name="Old Name",
        email="old@example.com",
    )

    updated = services["user_administration_commands"].update_user_profile(
        user.id,
        username="profile-target-updated",
        display_name="New Name",
        email="new@example.com",
    )

    assert updated.username == "profile-target-updated"
    assert updated.display_name == "New Name"
    assert updated.email == "new@example.com"
    assert services["authentication"].authenticate("profile-target-updated", "StrongPass123").id == user.id


def test_auth_service_supports_federated_identity_and_mfa_hooks(services):
    user = services["user_registration"].register_user("federated-user", "StrongPass123", role_names=["viewer"])

    linked = services["federated_identity_commands"].link_federated_identity(
        user.id,
        identity_provider="AzureAD",
        federated_subject="oidc-user-123",
    )
    secret = services["mfa_commands"].provision_mfa_secret(user.id)
    services["mfa_commands"].enable_user_mfa(user.id, generate_totp_code(secret))

    assert linked.identity_provider == "azuread"
    assert linked.federated_subject == "oidc-user-123"

    with pytest.raises(ValidationError, match="Multi-factor authentication code is required"):
        services["authentication"].authenticate("federated-user", "StrongPass123")

    password_login = services["authentication"].authenticate(
        "federated-user",
        "StrongPass123",
        mfa_code=generate_totp_code(secret),
        device_label="QA Laptop",
    )
    federated_login = services["authentication"].authenticate_federated(
        identity_provider="azuread",
        federated_subject="oidc-user-123",
        mfa_code=generate_totp_code(secret),
        device_label="SSO Browser",
    )

    assert password_login.mfa_enabled is True
    assert password_login.last_login_device_label == "QA Laptop"
    assert password_login.last_login_auth_method == "password"
    assert federated_login.last_login_auth_method == "federated:azuread"
    assert federated_login.last_login_device_label == "SSO Browser"


def test_auth_service_enforces_separation_of_duties_for_conflicting_roles(services):

    with pytest.raises(ValidationError, match="separation of duties"):
        services["user_registration"].register_user(
            "sod-conflict-user",
            "StrongPass123",
            role_names=["planner", "approver"],
        )

    access_user = services["user_registration"].register_user("sod-access-user", "StrongPass123", role_names=["access_admin"])
    with pytest.raises(ValidationError, match="separation of duties"):
        services["role_assignment_commands"].assign_role(access_user.id, "security_admin")


def test_auth_service_supports_per_user_session_timeout_policy(services):
    user = services["user_registration"].register_user("session-policy-user", "StrongPass123", role_names=["viewer"])

    services["auth_session_commands"].set_user_session_policy(user.id, session_timeout_minutes_override=30)
    authenticated = services["authentication"].authenticate("session-policy-user", "StrongPass123")

    assert authenticated.session_expires_at is not None
    assert authenticated.last_login_at is not None
    delta_seconds = (authenticated.session_expires_at - authenticated.last_login_at).total_seconds()
    assert delta_seconds == pytest.approx(timedelta(minutes=30).total_seconds(), rel=0.0, abs=5.0)


def test_edit_user_profile_rejects_duplicate_username(services):
    services["user_registration"].register_user("profile-alpha", "StrongPass123")
    target = services["user_registration"].register_user("profile-beta", "StrongPass123")

    with pytest.raises(ValidationError, match="Username already exists"):
        services["user_administration_commands"].update_user_profile(target.id, username="profile-alpha")


def test_auth_service_persists_sessions_and_supports_single_session_revocation(services):
    user = services["user_registration"].register_user("session-persist-user", "StrongPass123", role_names=["viewer"])

    desktop_login = services["authentication"].authenticate("session-persist-user", "StrongPass123", device_label="Desktop")
    desktop_principal = services["principal_builder"].build(desktop_login)
    browser_login = services["authentication"].authenticate("session-persist-user", "StrongPass123", device_label="Browser")
    browser_principal = services["principal_builder"].build(browser_login)
    sessions = services["auth_session_query"].list_user_sessions(user.id)

    assert desktop_principal.session_id is not None
    assert browser_principal.session_id is not None
    assert desktop_principal.session_id != browser_principal.session_id
    assert len(sessions) == 2

    services["auth_session_commands"].revoke_session(desktop_principal.session_id, note="Revoke one device")

    assert services["auth_session_commands"].validate_session_principal(desktop_principal) is None
    assert services["auth_session_commands"].validate_session_principal(browser_principal) is not None


def test_auth_service_restores_last_active_context_on_reauthentication(services):
    user_session = services["user_session"]

    restored_org = services["organization_commands"].create_organization(
        organization_code="RESTORE-ORG",
        display_name="Restore Org",
        timezone_name="UTC",
        base_currency="USD",
    )
    services["tenant_context_service"].set_active_organization(restored_org.id)
    current_principal = user_session.principal

    assert current_principal is not None
    assert current_principal.session_id is not None

    persisted_current_session = next(
        session
        for session in services["auth_session_query"].list_user_sessions(current_principal.user_id)
        if session.id == current_principal.session_id
    )
    assert persisted_current_session.last_active_organization_id == restored_org.id

    reauthenticated_user = services["authentication"].authenticate("admin", "ChangeMe123!", device_label="Runtime Reauth")
    reauthenticated_principal = services["principal_builder"].build(reauthenticated_user)

    assert reauthenticated_principal.active_organization_id == restored_org.id
    assert reauthenticated_principal.active_tenant_id == user_session.active_tenant_id()

    user_session.clear()
    user_session.set_principal(reauthenticated_principal)

    assert user_session.active_organization_id() == restored_org.id
    assert user_session.active_tenant_id() == reauthenticated_principal.active_tenant_id


def test_validate_session_principal_updates_last_validated_at(services):
    principal = services["user_session"].principal

    assert principal is not None
    assert principal.session_id is not None

    stale_validation_time = datetime.now(UTC) - timedelta(minutes=5)
    auth_session = services["session"].get(AuthSessionORM, principal.session_id)
    assert auth_session is not None
    auth_session.last_validated_at = stale_validation_time
    auth_session.updated_at = stale_validation_time
    services["session"].commit()

    validated_principal = services["auth_session_commands"].validate_session_principal(principal)

    assert validated_principal is not None

    services["session"].expire_all()
    refreshed_auth_session = services["session"].get(AuthSessionORM, principal.session_id)

    assert refreshed_auth_session is not None
    assert refreshed_auth_session.last_validated_at is not None
    assert ensure_utc_datetime(refreshed_auth_session.last_validated_at) > stale_validation_time

