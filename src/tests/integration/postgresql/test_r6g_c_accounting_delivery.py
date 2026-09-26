from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import select, text

from src.core.modules.project_management.infrastructure.persistence.orm.accounting.handoff import (
    ProjectAccountingOutboxORM,
)
from src.core.modules.project_management.infrastructure.persistence.uow.finance.accounting_delivery import (
    AccountingWorkerScope,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.port.integration.external_accounting import (
    ExternalAccountingReceipt,
)
from src.infra.composition.accounting_delivery import (
    build_external_accounting_processor,
)
from src.tests.integration.postgresql.test_r6f_billing_concurrency import (
    billing_scope,  # noqa: F401
)
from src.tests.integration.postgresql.test_r6g_b_accounting_handoff import (
    boundary,
    handoff_scope,  # noqa: F401
)
from src.tests.integration.postgresql.test_r6g_b_accounting_handoff import (
    request as request_handoff,
)

pytestmark = pytest.mark.postgresql_integration


@pytest.fixture
def external_worker(postgres_test_environment, request):
    scope = request.getfixturevalue("handoff_scope")
    environment = postgres_test_environment
    request_handoff(boundary(environment, scope, scope.actors[0]), scope)
    actor = str(uuid4())
    name = "accounting-worker-" + actor
    with environment.admin_engine.begin() as db:
        db.execute(
            text(
                "INSERT INTO users (id, username, password_hash, account_type, is_active, created_at, updated_at, version) VALUES (:id, :id, 'no-login', 'service', true, :now, :now, 1)"
            ),
            {"id": actor, "now": datetime.now(timezone.utc)},
        )
        db.execute(
            text(
                "INSERT INTO service_principals (id, tenant_id, organization_id, user_id, name, status, created_at, updated_at) VALUES (:id, :tenant, :org, :id, :name, 'active', :now, :now)"
            ),
            {
                "id": actor,
                "tenant": scope.tenant,
                "org": scope.org,
                "name": name,
                "now": datetime.now(timezone.utc),
            },
        )
    adapter = Mock(supports_durable_idempotency=True)

    def deliver(*, evidence, target, credential):
        assert environment.runtime_engine.pool.checkedout() == 0
        return ExternalAccountingReceipt(
            handoff_id=evidence.handoff_id,
            payload_hash=evidence.payload_hash,
            source_version=evidence.source_version,
            adapter_id=target.adapter_id,
            connection_id=target.connection_id,
            remote_reference="durable-acceptance",
            accepted_at=datetime.now(timezone.utc),
        )

    adapter.deliver.side_effect = deliver
    credentials = Mock()
    credentials.resolve.return_value = SecretStr("never-persist")

    def make(project_id=None, organization_id=None):
        return build_external_accounting_processor(
            engine=environment.runtime_engine,
            scope=AccountingWorkerScope(
                scope.tenant, organization_id or scope.org, project_id or scope.project
            ),
            principal_name=name,
            adapters={"test_connector": adapter},
            credentials=credentials,
        )

    return make, scope, actor, adapter


def test_runtime_identity_network_boundary_and_durable_receipt(
    external_worker, postgres_test_environment
):
    make, scope, actor, _ = external_worker
    assert make().process_one()
    with postgres_test_environment.runtime_session(
        tenant_id=scope.tenant, organization_id=scope.org
    ) as db:
        row = db.scalars(select(ProjectAccountingOutboxORM)).one()
        assert row.status == "published"
        assert "never-persist" not in row.transport_receipt_json
        assert (
            db.scalar(
                text(
                    "SELECT actor_id FROM audit_entries WHERE operation='accounting_transport.finalize'"
                )
            )
            == actor
        )
        assert (
            db.scalar(
                text("SELECT status FROM project_billing_preparations WHERE id=:id"),
                {"id": scope.preparation},
            )
            == "delivered"
        )


def test_competing_runtime_claimers_get_one_lease(external_worker):
    make, _, _, _ = external_worker
    barrier = Barrier(2)

    def claim(_):
        worker = make()
        barrier.wait(timeout=10)
        return worker._transactions.claim()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, range(2)))
    assert sum(result is not None for result in results) == 1


