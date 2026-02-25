from __future__ import annotations

import pytest

from core.exceptions import BusinessRuleError


def _login_as(services, username: str, password: str):
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


def test_user_session_enforces_manage_permissions(services):
    auth = services["auth_service"]
    auth.register_user("viewer1", "StrongPass123", role_names=["viewer"])
    _login_as(services, "viewer1", "StrongPass123")

    ps = services["project_service"]
    with pytest.raises(BusinessRuleError, match="Permission denied"):
        ps.create_project("Forbidden project")


def test_admin_session_can_execute_manage_operations(services):
    _login_as(services, "admin", "ChangeMe123!")

    ps = services["project_service"]
    p = ps.create_project("Allowed project")
    assert p.id

