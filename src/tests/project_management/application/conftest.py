from datetime import datetime, timezone

import pytest

from src.core.platform.infrastructure.persistence.orm.integration.accounting_connector import AccountingConnectorORM
from src.core.platform.infrastructure.persistence.orm.tenant.modules.modules import ModuleEntitlementORM


@pytest.fixture
def accounting_services(monkeypatch, request):
    from src.infra.composition import accounting_integration

    original = accounting_integration.build_accounting_capability

    def configured(**kwargs):
        kwargs["installed_adapters"] = frozenset({"test_connector"})
        return original(**kwargs)

    monkeypatch.setattr(accounting_integration, "build_accounting_capability", configured)
    services = request.getfixturevalue("services")
    session = request.getfixturevalue("session")
    scope = services["tenant_context_service"].require_active_scope_ids(operation_label="seed connector")
    session.merge(ModuleEntitlementORM(
        tenant_id=scope.tenant_id, organization_id=scope.organization_id,
        module_code="accounting_integration", enabled=True, licensed=True,
        lifecycle_status="active", updated_at=datetime.now(timezone.utc),
    ))
    session.add(AccountingConnectorORM(
        tenant_id=scope.tenant_id, organization_id=scope.organization_id,
        adapter_id="test_connector", connection_id="test_connection", secret_reference="test_secret_ref",
        enabled=True, version=1,
    ))
    session.commit()
    return services
