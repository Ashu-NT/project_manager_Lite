import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from unittest.mock import Mock

import pytest
from pydantic import SecretBytes
from sqlalchemy import text

from src.core.platform.contract.port.integration.accounting_outcomes import (
    AuthenticatedAccountingConnection,
)
from src.infra.composition.integration.accounting.accounting_outcomes import (
    build_external_accounting_ingress,
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

pytestmark = pytest.mark.postgresql_integration


@pytest.fixture
def inbound(request, postgres_test_environment):
    make, scope, actor, _ = request.getfixturevalue("external_worker")
    assert make().process_one()
    env = postgres_test_environment
    with env.runtime_session(tenant_id=scope.tenant, organization_id=scope.org) as db:
        handoff = db.execute(
            text(
                "SELECT id, approved_version, payload_hash FROM project_accounting_handoffs WHERE project_id=:p"
            ),
            {"p": scope.project},
        ).one()
        connection = db.execute(
            text(
                "SELECT adapter_id, connection_id FROM organization_accounting_connectors"
            )
        ).one()
    auth = Mock()
    auth.authenticate.return_value = AuthenticatedAccountingConnection(
        tenant_id=scope.tenant,
        organization_id=scope.org,
        adapter_id=connection.adapter_id,
        connection_id=connection.connection_id,
        principal_name="accounting-worker-" + actor,
        authoritative_sequence=True,
    )
    payload = {
        "schema_name": "external_accounting_outcome",
        "schema_version": 1,
        "external_event_id": "event-1",
        "tenant_id": scope.tenant,
        "organization_id": scope.org,
        "handoff_id": handoff.id,
        "approved_source_version": handoff.approved_version,
        "handoff_payload_hash": handoff.payload_hash,
        "outcome": "acknowledged",
        "sequence": 1,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    ingress = build_external_accounting_ingress(
        engine=env.runtime_engine, authenticator=auth
    )

    def send(**changes):
        return ingress.receive(
            body=json.dumps({**payload, **changes}).encode(),
            authentication=SecretBytes(b"test-authenticated"),
        )

    return send, scope, payload, ingress, auth


def _counts(env, scope):
    with env.runtime_session(tenant_id=scope.tenant, organization_id=scope.org) as db:
        return (
            db.scalar(
                text(
                    "SELECT count(*) FROM project_billing_external_events WHERE project_id=:p AND external_system='external_accounting'"
                ),
                {"p": scope.project},
            ),
            db.scalar(
                text(
                    "SELECT count(*) FROM project_finance_inbox_receipts WHERE consumer_name='project_management.accounting_outcomes.v1' AND status='processed'"
                )
            ),
            db.scalar(
                text("SELECT status FROM project_billing_preparations WHERE id=:p"),
                {"p": scope.preparation},
            ),
        )


def test_real_consumer_exact_replay_and_reconciliation(
    inbound, postgres_test_environment
):
    send, scope, _, _, _ = inbound
    assert send() == "processed"
    assert send() == "duplicate"
    assert (
        send(
            external_event_id="event-2",
            sequence=2,
            outcome="reconciled",
            reconciliation_reference="reconciliation-1",
        )
        == "processed"
    )
    assert _counts(postgres_test_environment, scope) == (2, 2, "reconciled")


@pytest.mark.parametrize(
    "changes",
    [
        {"handoff_id": "unknown"},
        {"approved_source_version": 999},
        {"handoff_payload_hash": "a" * 64},
        {"tenant_id": "foreign"},
        {"organization_id": "foreign"},
        {"project_id": "foreign"},
        {"schema_version": 2},
        {"outcome": "reconciled", "reconciliation_reference": "r"},
    ],
)
def test_hostile_input_quarantines_without_business_effect(
    inbound, postgres_test_environment, changes
):
    send, scope, _, _, _ = inbound
    assert send(**changes) == "quarantined"
    assert _counts(postgres_test_environment, scope) == (0, 0, "delivered")


@pytest.mark.parametrize(
    "changes",
    [
        {"outcome": "rejected"},
        {"handoff_id": "another-handoff"},
        {"approved_source_version": 999},
    ],
)
def test_changed_duplicate_preserves_established_truth(
    inbound, postgres_test_environment, changes
):
    send, scope, _, _, _ = inbound
    assert send() == "processed"
    assert send(**changes) == "quarantined"
    assert _counts(postgres_test_environment, scope)[::2] == (1, "acknowledged")


def test_concurrent_duplicate_has_one_effect(inbound, postgres_test_environment):
    send, scope, _, _, _ = inbound
    barrier = Barrier(2)

    def deliver():
        barrier.wait(timeout=5)
        return send()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: deliver(), range(2)))
    assert sorted(results) == ["duplicate", "processed"]
    assert _counts(postgres_test_environment, scope) == (1, 1, "acknowledged")


