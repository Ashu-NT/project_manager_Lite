from __future__ import annotations

import pytest

from src.core.platform.application.security.auth.auth_validation_policy import (
    AuthValidationPolicy,
)
from src.core.platform.common.exceptions import NotFoundError, ValidationError


def test_auth_validation_normalizes_and_validates_email():
    policy = AuthValidationPolicy()
    assert policy.normalize_email("  USER.Name@Example.COM  ") == "user.name@example.com"
    assert policy.normalize_email("   ") is None

    policy.validate_email(None)
    with pytest.raises(ValidationError, match="Invalid email format"):
        policy.validate_email("not-an-email")


def test_auth_validation_rejects_weak_password_shapes():
    policy = AuthValidationPolicy()
    with pytest.raises(ValidationError, match="at least 8"):
        policy.validate_password("Short1")
    with pytest.raises(ValidationError, match="uppercase"):
        policy.validate_password("alllowercase123")
    with pytest.raises(ValidationError, match="digit"):
        policy.validate_password("NoDigitsHere")


def test_auth_query_requires_existing_user_and_role(services):
    user = services["user_registration"].register_user("query-user", "StrongPass123")

    with pytest.raises(NotFoundError, match="User not found"):
        services["auth_queries"].get_user_permissions("missing-user-id")

    with pytest.raises(NotFoundError, match="Role not found"):
        services["role_assignment_commands"].assign_role(user.id, "missing-role")


def test_auth_query_returns_roles_and_permissions(services):
    tenant_id = services[
        "tenant_context_service"
    ].require_active_tenant_id(operation_label="test canonical auth query")
    user = services["user_registration"].register_user(
        "query-target",
        "StrongPass123",
        role_names=["viewer"],
        tenant_id=tenant_id,
    )

    services["role_assignment_commands"].assign_role(user.id, "planner")

    role_names = services["auth_queries"].get_user_role_names(user.id)
    assert "viewer" in role_names
    assert "planner" in role_names
    assert services["auth_queries"].has_permission(user.id, "task.manage")
    assert not services["auth_queries"].has_permission(user.id, "auth.manage")

