from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.invoicing.billing_events import (
    BillingPreparationStatusChanged,
    BillingPreparationStatusChangeType,
)
from src.core.modules.project_management.contracts.repositories.finance.invoicing.billing import (
    ProjectBillingRepository,
)
from src.core.modules.project_management.domain.financials.accounting.handoff import (
    AccountingHandoffRequestResult,
    AccountingHandoffSnapshot,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.integration.events import IntegrationEventEnvelope
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.time.clock import Clock


class AccountingHandoffRequestCommandHandler(ProjectManagementModuleGuardMixin):
    """Creates immutable PM evidence in the caller-owned Finance transaction."""

    def __init__(
        self, *, session: Session, billing_repo: ProjectBillingRepository,
        financial_profile_repo, handoffs, enqueue_event: Callable[[IntegrationEventEnvelope, datetime], object],
        evidence_builder, capability, context, clock: Clock, user_session,
        enterprise_audit_service, module_catalog_service, record_event: Callable[[object], None],
    ) -> None:
        self._session = session
        self._billing_repo = billing_repo
        self._financial_profile_repo = financial_profile_repo
        self._handoffs = handoffs
        self._enqueue_event = enqueue_event
        self._evidence_builder = evidence_builder
        self._capability = capability
        self._context = context
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._record_event = record_event

    def request(self, preparation_id, *, expected_row_version):
        preparation = self._billing_repo.get_preparation(
            preparation_id, for_update=True
        )
        if preparation is None:
            raise NotFoundError(
                "Billing preparation not found.", code="BILLING_PREPARATION_NOT_FOUND"
            )
        self._require(
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
            self._audit(existing, result="reused")
            return AccountingHandoffRequestResult.from_snapshot(existing)
        if preparation.status.value != "approved":
            raise BusinessRuleError(
                "Only approved Billing Preparation is eligible.",
                code="business_precondition_failed",
            )
        if preparation.row_version != expected_row_version:
            raise BusinessRuleError("Billing preparation changed.", code="STALE_WRITE")
        profile = self._billing_repo.get_profile(
            preparation.project_id, for_update=True
        )
        if profile is None or profile.id != preparation.billing_profile_id:
            raise BusinessRuleError(
                "Billing profile is unavailable.", code="business_precondition_failed"
            )
        now = self._clock.now()
        handoff_id = str(uuid4())
        approved_lines = tuple(
            self._billing_repo.list_preparation_lines(preparation.id)
        )
        payload = self._evidence_builder.build(
            preparation, profile, message_id=handoff_id, approved_lines=approved_lines
        )
        financial_profile = self._financial_profile_repo.get_by_project(preparation.project_id)
        if financial_profile is None or not financial_profile.is_billable:
            raise BusinessRuleError("The Project is not billable.", code="PROJECT_NOT_BILLABLE")
        self._require_currency(payload.currency_code, profile.currency_code)
        self._require_currency(payload.currency_code, financial_profile.currency_code)
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
            requested_by=self._actor_id(),
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

        self._enqueue_event(envelope, now)
        self._mark_delivery_requested(
            preparation, expected_row_version=expected_row_version, now=now
        )
        self._audit(snapshot, result="created")
        return AccountingHandoffRequestResult.from_snapshot(snapshot)

    def _require(self, project_id: str, permission: str, operation: str) -> None:
        require_permission(self._user_session, permission, operation_label=operation)
        require_project_permission(self._user_session, project_id, permission, operation_label=operation)

    def _actor_id(self) -> str:
        actor_id = getattr(getattr(self._user_session, "principal", None), "user_id", None)
        if not actor_id:
            raise BusinessRuleError("An authenticated actor is required for billing changes.", code="BILLING_ACTOR_REQUIRED")
        return str(actor_id)

    @staticmethod
    def _require_currency(expected: str, actual: str) -> None:
        if expected != actual:
            raise BusinessRuleError("Billable source currency must match the Project billing currency.", code="BILLING_SOURCE_CURRENCY_MISMATCH")

    def _mark_delivery_requested(self, preparation, *, expected_row_version, now) -> None:
        preparation.request_delivery(occurred_at=now)
        self._billing_repo.update_preparation(preparation, expected_row_version=expected_row_version)
        self._billing_repo.flush()
        operation = "project_billing_preparation.request_delivery"
        record_audit_entry(
            self, operation=operation, entity_type=type(preparation).__name__,
            entity_id=preparation.id, entity_parent_id=preparation.project_id,
            module="project_management", category="FINANCIAL",
            after_data={"project_id": preparation.project_id}, workspace_id=preparation.project_id,
            source="application", severity="high", metadata={"action": "request_delivery"},
            commit=False, fail_closed=True,
        )
        record_activity(
            self, action=operation, entity_type=type(preparation).__name__, entity_id=preparation.id,
            parent_entity_id=preparation.project_id, module="project_management",
            workspace_id=preparation.project_id, details={"action": "request_delivery"}, commit=False,
        )
        self._record_event(BillingPreparationStatusChanged(
            tenant_id=preparation.tenant_id, organization_id=preparation.organization_id,
            project_id=preparation.project_id, billing_preparation_id=preparation.id,
            change_type=BillingPreparationStatusChangeType.DELIVERY_PENDING, occurred_at=now,
        ))
        self._session.flush()

    def _audit(self, snapshot, *, result):
        evidence = snapshot.evidence
        record_audit_entry(
            self,
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
