from __future__ import annotations

import pytest

from core.exceptions import NotFoundError, ValidationError


def test_bootstrap_creates_admin_and_permissions(services):
    auth = services["auth_service"]

    admin = auth.authenticate("admin", "ChangeMe123!")
    permissions = auth.get_user_permissions(admin.id)

    assert "auth.manage" in permissions
    assert "project.manage" in permissions
    assert "report.export" in permissions


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