def test_wrong_project_has_no_work_and_wrong_org_cannot_resolve_worker(external_worker):
    make, _, _, _ = external_worker
    assert make(project_id="wrong-project")._transactions.claim() is None
    with pytest.raises(BusinessRuleError):
        make(organization_id="wrong-org")._transactions.claim()


def test_disabled_service_identity_cannot_deliver(
    external_worker, postgres_test_environment
):
    make, _, actor, adapter = external_worker
    with postgres_test_environment.admin_engine.begin() as db:
        db.execute(
            text("UPDATE service_principals SET status='disabled' WHERE user_id=:id"),
            {"id": actor},
        )
    with pytest.raises(BusinessRuleError):
        make().process_one()
    adapter.deliver.assert_not_called()


def test_stale_finalize_cannot_overwrite_another_lease(
    external_worker, postgres_test_environment
):
    make, scope, _, adapter = external_worker
    processor = make()
    claim = processor._transactions.claim()
    receipt = adapter.deliver(
        evidence=claim.evidence, target=claim.target, credential=SecretStr("test")
    )
    with postgres_test_environment.runtime_session(
        tenant_id=scope.tenant, organization_id=scope.org
    ) as db:
        db.execute(
            text(
                "UPDATE project_accounting_outbox SET lease_token='another-worker', version=version+1"
            )
        )
        db.commit()
    with pytest.raises(BusinessRuleError):
        processor._transactions.finalize(claim, receipt)


@pytest.mark.parametrize("failure", ["audit", "commit"])
def test_finalize_failure_is_atomic_and_replay_is_idempotent(
    external_worker, postgres_test_environment, monkeypatch, failure
):
    from sqlalchemy.orm import Session

    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    make, scope, _, adapter = external_worker
    processor = make()
    claim = processor._transactions.claim()
    accepted = {}
    original = adapter.deliver.side_effect

    def idempotent_remote(**kwargs):
        evidence = kwargs["evidence"]
        if evidence.handoff_id not in accepted:
            accepted[evidence.handoff_id] = original(**kwargs)
        return accepted[evidence.handoff_id]

    adapter.deliver.side_effect = idempotent_remote
    result = processor._deliver(claim)

    def fail(*args, **kwargs):
        raise RuntimeError("injected finalization failure")

    with monkeypatch.context() as patch:
        patch.setattr(
            EnterpriseAuditService if failure == "audit" else Session,
            "record" if failure == "audit" else "commit",
            fail,
        )
        with pytest.raises(RuntimeError):
            processor._transactions.finalize(claim, result)
    with postgres_test_environment.runtime_session(
        tenant_id=scope.tenant, organization_id=scope.org
    ) as db:
        row = db.scalars(select(ProjectAccountingOutboxORM)).one()
        assert row.status == "claimed" and row.transport_receipt_json is None
        assert (
            db.scalar(
                text(
                    "SELECT count(*) FROM audit_entries WHERE operation='accounting_transport.finalize'"
                )
            )
            == 0
        )
        assert (
            db.scalar(
                text("SELECT status FROM project_billing_preparations WHERE id=:id"),
                {"id": scope.preparation},
            )
            == "delivery_pending"
        )
        db.execute(
            text(
                "UPDATE project_accounting_outbox SET lease_expires_at=now()-interval '1 second'"
            )
        )
        db.commit()
    assert make().process_one()
    assert len(accepted) == 1
    assert (
        adapter.deliver.call_args_list[0].kwargs["evidence"]
        == adapter.deliver.call_args_list[1].kwargs["evidence"]
    )


