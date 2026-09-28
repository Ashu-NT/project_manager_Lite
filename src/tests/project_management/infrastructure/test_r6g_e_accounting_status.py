import json
from dataclasses import replace
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from src.core.modules.project_management.api.desktop.financials.serializers.accounting_status_serializer import (
    serialize_accounting_status_page,
)
from src.core.modules.project_management.application.financials.accounting_status_capabilities import (
    with_accounting_capabilities,
)
from src.core.modules.project_management.contracts.reads.financials.models.accounting_delivery import (
    AccountingDeliveryFact,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_billing_facts import (
    AccountingStatusQuery,
)
from src.core.modules.project_management.infrastructure.persistence.orm.accounting.handoff import (
    ProjectAccountingHandoffORM,
    ProjectAccountingOutboxORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.billing import (
    ProjectBillingPreparationORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.finance_inbox import (
    ProjectFinanceInboxORM,
)
from src.core.platform.domain.integration.accounting.connector import (
    AccountingHandoffCapability,
    AccountingHandoffDenial,
)
from src.tests.project_management.infrastructure.test_r6b_billing_reader import (
    _seed_billing,
    _statement_count,
)


@pytest.fixture
def status_page(services):
    project, scope = _seed_billing(services)
    reader = services["finance_workspace_query"]._billing_reader
    return reader.list_accounting_statuses(
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        project_id=project.id,
        request=AccountingStatusQuery(page_size=1),
    )


def _delivery(state, failure=None):
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    return AccountingDeliveryFact(
        handoff_id="handoff",
        approved_source_version=2,
        requested_at=now,
        transport_state=state,
        adapter_id="adapter",
        connection_id="connection",
        attempt_count=0,
        max_attempts=5,
        next_attempt_at=now if state == "retry" else None,
        delivered_at=now if state == "published" else None,
        last_activity_at=now,
        failure_category=failure,
        receipt_reference=None,
    )


@pytest.mark.parametrize(
    "state,failure,label",
    [
        ("pending", None, "Queued"),
        ("claimed", None, "Delivery in progress"),
        ("retry", "retryable_transport", "Retry scheduled"),
        ("retry", "configuration_blocked", "Blocked configuration"),
        ("retry", "credential_failure", "Blocked configuration"),
        ("published", None, "Transport delivered"),
        ("dead_letter", "permanent_rejection", "Permanent transport failure"),
    ],
)
def test_transport_states_are_not_accounting_outcomes(
    status_page, state, failure, label
):
    item = replace(
        status_page.items[0],
        delivery=_delivery(state, failure),
        latest_external_message="SECRET remote error",
    )
    dto = serialize_accounting_status_page(replace(status_page, items=(item,))).items[0]
    assert dto.state["transportLabel"] == label
    assert dto.state["attemptCount"] == 0
    assert not dto.state["externalOutcomeRecorded"]
    assert "SECRET" not in repr(dto)
    assert not dto.state["canRetryAccountingHandoff"]


@pytest.mark.parametrize("outcome", ["acknowledged", "rejected", "reconciled"])
def test_business_outcome_and_quarantine_do_not_replace_delivery(status_page, outcome):
    item = replace(
        status_page.items[0],
        delivery=replace(
            _delivery("published"), quarantined_count=3, latest_quarantine_id="incident"
        ),
        latest_external_event_type=outcome,
        latest_external_status=outcome,
    )
    dto = serialize_accounting_status_page(replace(status_page, items=(item,))).items[0]
    assert dto.status_label == outcome.title()
    assert dto.state["transportState"] == "published"
    assert dto.state["quarantinedCount"] == 3
    assert "invoice issued" not in dto.supporting_text.lower()
    assert "paid" not in dto.supporting_text.lower()


def test_absence_is_not_zero_and_unsafe_legacy_message_is_not_rendered(status_page):
    dto = serialize_accounting_status_page(status_page).items[0]
    assert dto.state["attemptCount"] is None
    assert dto.state["handoffId"] is None
    assert dto.state["transportState"] is None


@pytest.mark.parametrize("eligible", [False, True])
def test_business_eligibility_controls_request_not_qml(status_page, eligible):
    service = Mock()
    service.evaluate.return_value = AccountingHandoffCapability(allowed=True, reason=None)
    page = replace(status_page, items=(replace(status_page.items[0], handoff_eligible=eligible),))
    page = with_accounting_capabilities(page, capability_service=service, authorized=True)
    assert page.items[0].can_request_accounting_handoff is eligible
    assert page.items[0].handoff_unavailable_reason == (None if eligible else "business_precondition_failed")


@pytest.mark.parametrize("reason", list(AccountingHandoffDenial))
def test_capability_denials_are_server_authored_once_per_page(status_page, reason):
    service = Mock()
    service.evaluate.return_value = AccountingHandoffCapability(
        allowed=False, reason=reason
    )
    page = with_accounting_capabilities(
        status_page, capability_service=service, authorized=False
    )
    assert all(
        not item.can_request_accounting_handoff
        and item.handoff_unavailable_reason == reason.value
        for item in page.items
    )
    service.evaluate.assert_called_once_with(authorized=False, eligible=True)


@pytest.mark.parametrize(
    "state,reason",
    [
        ("pending", "handoff_already_in_progress"),
        ("published", "handoff_already_terminal"),
        ("dead_letter", "handoff_already_terminal"),
    ],
)
def test_existing_handoffs_are_not_requestable(status_page, state, reason):
    service = Mock()
    service.evaluate.return_value = AccountingHandoffCapability(
        allowed=True, reason=None
    )
    item = replace(
        status_page.items[0], delivery=_delivery(state), handoff_eligible=True
    )
    page = with_accounting_capabilities(
        replace(status_page, items=(item,)), capability_service=service, authorized=True
    )
    assert page.items[0].handoff_unavailable_reason == reason


def test_transport_projection_is_bounded_scoped_and_redacted(services):
    project, scope = _seed_billing(services)
    session = services["session"]
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    original = session.get(ProjectBillingPreparationORM, "preparation-zulu")
    preparations = ["preparation-alpha", "preparation-zulu"]
    for index in range(38):
        identifier = f"preparation-{index}"
        values = {
            column.name: getattr(original, column.name)
            for column in ProjectBillingPreparationORM.__table__.columns
        }
        values.update(
            id=identifier,
            preparation_number=f"BP-{index + 3:04}",
            idempotency_key=identifier,
        )
        session.add(ProjectBillingPreparationORM(**values))
        preparations.append(identifier)
    session.flush()
    for preparation in preparations:
        session.add(
            ProjectAccountingHandoffORM(
                id=preparation,
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                project_id=project.id,
                preparation_id=preparation,
                approved_version=2,
                handoff_kind="billing_preparation",
                payload_bytes=b"SECRET",
                payload_hash="a" * 64,
            )
        )
        session.flush()
        session.add(
            ProjectAccountingOutboxORM(
                id=preparation,
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                project_id=project.id,
                event_id=preparation,
                event_type="test",
                aggregate_type="test",
                aggregate_id=preparation,
                aggregate_version=2,
                occurred_at=now,
                envelope_json="SECRET",
                envelope_hash="a" * 64,
                status="retry",
                attempt_count=4,
                max_attempts=5,
                available_at=now,
                created_at=now,
                updated_at=now,
                last_error_code="unsafe-provider-error",
                last_error_message="SECRET credentials",
                target_adapter_id="adapter",
                target_connection_id="connection",
            )
        )
        for number in range(10):
            identifier = f"{preparation}-inbound-{number}"
            session.add(
                ProjectFinanceInboxORM(
                    id=identifier,
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    source_project_id=project.id,
                    event_id=identifier,
                    event_type="external_accounting.outcome.v1",
                    aggregate_type="accounting_handoff_outcome",
                    aggregate_id=preparation,
                    aggregate_version=number + 1,
                    occurred_at=now,
                    envelope_json=json.dumps(
                        {
                            "causation_id": preparation,
                            "payload": {
                                "adapter_id": "adapter",
                                "connection_id": "connection",
                            },
                        }
                    ),
                    envelope_hash="a" * 64,
                    status="quarantined" if number % 2 else "processed",
                    consumer_name="project_management.accounting_outcomes.v1",
                    deduplication_key=identifier,
                    processed_at=now if number % 2 == 0 else None,
                    attempt_count=1,
                    max_attempts=5,
                    available_at=now,
                    created_at=now,
                    updated_at=now,
                    last_error_message="SECRET provider error",
                )
            )
    session.commit()
    reader = services["finance_workspace_query"]._billing_reader
    for size in (1, 200):
        with _statement_count(session) as statements:
            page = reader.list_accounting_statuses(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                project_id=project.id,
                request=AccountingStatusQuery(page_size=size),
            )
        assert len(statements) == 4
        assert len(page.items) == min(size, 40)
        assert all(
            item.delivery.failure_category == "delivery_failed" for item in page.items
        )
        assert all(item.delivery.quarantined_count == 5 for item in page.items)
        assert all(item.delivery.external_sequence == 9 for item in page.items)
        assert "SECRET" not in repr(page)
        assert "payload_bytes" not in " ".join(statements)
        assert "last_error_message" not in " ".join(statements)
    for tenant, org, project_id in (
        ("wrong", scope.organization_id, project.id),
        (scope.tenant_id, "wrong", project.id),
        (scope.tenant_id, scope.organization_id, "wrong"),
    ):
        assert (
            reader.list_accounting_statuses(
                tenant_id=tenant,
                organization_id=org,
                project_id=project_id,
                request=AccountingStatusQuery(),
            ).items
            == ()
        )
