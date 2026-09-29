import pytest
from sqlalchemy import event, text

from src.core.modules.project_management.domain.financials.accounting.handoff import (
    AccountingHandoffSnapshot,
)
from src.core.platform.integration.events import IntegrationEventEnvelope
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


def test_claim_plan_is_bounded_and_network_is_detached(
    request, postgres_test_environment
):
    make, scope, _, adapter = request.getfixturevalue("external_worker")
    worker = make()
    statements = []

    def capture(_connection, _cursor, statement, parameters, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append((statement, parameters))

    engine = postgres_test_environment.runtime_engine
    event.listen(engine, "before_cursor_execute", capture)
    try:
        claim = worker._transactions.claim()
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert not adapter.deliver.called
    assert engine.pool.checkedout() == 0
    queries = [(sql, params) for sql, params in statements if "SKIP LOCKED" in sql]
    assert len(queries) == 1
    sql, parameters = queries[0]
    assert "LIMIT" in sql
    with postgres_test_environment.runtime_session(
        tenant_id=scope.tenant, organization_id=scope.org
    ) as db:
        plan = (
            db.connection()
            .exec_driver_sql(
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql, parameters
            )
            .scalar_one()[0]
        )
    assert plan["Plan"]["Node Type"] == "Limit"
    result = worker._deliver(claim)
    assert engine.pool.checkedout() == 0
    worker._transactions.finalize(claim, result)
    print(
        f"R6G-F claim SELECT count={len(statements)}; plan={plan['Plan']['Node Type']}; execution_ms={plan['Execution Time']}"
    )


def test_connector_removal_preserves_neutral_handoff_and_event(
    request, postgres_test_environment
):
    make, scope, _, _ = request.getfixturevalue("external_worker")
    claim = make()._transactions.claim()
    env = postgres_test_environment
    with env.admin_engine.begin() as db:
        db.execute(
            text(
                "DELETE FROM organization_accounting_connectors WHERE tenant_id=:t AND organization_id=:o"
            ),
            {"t": scope.tenant, "o": scope.org},
        )
    with env.runtime_session(tenant_id=scope.tenant, organization_id=scope.org) as db:
        payload = db.execute(
            text(
                "SELECT payload_bytes, payload_hash FROM project_accounting_handoffs WHERE id=:id"
            ),
            {"id": claim.evidence.handoff_id},
        ).one()
        envelope_json = db.scalar(
            text(
                "SELECT envelope_json FROM project_accounting_outbox WHERE event_id=:id"
            ),
            {"id": claim.evidence.handoff_id},
        )
    # A future consumer needs only the neutral persisted contracts, not an adapter,
    # connection, secret resolver or external worker to deserialize approved facts.
    snapshot = AccountingHandoffSnapshot.model_validate_json(
        bytes(payload.payload_bytes)
    )
    envelope = IntegrationEventEnvelope.model_validate_json(envelope_json)
    assert snapshot.canonical_bytes == claim.evidence.payload_bytes
    assert snapshot.content_hash == payload.payload_hash == claim.evidence.payload_hash
    assert envelope.event_id == snapshot.handoff_id
    assert envelope.payload["handoff_id"] == snapshot.handoff_id
    assert snapshot.evidence.project_id == scope.project
    assert snapshot.approved_preparation_version == claim.evidence.source_version


def test_fresh_worker_recovers_committed_claim_without_rebuilding(
    request, postgres_test_environment
):
    make, scope, _, adapter = request.getfixturevalue("external_worker")
    first = make()._transactions.claim()
    # Simulate a process dying after claim commit, before any network call.
    with postgres_test_environment.admin_engine.begin() as db:
        db.execute(
            text(
                "UPDATE project_accounting_outbox SET lease_expires_at=now()-interval '1 second', available_at=now()-interval '1 second' WHERE event_id=:id"
            ),
            {"id": first.evidence.handoff_id},
        )
    assert make().process_one()
    delivered = adapter.deliver.call_args.kwargs["evidence"]
    assert delivered.payload_bytes == first.evidence.payload_bytes
    assert delivered.payload_hash == first.evidence.payload_hash
    assert delivered.handoff_id == first.evidence.handoff_id
    with postgres_test_environment.runtime_session(
        tenant_id=scope.tenant, organization_id=scope.org
    ) as db:
        assert (
            db.scalar(
                text("SELECT count(*) FROM project_accounting_handoffs WHERE id=:id"),
                {"id": delivered.handoff_id},
            )
            == 1
        )
        assert (
            db.scalar(
                text("SELECT status FROM project_accounting_outbox WHERE event_id=:id"),
                {"id": delivered.handoff_id},
            )
            == "published"
        )
