import pytest
from sqlalchemy import text

from src.core.modules.project_management.contracts.reads.financials.models.finance_billing_facts import (
    AccountingStatusQuery,
)
from src.core.modules.project_management.infrastructure.persistence.reads.financials.sqlalchemy_finance_billing_reader import (
    SqlAlchemyFinanceBillingReader,
)
from src.tests.integration.postgresql.test_r6f_billing_concurrency import (
    billing_scope,  # noqa: F401
)
from src.tests.integration.postgresql.test_r6g_b_accounting_handoff import (
    handoff_scope,  # noqa: F401
)
from src.tests.integration.postgresql.test_r6g_c_accounting_delivery import (
    external_worker,  # noqa: F401
)
from src.tests.integration.postgresql.test_r6g_d_accounting_outcomes import (
    inbound,  # noqa: F401
)
from src.tests.project_management.infrastructure.test_r6b_billing_reader import (
    _statement_count,
)

pytestmark = pytest.mark.postgresql_integration


def test_provider_timestamp_cannot_regress_reconciled_operator_state(request, postgres_test_environment):
    send, scope, _, _, _ = request.getfixturevalue("inbound")
    assert send(occurred_at="2027-01-01T00:00:00Z") == "processed"
    assert send(
        external_event_id="reconciled", sequence=2, outcome="reconciled",
        reconciliation_reference="recon-2", occurred_at="2026-09-01T00:00:00Z",
    ) == "processed"
    with postgres_test_environment.runtime_session(tenant_id=scope.tenant, organization_id=scope.org) as db:
        item = SqlAlchemyFinanceBillingReader(session=db).list_accounting_statuses(
            tenant_id=scope.tenant, organization_id=scope.org, project_id=scope.project,
            request=AccountingStatusQuery(),
        ).items[0]
        assert item.latest_external_status == "reconciled"
        assert item.latest_reconciliation_reference == "recon-2"
        assert item.delivery.external_sequence == 2


def test_operator_projection_uses_runtime_rls_and_authenticated_evidence(
    request, postgres_test_environment
):
    send, scope, _, _, _ = request.getfixturevalue("inbound")
    assert send() == "processed"
    assert send(outcome="rejected") == "quarantined"
    env = postgres_test_environment
    with env.runtime_session(tenant_id=scope.tenant, organization_id=scope.org) as db:
        assert db.scalar(text("SELECT current_user")) == "app_runtime"
        assert db.execute(
            text(
                "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user"
            )
        ).one() == (False, False)
        with _statement_count(db) as statements:
            page = SqlAlchemyFinanceBillingReader(session=db).list_accounting_statuses(
                tenant_id=scope.tenant,
                organization_id=scope.org,
                project_id=scope.project,
                request=AccountingStatusQuery(),
            )
        # Session context establishment is separate from the four bounded Reader projections.
        assert len([sql for sql in statements if "set_config" not in sql]) == 4
        item = page.items[0]
        assert item.latest_external_status == "acknowledged"
        assert item.delivery.transport_state == "published"
        assert item.delivery.quarantined_count == 1
        assert item.delivery.latest_quarantine_id is not None
        assert item.delivery.external_sequence == 1
        assert "never-persist" not in repr(page)
    for tenant, org in (
        ("foreign", scope.org),
        (scope.tenant, "foreign"),
        (None, None),
    ):
        with env.runtime_session(tenant_id=tenant, organization_id=org) as db:
            assert (
                SqlAlchemyFinanceBillingReader(session=db)
                .list_accounting_statuses(
                    tenant_id=scope.tenant,
                    organization_id=scope.org,
                    project_id=scope.project,
                    request=AccountingStatusQuery(),
                )
                .items
                == ()
            )
    with env.runtime_session(tenant_id=scope.tenant, organization_id=scope.org) as db:
        assert (
            SqlAlchemyFinanceBillingReader(session=db)
            .list_accounting_statuses(
                tenant_id=scope.tenant,
                organization_id=scope.org,
                project_id="foreign",
                request=AccountingStatusQuery(),
            )
            .items
            == ()
        )
