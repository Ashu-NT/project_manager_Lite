import sys
sys.path.insert(0, ".")
import pytest

def test_diag(services, monkeypatch):
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.platform.context import PlatformWorkspaceCatalog
    from src.core.platform.infrastructure.persistence.uow.role_governance_unit_of_work import SqlAlchemyRoleGovernanceUnitOfWork

    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    catalog.adminAccessWorkspace.refresh()

    channel = services["platform_view_invalidation_channel"]
    from src.core.shared.events.view_invalidation import TenantWide
    tenant_id = services["tenant_context_service"].get_active_tenant_id()
    hints = []
    channel.subscribe(TenantWide(tenant_id), lambda h: hints.append(h))

    refresh_calls = []
    catalog.adminAccessWorkspace.refresh_role_bindings = lambda: refresh_calls.append("refresh") or None
    site = services["site_service"].create_site(
        site_code="DIAG-SITE", name="Diag Site", city="Berlin", currency_code="EUR"
    )
    user = services["auth_service"].register_user(
        "diag-user", "P5C3CommitFail123!", role_names=["inventory_manager"],
        tenant_id=tenant_id,
    )

    def _fail_commit(self):
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(SqlAlchemyRoleGovernanceUnitOfWork, "commit", _fail_commit)
    with pytest.raises(RuntimeError):
        services["access_service"].assign_scope_grant(
            scope_type="site", scope_id=site.id, user_id=user.id, scope_role="editor"
        )

    print("HINTS:", hints)
    print("REFRESH CALLS:", refresh_calls)
    assert refresh_calls == []
