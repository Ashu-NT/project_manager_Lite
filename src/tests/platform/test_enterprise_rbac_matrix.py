from __future__ import annotations

import pytest

from src.api.desktop.platform import PlatformAccessDesktopApi, PlatformUserDesktopApi
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.modules.project_management.access.policy import (
    PROJECT_SCOPE_ROLE_CHOICES,
    normalize_project_scope_role,
    resolve_project_scope_permissions,
)
from src.tests.ui_runtime_helpers import login_as


def _platform_access_api(services) -> PlatformAccessDesktopApi:
    return PlatformAccessDesktopApi(access_service=services["access_service"])


def _platform_user_api(services) -> PlatformUserDesktopApi:
    return PlatformUserDesktopApi(auth_service=services["auth_service"])


def _access_scope_option_loaders(services):
    return {
        "project": lambda: [
            (project.name, project.id)
            for project in services["project_service"].list_projects()
        ]
    }


def test_security_and_payroll_roles_expose_expected_permissions(services):
    auth = services["auth_service"]

    security_user = auth.register_user(
        "security-admin-role",
        "StrongPass123",
        role_names=["security_admin"],
    )
    payroll_user = auth.register_user(
        "payroll-manager-role",
        "StrongPass123",
        role_names=["payroll_manager"],
    )
    inventory_user = auth.register_user(
        "inventory-manager-role",
        "StrongPass123",
        role_names=["inventory_manager"],
    )

    security_permissions = auth.get_user_permissions(security_user.id)
    payroll_permissions = auth.get_user_permissions(payroll_user.id)
    inventory_permissions = auth.get_user_permissions(inventory_user.id)

    assert "security.manage" in security_permissions
    assert "auth.read" in security_permissions
    assert "auth.manage" not in security_permissions
    assert "task.manage" not in security_permissions

    assert "payroll.read" in payroll_permissions
    assert "payroll.manage" in payroll_permissions
    assert "payroll.approve" in payroll_permissions
    assert "payroll.export" in payroll_permissions
    assert "timesheet.approve" in payroll_permissions
    assert "timesheet.lock" in payroll_permissions
    assert "employee.read" in payroll_permissions
    assert "employee.manage" in payroll_permissions
    assert "site.read" in payroll_permissions
    assert "department.read" in payroll_permissions
    assert "auth.manage" not in payroll_permissions

    assert "inventory.read" in inventory_permissions
    assert "inventory.manage" in inventory_permissions
    assert "site.read" in inventory_permissions
    assert "party.read" in inventory_permissions
    assert "report.export" in inventory_permissions
    assert "import.manage" in inventory_permissions
    assert "approval.request" in inventory_permissions
    assert "settings.manage" not in inventory_permissions


def test_access_and_security_admin_capabilities_are_separated(services):
    auth = services["auth_service"]
    access = services["access_service"]
    project = services["project_service"].create_project("Access Admin Project")
    target = auth.register_user("locked-target", "StrongPass123", role_names=["viewer"])
    auth.register_user("access-admin-user", "StrongPass123", role_names=["access_admin"])
    auth.register_user(
        "security-admin-user",
        "StrongPass123",
        role_names=["security_admin"],
    )

    access.assign_project_membership(project_id=project.id, user_id=target.id, scope_role="lead")

    login_as(services, "access-admin-user", "StrongPass123")
    memberships = access.list_project_memberships(project.id)
    assert len(memberships) == 1
    assert memberships[0].scope_role == "lead"
    assert len(auth.list_users()) >= 3
    with pytest.raises(BusinessRuleError, match="security.manage"):
        auth.unlock_user_account(target.id)

    login_as(services, "security-admin-user", "StrongPass123")
    assert len(auth.list_users()) >= 3
    assert len(auth.list_roles()) >= 1
    auth.unlock_user_account(target.id)
    with pytest.raises(BusinessRuleError, match="auth.manage"):
        auth.register_user("blocked-by-security-admin", "StrongPass123")


def test_project_scope_roles_are_canonical_and_editor_is_compatibility_alias():
    assert PROJECT_SCOPE_ROLE_CHOICES == ("viewer", "contributor", "lead", "owner")
    assert normalize_project_scope_role("editor") == "contributor"
    assert resolve_project_scope_permissions("editor") == resolve_project_scope_permissions("contributor")
    assert "task.manage" not in resolve_project_scope_permissions("viewer")
    assert "task.manage" in resolve_project_scope_permissions("contributor")
    assert "cost.manage" in resolve_project_scope_permissions("lead")
    assert "project.manage" not in resolve_project_scope_permissions("lead")
    assert "project.manage" in resolve_project_scope_permissions("owner")

