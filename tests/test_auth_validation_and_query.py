from __future__ import annotations

import pytest

from core.exceptions import NotFoundError, ValidationError
from core.services.auth.validation import AuthValidationMixin


class _ValidationProbe(AuthValidationMixin):
    pass


def test_auth_validation_normalizes_and_validates_email():
    probe = _ValidationProbe()
    assert probe._normalize_email("  USER.Name@Example.COM  ") == "user.name@example.com"
    assert probe._normalize_email("   ") is None

    probe._validate_email(None)
    with pytest.raises(ValidationError, match="Invalid email format"):
        probe._validate_email("not-an-email")


def test_auth_validation_rejects_weak_password_shapes():
    probe = _ValidationProbe()
    with pytest.raises(ValidationError, match="at least 8"):
        probe._validate_password("Short1")
    with pytest.raises(ValidationError, match="uppercase"):
        probe._validate_password("alllowercase123")
    with pytest.raises(ValidationError, match="digit"):
        probe._validate_password("NoDigitsHere")


def test_auth_query_requires_existing_user_and_role(services):
    auth = services["auth_service"]
    user = auth.register_user("query-user", "StrongPass123")

    with pytest.raises(NotFoundError, match="User not found"):
        auth.get_user_permissions("missing-user-id")

    with pytest.raises(NotFoundError, match="Role not found"):
        auth.assign_role(user.id, "missing-role")


def test_auth_query_returns_roles_and_permissions(services):
    auth = services["auth_service"]
    user = auth.register_user("query-target", "StrongPass123")

    auth.assign_role(user.id, "planner")

    role_names = auth.get_user_role_names(user.id)
    assert "viewer" in role_names
    assert "planner" in role_names
    assert auth.has_permission(user.id, "task.manage")
    assert not auth.has_permission(user.id, "auth.manage")
