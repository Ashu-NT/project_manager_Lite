from __future__ import annotations


def test_project_scope_resolvers_are_registered_once_on_shared_platform_services(services) -> None:
    access = services["access_service"]
    auth = services["auth_service"]
    governance = services["role_governance_service"]

    assert "project" in access.list_supported_scope_types()
    assert (
        auth._canonical_role_resolver._scope_tenant_resolvers["project"]
        is access._scope_exists_resolvers["project"]
    )
    assert "project" in governance._scope_exists_resolvers
    assert "project" in governance._organization_owner_resolvers
    assert access._scope_exists_resolvers["project"]("missing-tenant", "missing-project") is False
