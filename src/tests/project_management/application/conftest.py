from datetime import datetime, timezone

import pytest

from src.core.platform.infrastructure.persistence.orm.integration.accounting_connector import (
    AccountingConnectorORM,
)
from src.core.platform.infrastructure.persistence.orm.tenant.modules.modules import (
    ModuleEntitlementORM,
)


@pytest.fixture
def accounting_services(session):
    from src.infra.composition.app_container import build_service_dict

    services = build_service_dict(
        session, accounting_adapter_ids=frozenset({"test_connector"})
    )
    auth = services["auth_service"]
    admin = auth.authenticate("admin", "ChangeMe123!")
    services["user_session"].set_principal(auth.build_principal(admin))
    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="seed connector"
    )
    session.merge(
        ModuleEntitlementORM(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            module_code="accounting_integration",
            enabled=True,
            licensed=True,
            lifecycle_status="active",
            updated_at=datetime.now(timezone.utc),
        )
    )
    session.add(
        AccountingConnectorORM(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            adapter_id="test_connector",
            connection_id="test_connection",
            secret_reference="test_secret_ref",
            enabled=True,
            version=1,
        )
    )
    session.commit()
    return services


@pytest.fixture
def accounting_outcome(accounting_services, session):
    from src.tests.project_management.application.accounting_outcome_support import (
        outcome_sender,
    )
    return outcome_sender(accounting_services, session)