def test_configuration_disable_and_repair_keeps_pinned_destination(
    external_worker, postgres_test_environment
):
    from src.core.platform.contract.port.integration.external_accounting import (
        ExternalAccountingFailureKind,
    )

    make, scope, _, adapter = external_worker
    processor = make()
    claim = processor._transactions.claim()
    processor._transactions.finalize(claim, ExternalAccountingFailureKind.RETRYABLE)
    with postgres_test_environment.runtime_session(
        tenant_id=scope.tenant, organization_id=scope.org
    ) as db:
        db.execute(
            text(
                "UPDATE organization_accounting_connectors SET enabled=false, version=version+1"
            )
        )
        db.execute(
            text(
                "UPDATE project_accounting_outbox SET available_at=now()-interval '1 second'"
            )
        )
        db.commit()
    processor.process_one()
    adapter.deliver.assert_not_called()
    with postgres_test_environment.runtime_session(
        tenant_id=scope.tenant, organization_id=scope.org
    ) as db:
        db.execute(
            text(
                "UPDATE organization_accounting_connectors SET enabled=true, connection_id='different', version=version+1"
            )
        )
        db.execute(
            text(
                "UPDATE project_accounting_outbox SET available_at=now()-interval '1 second'"
            )
        )
        db.commit()
    processor.process_one()
    adapter.deliver.assert_not_called()
    with postgres_test_environment.runtime_session(
        tenant_id=scope.tenant, organization_id=scope.org
    ) as db:
        db.execute(
            text(
                "UPDATE organization_accounting_connectors SET connection_id='test_connection', version=version+1"
            )
        )
        db.execute(
            text(
                "UPDATE project_accounting_outbox SET available_at=now()-interval '1 second'"
            )
        )
        db.commit()
    assert processor.process_one()
    adapter.deliver.assert_called_once()


def test_final_attempt_expiry_and_target_immutability(
    external_worker, postgres_test_environment
):
    from sqlalchemy.exc import DBAPIError

    make, scope, _, _ = external_worker
    claim = make()._transactions.claim()
    with postgres_test_environment.runtime_session(
        tenant_id=scope.tenant, organization_id=scope.org
    ) as db:
        with pytest.raises(DBAPIError):
            db.execute(
                text(
                    "UPDATE project_accounting_outbox SET target_connection_id='hostile'"
                )
            )
        db.rollback()
        db.execute(
            text(
                "UPDATE project_accounting_outbox SET max_attempts=1, lease_expires_at=now()-interval '1 second'"
            )
        )
        db.commit()
    assert make()._transactions.claim() is None
    with postgres_test_environment.runtime_session(
        tenant_id=scope.tenant, organization_id=scope.org
    ) as db:
        row = db.get(ProjectAccountingOutboxORM, claim.outbox_id)
        assert row.attempt_count == 1 and row.status == "dead_letter"


def test_skip_locked_does_not_wait_for_another_claim_transaction(
    external_worker, postgres_test_environment
):
    make, scope, _, _ = external_worker
    with postgres_test_environment.runtime_session(
        tenant_id=scope.tenant, organization_id=scope.org
    ) as held:
        held.execute(select(ProjectAccountingOutboxORM).with_for_update()).one()
        with ThreadPoolExecutor(max_workers=1) as pool:
            assert pool.submit(make()._transactions.claim).result(timeout=5) is None
        held.rollback()
    assert make()._transactions.claim() is not None


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_id", "wrong-preparation"),
        ("source_version", 99),
        ("payload_bytes", b"wrong"),
    ],
)
def test_forged_claim_evidence_cannot_finalize(external_worker, field, value):
    make, _, _, adapter = external_worker
    processor = make()
    claim = processor._transactions.claim()
    receipt = adapter.deliver(
        evidence=claim.evidence, target=claim.target, credential=SecretStr("test")
    )
    forged = claim.model_copy(
        update={"evidence": claim.evidence.model_copy(update={field: value})}
    )
    with pytest.raises(BusinessRuleError):
        processor._transactions.finalize(forged, receipt)