@pytest.mark.parametrize("sequence", [1, 2])
def test_old_or_equal_sequence_cannot_regress(
    inbound, postgres_test_environment, sequence
):
    send, scope, _, _, _ = inbound
    assert send(sequence=2) == "processed"
    assert (
        send(external_event_id="old", sequence=sequence, outcome="rejected")
        == "quarantined"
    )
    assert _counts(postgres_test_environment, scope)[::2] == (1, "acknowledged")


def test_business_rejection_does_not_reject_pm_approval(
    inbound, postgres_test_environment
):
    send, scope, _, _, _ = inbound
    assert send(outcome="rejected") == "processed"
    assert send(external_event_id="later", sequence=2) == "quarantined"
    assert _counts(postgres_test_environment, scope)[::2] == (1, "delivered")


@pytest.mark.parametrize("stage", ["audit", "mutation", "commit"])
def test_atomic_failure_rolls_back_every_effect(
    inbound, postgres_test_environment, monkeypatch, stage
):
    from sqlalchemy.orm import Session

    from src.core.modules.project_management.infrastructure.persistence.repositories.finance.invoicing.billing import (
        SqlAlchemyProjectBillingRepository,
    )
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    send, scope, _, ingress, _ = inbound
    notifications = Mock()
    ingress._consumer._bus = notifications
    target, name = {
        "audit": (EnterpriseAuditService, "record"),
        "mutation": (SqlAlchemyProjectBillingRepository, "add_external_event"),
        "commit": (Session, "commit"),
    }[stage]
    with monkeypatch.context() as patch:
        patch.setattr(target, name, Mock(side_effect=RuntimeError("injected")))
        with pytest.raises(RuntimeError, match="injected"):
            send()
    assert _counts(postgres_test_environment, scope) == (0, 0, "delivered")
    notifications.publish.assert_not_called()
    assert send() == "processed"


def test_malformed_production_ingress_retains_only_safe_fingerprint(inbound, postgres_test_environment):
    _, scope, _, ingress, _ = inbound
    assert ingress.receive(body=b'{"secret":"must-not-persist"', authentication=SecretBytes(b"auth-header")) == "quarantined"
    assert _counts(postgres_test_environment, scope) == (0,0,"delivered")
    with postgres_test_environment.runtime_session(tenant_id=scope.tenant, organization_id=scope.org) as db:
        evidence = db.scalar(text("SELECT envelope_json FROM project_finance_inbox_receipts WHERE consumer_name='project_management.accounting_quarantine.v1'"))
        assert "must-not-persist" not in evidence
        assert "auth-header" not in evidence
        assert "body_sha256" in evidence


@pytest.mark.parametrize(
    "field,value",
    [
        ("tenant_id", "foreign"),
        ("organization_id", "foreign"),
        ("connection_id", "foreign"),
        ("principal_name", "unknown"),
    ],
)
def test_auth_context_is_revalidated_against_configuration_and_service_identity(
    inbound, field, value
):
    send, _, _, _, auth = inbound
    auth.authenticate.return_value = auth.authenticate.return_value.model_copy(
        update={field: value}
    )
    # Tenant/org payload claims cannot rescue an unknown scoped service identity.
    with pytest.raises(Exception):
        send()


def test_disabled_connection_blocks_new_ingress_without_erasing_history(
    inbound, postgres_test_environment
):
    from src.core.platform.application.integration.accounting.outcome_ingress import (
        AccountingIngressAuthenticationError,
    )

    send, scope, _, _, _ = inbound
    assert send() == "processed"
    with postgres_test_environment.admin_engine.begin() as db:
        db.execute(
            text(
                "UPDATE organization_accounting_connectors SET enabled=false WHERE tenant_id=:t AND organization_id=:o"
            ),
            {"t": scope.tenant, "o": scope.org},
        )
    with pytest.raises(AccountingIngressAuthenticationError):
        send(external_event_id="disabled-event", sequence=2)
    assert _counts(postgres_test_environment, scope) == (1, 1, "acknowledged")


