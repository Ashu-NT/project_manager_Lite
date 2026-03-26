from __future__ import annotations

import pytest

from core.platform.access.authorization import require_scope_permission
from core.platform.auth.session import UserSessionContext, UserSessionPrincipal
from core.platform.common.exceptions import BusinessRuleError, ValidationError
from core.modules.project_management.access.policy import resolve_project_scope_permissions


def test_user_session_supports_generic_scoped_access_and_project_compatibility():
    user_session = UserSessionContext()
    user_session.set_principal(
        UserSessionPrincipal(
            user_id="user-1",
            username="scoped-user",
            display_name=None,
            role_names=frozenset({"viewer"}),
            permissions=frozenset({"task.read", "inventory.read"}),
            scoped_access={
                "project": {"project-1": frozenset({"task.read"})},
                "storeroom": {"storeroom-1": frozenset({"inventory.read"})},
            },
        )
    )

    assert user_session.has_scope_permission("project", "project-1", "task.read") is True
    assert user_session.has_project_permission("project-1", "task.read") is True
    assert user_session.has_scope_permission("project", "project-2", "task.read") is False
    assert user_session.has_scope_permission("storeroom", "storeroom-1", "inventory.read") is True
    assert user_session.has_any_scope_access("storeroom", "inventory.read") is True
    assert user_session.scope_ids_for("storeroom", "inventory.read") == {"storeroom-1"}
    assert user_session.is_scope_restricted("project") is True
    assert user_session.is_project_restricted() is True
    assert user_session.principal is not None
    assert user_session.principal.project_access == {"project-1": frozenset({"task.read"})}


def test_require_scope_permission_uses_generic_scope_model():
    user_session = UserSessionContext()
    user_session.set_principal(
        UserSessionPrincipal(
            user_id="user-2",
            username="project-reader",
            display_name=None,
            role_names=frozenset({"viewer"}),
            permissions=frozenset({"task.read"}),
            scoped_access={"project": {"project-1": frozenset({"task.read"})}},
        )
    )

    require_scope_permission(
        user_session,
        "project",
        "project-1",
        "task.read",
        operation_label="view project tasks",
    )

    with pytest.raises(BusinessRuleError, match="project 'project-2'"):
        require_scope_permission(
            user_session,
            "project",
            "project-2",
            "task.read",
            operation_label="view project tasks",
        )


def test_auth_build_principal_populates_generic_scoped_access_from_project_memberships(services):
    auth = services["auth_service"]
    access = services["access_service"]
    project = services["project_service"].create_project("Scoped Principal Project")
    user = auth.register_user("scoped-principal-user", "StrongPass123", role_names=["viewer"])

    access.assign_project_membership(
        project_id=project.id,
        user_id=user.id,
        scope_role="viewer",
    )

    principal = auth.build_principal(user)

    assert principal.scoped_access["project"][project.id] == frozenset(
        resolve_project_scope_permissions("viewer")
    )
    assert principal.project_access[project.id] == principal.scoped_access["project"][project.id]


def test_access_service_exposes_generic_scope_grant_wrappers_for_project_scope(services):
    auth = services["auth_service"]
    access = services["access_service"]
    project = services["project_service"].create_project("Generic Scope Grant Project")
    user = auth.register_user("generic-scope-user", "StrongPass123", role_names=["viewer"])

    grant = access.assign_scope_grant(
        scope_type="project",
        scope_id=project.id,
        user_id=user.id,
        scope_role="editor",
    )

    assert grant.scope_type == "project"
    assert grant.scope_id == project.id
    assert grant.scope_role == "contributor"
    assert grant.permission_codes == sorted(resolve_project_scope_permissions("contributor"))
    assert access.list_scope_role_choices("project") == ("viewer", "contributor", "lead", "owner")
    assert access.list_supported_scope_types() == ("project",)
    listed_scope_grants = access.list_scope_grants("project", project.id)
    listed_user_grants = access.list_user_scope_grants(user.id, scope_type="project")

    assert len(listed_scope_grants) == 1
    assert len(listed_user_grants) == 1
    assert listed_scope_grants[0].id == grant.id
    assert listed_scope_grants[0].scope_role == grant.scope_role
    assert listed_scope_grants[0].permission_codes == grant.permission_codes
    assert listed_user_grants[0].id == grant.id
    assert listed_user_grants[0].scope_role == grant.scope_role
    assert listed_user_grants[0].permission_codes == grant.permission_codes


def test_access_service_rejects_unsupported_scope_types_before_repository_calls(services):
    auth = services["auth_service"]
    access = services["access_service"]
    project = services["project_service"].create_project("Unsupported Scope Guardrail Project")
    user = auth.register_user("unsupported-scope-user", "StrongPass123", role_names=["viewer"])

    access.assign_project_membership(
        project_id=project.id,
        user_id=user.id,
        scope_role="viewer",
    )

    with pytest.raises(ValidationError, match="Unsupported scope type 'storeroom'"):
        access.list_scope_grants("storeroom", "storeroom-1")

    with pytest.raises(ValidationError, match="Unsupported scope type 'storeroom'"):
        access.list_user_scope_grants(user.id, scope_type="storeroom")

    with pytest.raises(ValidationError, match="Unsupported scope type 'storeroom'"):
        access.remove_scope_grant(scope_type="storeroom", scope_id="storeroom-1", user_id=user.id)
