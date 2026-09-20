from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from decimal import Decimal
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import text

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.rate_cards.rate_card_resolver import (
    RateCardResolver,
)
from src.core.modules.project_management.domain.financials.billing_preparation import (
    ProjectBillingPreparation,
)
from src.core.modules.project_management.domain.financials.billing_profile import (
    ProjectBillingProfile,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.invoicing.billing import (
    SqlAlchemyProjectBillingRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.rate_cards.rate_resolution_reader import (
    SqlAlchemyRateResolutionReader,
)
from src.core.platform.domain.security.auth.session import (
    UserSessionContext,
    UserSessionPrincipal,
)
from src.infra.composition.approval_apply_dependencies.billing_preparation import (
    build_billing_preparation_approval_deps,
)
from src.infra.persistence.db.postgresql_rls import validate_postgresql_execution_role
from src.tests.integration.postgresql import (
    test_r6d_d_approved_time_labor_posting as labor,
)

pytestmark = pytest.mark.postgresql_integration


def test_billing_rate_race_preserves_complete_immutable_snapshot(postgres_test_environment):
    env = postgres_test_environment
    with env.admin_engine.connect() as connection:
        exists = connection.scalar(text("SELECT EXISTS (SELECT 1 FROM tenants WHERE id=:id)"), {"id": labor.TENANT_A})
    if not exists:
        labor.seed_approved_time_scope(env)
    suffix = uuid4().hex
    envelope = labor._approved_time_envelope(suffix)
    session, outbox, dispatcher = labor._build_dispatcher(env)
    try:
        outbox.enqueue(envelope)
        session.commit()
        assert dispatcher.dispatch_pending(limit=1) == 1
    finally:
        session.close()
    card_id, line_id = str(uuid4()), str(uuid4())
    now = datetime.now(timezone.utc)
    with env.admin_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO project_finance_rate_cards (id, tenant_id, organization_id, project_id, name, version, is_active, created_at, updated_at) "
            "VALUES (:id, :tenant, :org, :project, 'Billing race', 1, true, :now, :now)"
        ), {"id": card_id, "tenant": labor.TENANT_A, "org": labor.ORG_A, "project": labor.PROJECT_A, "now": now})
        connection.execute(text(
            "INSERT INTO project_finance_rate_card_lines (id, tenant_id, organization_id, rate_card_id, rate_type, origin, resource_id, is_active, unit, rate_amount, rate_currency, version, created_at, updated_at) "
            "VALUES (:id, :tenant, :org, :card, 'billing', 'configured', :resource, true, 'HOUR', 120, 'USD', 1, :now, :now)"
        ), {"id": line_id, "tenant": labor.TENANT_A, "org": labor.ORG_A, "card": card_id, "resource": labor.RESOURCE_A, "now": now})
    scope = labor._TenantContext()
    user = UserSessionContext()
    permissions = frozenset({"finance.manage", "finance.read"})
    user.set_principal(UserSessionPrincipal(
        user_id="billing-rate-user", username="billing-rate-user", display_name="Billing",
        role_names=frozenset(), permissions=permissions, scoped_access={"project": {labor.PROJECT_A: permissions}},
        active_tenant_id=labor.TENANT_A, active_organization_id=labor.ORG_A,
    ))
    captured, edited = Event(), Event()

    class PausingReader(SqlAlchemyRateResolutionReader):
        def list_candidates(self, **kwargs):
            result = super().list_candidates(**kwargs)
            captured.set()
            assert edited.wait(10), "Rate editor did not complete"
            return result

    def prepare():
        with env.runtime_session(tenant_id=labor.TENANT_A, organization_id=labor.ORG_A) as session:
            validate_postgresql_execution_role(session)
            repo = SqlAlchemyProjectBillingRepository(session)
            repo._tenant_context_service = scope
            profile = ProjectBillingProfile.create(
                tenant_id=labor.TENANT_A, organization_id=labor.ORG_A, project_id=labor.PROJECT_A,
                currency_code="USD", contract_reference="Billing race", contract_value=Decimal("10000"),
                customer_party_id="customer", created_by="billing-rate-user",
            )
            profile.activate(actor_id="billing-rate-user", occurred_at=now)
            repo.add_profile(profile)
            session.flush()
            preparation = ProjectBillingPreparation.create(
                tenant_id=labor.TENANT_A, organization_id=labor.ORG_A, project_id=labor.PROJECT_A,
                billing_profile_id=profile.id, preparation_number=suffix, billing_method="time_and_materials",
                period_start=date(2026, 9, 1), period_end=date(2026, 9, 30), currency_code="USD",
                idempotency_key=suffix, created_by="billing-rate-user",
            )
            repo.add_preparation(preparation)
            session.flush()
            service = build_billing_preparation_approval_deps(
                session, user_session=user, tenant_context_service=scope,
            ).billing_preparation_service
            service._rate_resolver = RateCardResolver(reader=PausingReader(session), tenant_context_service=scope, clock=SystemClock())
            line = service.add_approved_time_source(preparation.id, time_entry_id=envelope.aggregate_id, expected_row_version=1)
            session.commit()
            return preparation.id, line

    def edit():
        assert captured.wait(10), "Billing did not read the Rate"
        with env.runtime_session(tenant_id=labor.TENANT_A, organization_id=labor.ORG_A) as session:
            validate_postgresql_execution_role(session)
            session.execute(text("UPDATE project_finance_rate_card_lines SET rate_amount=240, version=2 WHERE id=:id"), {"id": line_id})
            session.execute(text("UPDATE project_finance_rate_cards SET version=2 WHERE id=:id"), {"id": card_id})
            session.commit()
        edited.set()

    with ThreadPoolExecutor(max_workers=2) as executor:
        preparing = executor.submit(prepare)
        editing = executor.submit(edit)
        preparation_id, result = preparing.result(timeout=20)
        editing.result(timeout=20)
    assert (result.rate_card_version, result.rate_line_version, result.unit_rate) == (1, 1, Decimal("120"))
    assert result.quantity == Decimal("2.3750")
    assert result.net_amount == Decimal("285.00")
    with env.runtime_session(tenant_id=labor.TENANT_A, organization_id=labor.ORG_A) as session:
        repo = SqlAlchemyProjectBillingRepository(session)
        repo._tenant_context_service = scope
        saved = repo.list_preparation_lines(preparation_id)[0]
        assert (saved.rate_card_version, saved.rate_line_version, saved.unit_rate, saved.net_amount) == (1, 1, Decimal("120"), Decimal("285"))
        assert session.scalar(text("SELECT rate_amount FROM project_finance_rate_card_lines WHERE id=:id"), {"id": line_id}) == Decimal("240")