@pytest.mark.parametrize(
    "tenant,org", [(None, None), ("foreign", "foreign"), ("same", "foreign")]
)
def test_inbox_and_quarantine_rls(inbound, postgres_test_environment, tenant, org):
    send, scope, _, _, _ = inbound
    assert send(schema_version=2) == "quarantined"
    assert send() == "processed"
    with postgres_test_environment.runtime_session(
        tenant_id=scope.tenant if tenant == "same" else tenant, organization_id=org
    ) as db:
        assert (
            db.scalar(text("SELECT count(*) FROM project_finance_inbox_receipts")) == 0
        )
        assert (
            db.scalar(text("SELECT count(*) FROM project_billing_external_events")) == 0
        )


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE project_finance_inbox_receipts SET envelope_json='{}' WHERE consumer_name='project_management.accounting_outcomes.v1'",
        "DELETE FROM project_finance_inbox_receipts WHERE consumer_name='project_management.accounting_quarantine.v1'",
        "UPDATE project_billing_external_events SET external_status='paid' WHERE external_system='external_accounting'",
    ],
)
def test_database_preserves_authenticated_evidence(
    inbound, postgres_test_environment, statement
):
    from sqlalchemy.exc import DBAPIError

    send, scope, _, _, _ = inbound
    assert send() == "processed"
    assert send(schema_version=2) == "quarantined"
    with postgres_test_environment.runtime_session(
        tenant_id=scope.tenant, organization_id=scope.org
    ) as db:
        with pytest.raises(DBAPIError, match="immutable"):
            db.execute(text(statement))
        db.rollback()


def test_committed_outcomes_only_emit_narrow_invalidation(
    inbound, postgres_test_environment
):
    from src.core.modules.project_management.application.financials.invoicing.billing_events import (
        BillingPreparationExternalOutcomeRecorded,
    )
    from src.core.modules.project_management.application.financials.invoicing.event_handlers.view_invalidation import (
        build_billing_view_invalidation_handler,
    )
    from src.infra.events.in_process_post_commit_event_bus import (
        InProcessPostCommitEventBus,
    )

    send, scope, _, ingress, _ = inbound
    bus = InProcessPostCommitEventBus()
    channel = Mock()
    handler = build_billing_view_invalidation_handler(channel)
    snapshots = []

    def after_commit(event, context):
        snapshots.append(_counts(postgres_test_environment, scope))
        handler(event, context)

    bus.subscribe(BillingPreparationExternalOutcomeRecorded, after_commit)
    ingress._consumer._bus = bus
    assert send() == "processed"
    assert send() == "duplicate"
    assert (
        send(
            external_event_id="event-2",
            sequence=2,
            outcome="reconciled",
            reconciliation_reference="r",
        )
        == "processed"
    )
    assert snapshots == [(1, 1, "acknowledged"), (2, 2, "reconciled")]
    assert channel.notify.call_count == 2
    for call in channel.notify.call_args_list:
        hint = call.args[0]
        assert hint.scope_code == "billing_transport"
        assert hint.scope.entity_id == scope.project


def test_new_connection_cannot_consume_a_handoff_pinned_elsewhere(inbound, postgres_test_environment):
    send, scope, _, _, auth = inbound
    with postgres_test_environment.admin_engine.begin() as db:
        db.execute(text("UPDATE organization_accounting_connectors SET connection_id='replacement' WHERE tenant_id=:t AND organization_id=:o"), {"t":scope.tenant,"o":scope.org})
    auth.authenticate.return_value = auth.authenticate.return_value.model_copy(update={"connection_id":"replacement"})
    assert send() == "quarantined"
    assert _counts(postgres_test_environment, scope) == (0,0,"delivered")


def test_external_business_evidence_requires_scoped_preparation_parent(inbound, postgres_test_environment):
    from uuid import uuid4

    from sqlalchemy.exc import DBAPIError
    _, scope, _, _, _ = inbound
    with postgres_test_environment.runtime_session(tenant_id=scope.tenant, organization_id=scope.org) as db:
        with pytest.raises(DBAPIError, match="foreign key"):
            db.execute(text("""INSERT INTO project_billing_external_events
                (id,tenant_id,organization_id,project_id,preparation_id,event_type,external_system,external_status,idempotency_key,occurred_at,message,recorded_at)
                VALUES (:id,:t,:o,:p,'foreign-preparation','delivery_accepted','external_accounting','acknowledged',:id,CURRENT_TIMESTAMP,'',CURRENT_TIMESTAMP)"""),
                {"id":str(uuid4()),"t":scope.tenant,"o":scope.org,"p":scope.project})
        db.rollback()
