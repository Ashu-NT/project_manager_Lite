from __future__ import annotations

from datetime import timedelta

import pytest

from core.platform.auth.mfa import generate_totp_code
from core.platform.common.exceptions import NotFoundError, ValidationError
from infra.platform.services import build_service_dict


def test_bootstrap_creates_admin_and_permissions(services):
    auth = services["auth_service"]

    admin = auth.authenticate("admin", "ChangeMe123!")
    permissions = auth.get_user_permissions(admin.id)

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


def test_register_user_uses_default_viewer_role(services):
    auth = services["auth_service"]

    user = auth.register_user("alice", "StrongPass123")
    authenticated = auth.authenticate("alice", "StrongPass123")
    permissions = auth.get_user_permissions(user.id)

    assert authenticated.id == user.id
    assert "project.read" in permissions
    assert "project.manage" not in permissions


def test_assign_role_elevates_permissions(services):
    auth = services["auth_service"]
    user = auth.register_user("planner-user", "StrongPass123")

    auth.assign_role(user.id, "planner")
    permissions = auth.get_user_permissions(user.id)

    assert "task.manage" in permissions
    assert "baseline.manage" in permissions


def test_register_user_rejects_weak_password(services):
    auth = services["auth_service"]

    with pytest.raises(ValidationError):
        auth.register_user("weak-pass-user", "123")

    with pytest.raises(ValidationError, match="uppercase"):
        auth.register_user("weak-pass-user-2", "alllowercase123")

    with pytest.raises(ValidationError, match="digit"):
        auth.register_user("weak-pass-user-3", "NoDigitsHere")


def test_register_user_rejects_invalid_email(services):
    auth = services["auth_service"]

    with pytest.raises(ValidationError, match="Invalid email format"):
        auth.register_user(
            "email-invalid-user",
            "StrongPass123",
            email="not-an-email",
        )


def test_register_user_normalizes_email(services):
    auth = services["auth_service"]

    user = auth.register_user(
        "email-normalized-user",
        "StrongPass123",
        email="  USER.Name@Example.COM  ",
    )

    assert user.email == "user.name@example.com"


def test_register_user_rolls_back_when_role_is_invalid(services):
    auth = services["auth_service"]

    with pytest.raises(NotFoundError):
        auth.register_user(
            "transient-user",
            "StrongPass123",
            role_names=["missing-role"],
        )

    created = auth.register_user("transient-user", "StrongPass123")
    assert created.username == "transient-user"


def test_admin_can_reset_other_user_password(services):
    auth = services["auth_service"]
    user = auth.register_user("reset-target", "StrongPass123")

    auth.reset_user_password(user.id, "NewStrongPass123")

    authenticated = auth.authenticate("reset-target", "NewStrongPass123")
    assert authenticated.id == user.id
    assert authenticated.must_change_password is True
    with pytest.raises(ValidationError, match="Invalid credentials"):
        auth.authenticate("reset-target", "StrongPass123")


def test_admin_can_edit_user_profile_without_touching_password(services):
    auth = services["auth_service"]
    user = auth.register_user(
        "profile-target",
        "StrongPass123",
        display_name="Old Name",
        email="old@example.com",
    )

    updated = auth.update_user_profile(
        user.id,
        username="profile-target-updated",
        display_name="New Name",
        email="new@example.com",
    )

    assert updated.username == "profile-target-updated"
    assert updated.display_name == "New Name"
    assert updated.email == "new@example.com"
    assert auth.authenticate("profile-target-updated", "StrongPass123").id == user.id


def test_auth_service_supports_federated_identity_and_mfa_hooks(services):
    auth = services["auth_service"]
    user = auth.register_user("federated-user", "StrongPass123", role_names=["viewer"])

    linked = auth.link_federated_identity(
        user.id,
        identity_provider="AzureAD",
        federated_subject="oidc-user-123",
    )
    secret = auth.provision_mfa_secret(user.id)
    auth.enable_user_mfa(user.id, generate_totp_code(secret))

    assert linked.identity_provider == "azuread"
    assert linked.federated_subject == "oidc-user-123"

    with pytest.raises(ValidationError, match="Multi-factor authentication code is required"):
        auth.authenticate("federated-user", "StrongPass123")

    password_login = auth.authenticate(
        "federated-user",
        "StrongPass123",
        mfa_code=generate_totp_code(secret),
        device_label="QA Laptop",
    )
    federated_login = auth.authenticate_federated(
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
    auth = services["auth_service"]

    with pytest.raises(ValidationError, match="separation of duties"):
        auth.register_user(
            "sod-conflict-user",
            "StrongPass123",
            role_names=["planner", "approver"],
        )

    access_user = auth.register_user("sod-access-user", "StrongPass123", role_names=["access_admin"])
    with pytest.raises(ValidationError, match="separation of duties"):
        auth.assign_role(access_user.id, "security_admin")


def test_auth_service_supports_per_user_session_timeout_policy(services):
    auth = services["auth_service"]
    user = auth.register_user("session-policy-user", "StrongPass123", role_names=["viewer"])

    auth.set_user_session_policy(user.id, session_timeout_minutes_override=30)
    authenticated = auth.authenticate("session-policy-user", "StrongPass123")

    assert authenticated.session_expires_at is not None
    assert authenticated.last_login_at is not None
    delta_seconds = (authenticated.session_expires_at - authenticated.last_login_at).total_seconds()
    assert delta_seconds == pytest.approx(timedelta(minutes=30).total_seconds(), rel=0.0, abs=5.0)


def test_edit_user_profile_rejects_duplicate_username(services):
    auth = services["auth_service"]
    auth.register_user("profile-alpha", "StrongPass123")
    target = auth.register_user("profile-beta", "StrongPass123")

    with pytest.raises(ValidationError, match="Username already exists"):
        auth.update_user_profile(target.id, username="profile-alpha")


def test_auth_service_persists_sessions_and_supports_single_session_revocation(services):
    auth = services["auth_service"]
    user = auth.register_user("session-persist-user", "StrongPass123", role_names=["viewer"])

    desktop_login = auth.authenticate("session-persist-user", "StrongPass123", device_label="Desktop")
    desktop_principal = auth.build_principal(desktop_login)
    browser_login = auth.authenticate("session-persist-user", "StrongPass123", device_label="Browser")
    browser_principal = auth.build_principal(browser_login)
    sessions = auth.list_user_sessions(user.id)

    assert desktop_principal.session_id is not None
    assert browser_principal.session_id is not None
    assert desktop_principal.session_id != browser_principal.session_id
    assert len(sessions) == 2

    auth.revoke_session(desktop_principal.session_id, note="Revoke one device")

    assert auth.validate_session_principal(desktop_principal) is None
    assert auth.validate_session_principal(browser_principal) is not None
