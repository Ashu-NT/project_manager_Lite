from uuid import uuid4

from src.core.modules.project_management.domain.financials.accounting.handoff import (
    AccountingHandoffRequestResult,
    AccountingHandoffSnapshot,
)
from src.core.platform.application.integration.delivery_service import (
    IntegrationOutboxService,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.integration.events import IntegrationEventEnvelope
from src.core.shared.audit import record_audit_entry


class AccountingHandoffRequestService:
    def __init__(self, *, preparations, handoffs, outbox, capability, context):
        self._preparations = preparations
        self._handoffs = handoffs
        self._outbox = outbox
        self._capability = capability
        self._context = context

    def request(self, preparation_id, *, expected_row_version):
        owner = self._preparations
        preparation = owner._billing_repo.get_preparation(
            preparation_id, for_update=True
        )
        if preparation is None:
            raise NotFoundError(
                "Billing preparation not found.", code="BILLING_PREPARATION_NOT_FOUND"
            )
        owner._require(
            preparation.project_id,
            "finance.accounting_handoff.request",
            "request Accounting handoff",
        )
        decision = self._capability.evaluate(
            authorized=True, eligible=True, for_update=True
        )
        if not decision.allowed:
            raise BusinessRuleError(decision.message, code=decision.reason.value)
        existing = self._handoffs.get_for_preparation(
            preparation.project_id, preparation.id
        )
        if existing is not None:
            if expected_row_version not in (
                existing.approved_preparation_version,
                preparation.row_version,
            ):
                raise BusinessRuleError(
                    "Billing preparation changed.", code="STALE_WRITE"
                )
            self._audit(owner, existing, result="reused")
            return AccountingHandoffRequestResult.from_snapshot(existing)
        if preparation.status.value != "approved":
            raise BusinessRuleError(
                "Only approved Billing Preparation is eligible.",
                code="business_precondition_failed",
            )
        if preparation.row_version != expected_row_version:
            raise BusinessRuleError("Billing preparation changed.", code="STALE_WRITE")
        profile = owner._billing_repo.get_profile(
            preparation.project_id, for_update=True
        )
        if profile is None or profile.id != preparation.billing_profile_id:
            raise BusinessRuleError(
                "Billing profile is unavailable.", code="business_precondition_failed"
            )
        now = owner._clock.now()
        handoff_id = str(uuid4())
        approved_lines = tuple(
            owner._billing_repo.list_preparation_lines(preparation.id)
        )
        payload = owner._build_approved_delivery_payload(
            preparation, profile, message_id=handoff_id, approved_lines=approved_lines
        )
        financial_profile = owner._require_financial_profile(preparation.project_id)
        owner._require_currency(payload.currency_code, profile.currency_code)
        owner._require_currency(payload.currency_code, financial_profile.currency_code)
        if len(payload.lines) != preparation.line_count:
            raise BusinessRuleError(
                "Approved line count mismatch.", code="BILLING_DELIVERY_INCOMPLETE"
            )
        snapshot = AccountingHandoffSnapshot(
            schema_name="project_accounting_handoff.v1",
            handoff_id=handoff_id,
            approved_preparation_version=preparation.row_version,
            billing_profile_version=profile.row_version,
            approval_request_id=preparation.approval_request_id,
            requested_by=owner._actor_id(),
            requested_at=now,
            evidence=payload,
            approved_lines=approved_lines,
        )
        self._handoffs.add(snapshot)
        envelope = IntegrationEventEnvelope(
            event_id=handoff_id,
            event_type="project_accounting_handoff.requested",
            schema_version=1,
            tenant_id=preparation.tenant_id,
            organization_id=preparation.organization_id,
            aggregate_type="billing_preparation",
            aggregate_id=preparation.id,
            aggregate_version=preparation.row_version,
            occurred_at=now,
            correlation_id=self._context.correlation_id,
            causation_id=self._context.causation_id,
            payload=snapshot.model_dump(mode="json"),
        )

        class RequestClock:
            def now(self):
                return now

        IntegrationOutboxService(
            repository=self._outbox,
            owner_module="project_management",
            clock=RequestClock(),
        ).enqueue(envelope)
        owner._mark_delivery_requested(
            preparation, expected_row_version=expected_row_version, now=now
        )
        self._audit(owner, snapshot, result="created")
        return AccountingHandoffRequestResult.from_snapshot(snapshot)

    @staticmethod
    def _audit(owner, snapshot, *, result):
        evidence = snapshot.evidence
        record_audit_entry(
            owner,
            operation="project_accounting_handoff.request",
            entity_type="AccountingHandoff",
            entity_id=snapshot.handoff_id,
            entity_parent_id=evidence.project_id,
            module="project_management",
            category="FINANCIAL",
            workspace_id=evidence.project_id,
            source="application",
            severity="high",
            commit=False,
            fail_closed=True,
            after_data={
                "preparation_id": evidence.preparation_id,
                "approved_version": snapshot.approved_preparation_version,
                "handoff_id": snapshot.handoff_id,
                "requested_at": snapshot.requested_at.isoformat(),
                "result": result,
            },
        )
