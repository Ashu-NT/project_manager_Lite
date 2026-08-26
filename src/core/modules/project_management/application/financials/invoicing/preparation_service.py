from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.modules.project_management.application.common.clock import Clock
from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin
from src.core.modules.project_management.application.financials.rate_cards.rate_card_resolver import RateCardResolver
from src.core.modules.project_management.contracts.repositories.finance.invoicing.billing import ProjectBillingRepository
from src.core.modules.project_management.contracts.repositories.finance.cost_entries.cost_entry import ProjectCostEntryRepository
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import ProjectFinancialProfileRepository
from src.core.modules.project_management.contracts.repositories.finance.cost_entries.labor_posting import ApprovedTimeLaborPostingRepository
from src.core.modules.project_management.domain.financials.billing_preparation import (
    BillableSourceType,
    BillingExternalEventType,
    BillingPreparationStatus,
    ProjectBillingExternalEvent,
    ProjectBillingPreparation,
    ProjectBillingPreparationLine,
    ProjectBillingSourceLock,
)
from src.core.modules.project_management.domain.financials.billing_profile import (
    BillingProfileStatus,
    BillingScheduleLineStatus,
)
from src.core.modules.project_management.domain.financials.configuration import BillingMethod
from src.core.modules.project_management.domain.financials.cost_entry import ProjectCostEntryStatus
from src.core.modules.project_management.domain.financials.rate_cards import RateType
from src.core.modules.project_management.gateway.billing.accounting_billing import (
    BillingPreparationLinePayload,
    ProjectBillingPreparationPayload,
)
from src.core.modules.project_management.contracts.persistence.billing_preparation_submission_unit_of_work import (
    BillingPreparationSubmissionUnitOfWorkFactory,
)
from src.core.platform.application.approval.approval_mutation_participant import (
    request_approval_using,
)
from src.core.platform.application.approval.approval_service import ApprovalService
from src.core.platform.application.finance.financial_period_service import FinancialPeriodService
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.common.ids import generate_id
from src.core.platform.finance import DecimalQuantity, Money
from src.core.platform.integration.canonical_json import canonical_json_sha256
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events


class ProjectBillingPreparationService(ProjectManagementModuleGuardMixin):
    """Prepares governed commercial evidence without issuing accounting records."""

    def __init__(
        self,
        *,
        session: Session,
        billing_repo: ProjectBillingRepository,
        financial_profile_repo: ProjectFinancialProfileRepository,
        cost_entry_repo: ProjectCostEntryRepository,
        labor_posting_repo: ApprovedTimeLaborPostingRepository,
        rate_resolver: RateCardResolver,
        financial_period_service: FinancialPeriodService,
        approval_service: ApprovalService,
        tenant_context_service: TenantContextService,
        clock: Clock,
        submission_uow_factory: BillingPreparationSubmissionUnitOfWorkFactory | None = None,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
    ) -> None:
        self._session = session
        self._billing_repo = billing_repo
        self._financial_profile_repo = financial_profile_repo
        self._cost_entry_repo = cost_entry_repo
        self._labor_posting_repo = labor_posting_repo
        self._rate_resolver = rate_resolver
        self._financial_period_service = financial_period_service
        self._approval_service = approval_service
        self._tenant_context_service = tenant_context_service
        self._clock = clock
        # Approval-P1: `submit_preparation`'s own canonical transaction owner -- the
        # preparation's submit transition, the governed `ApprovalRequest`, and both audit
        # trails all commit atomically through this ONE fresh Session. Optional only so this
        # constructor stays backward-compatible for any test double that never calls
        # `submit_preparation`; production composition always supplies it.
        self._submission_uow_factory = submission_uow_factory
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service

    def get_preparation(self, preparation_id: str) -> ProjectBillingPreparation:
        preparation = self._require_preparation(preparation_id)
        self._require(preparation.project_id, "finance.read", "view billing preparation")
        return preparation

    def list_preparations(
        self, project_id: str, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[ProjectBillingPreparation], int]:
        self._require(project_id, "finance.read", "list billing preparations")
        return self._billing_repo.list_preparations(
            project_id, offset=offset, limit=limit
        )

    def list_latest_external_events(
        self, project_id: str, preparation_ids: tuple[str, ...]
    ) -> dict[str, ProjectBillingExternalEvent]:
        self._require(project_id, "finance.read", "list latest accounting outcomes")
        return self._billing_repo.list_latest_external_events(preparation_ids)

    def list_lines(self, preparation_id: str) -> list[ProjectBillingPreparationLine]:
        preparation = self.get_preparation(preparation_id)
        return self._billing_repo.list_preparation_lines(preparation.id)

    def list_external_events(self, preparation_id: str) -> list[ProjectBillingExternalEvent]:
        preparation = self.get_preparation(preparation_id)
        return self._billing_repo.list_external_events(preparation.id)

    def create_preparation(
        self,
        project_id: str,
        *,
        preparation_number: str,
        period_start: date,
        period_end: date,
        idempotency_key: str,
        correction_of_preparation_id: str | None = None,
    ) -> ProjectBillingPreparation:
        self._require(project_id, "finance.manage", "create billing preparation")
        existing = self._billing_repo.get_preparation_by_idempotency_key(idempotency_key)
        if existing is not None:
            if existing.project_id != project_id:
                raise BusinessRuleError(
                    "Billing idempotency key belongs to another Project.",
                    code="BILLING_IDEMPOTENCY_SCOPE_MISMATCH",
                )
            return existing
        profile = self._require_active_profile(project_id)
        financial_profile = self._require_financial_profile(project_id)
        self._require_supported_method(financial_profile.billing_method)
        self._financial_period_service.require_open_period_for_integration(period_start)
        self._financial_period_service.require_open_period_for_integration(period_end)
        correction = None
        if correction_of_preparation_id:
            correction = self._require_preparation(correction_of_preparation_id)
            if correction.project_id != project_id or correction.status is not BillingPreparationStatus.RECONCILED:
                raise BusinessRuleError(
                    "A correction must reference a reconciled preparation in the same Project.",
                    code="BILLING_CORRECTION_REFERENCE_INVALID",
                )
        context = self._tenant_context_service.require_active_scope_ids(
            operation_label="create billing preparation"
        )
        preparation = ProjectBillingPreparation.create(
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            project_id=project_id,
            billing_profile_id=profile.id,
            preparation_number=preparation_number,
            billing_method=financial_profile.billing_method,
            period_start=period_start,
            period_end=period_end,
            currency_code=profile.currency_code,
            idempotency_key=idempotency_key,
            correction_of_preparation_id=correction.id if correction else None,
            created_by=self._actor_id(),
            created_at=self._clock.now(),
        )
        return self._write("create", preparation, lambda: self._billing_repo.add_preparation(preparation))

    def add_fixed_price_source(
        self, preparation_id: str, *, schedule_line_id: str, expected_row_version: int
    ) -> ProjectBillingPreparationLine:
        preparation = self._mutable_preparation(
            preparation_id, expected_row_version, BillingMethod.FIXED_PRICE
        )
        source = self._billing_repo.get_schedule_line(schedule_line_id)
        if source is None or source.project_id != preparation.project_id:
            raise NotFoundError("Billing schedule line not found.", code="BILLING_SCHEDULE_LINE_NOT_FOUND")
        if source.status is not BillingScheduleLineStatus.READY:
            raise BusinessRuleError(
                "Only a ready billing schedule line can be prepared.",
                code="BILLING_SCHEDULE_NOT_READY",
            )
        source_hash = canonical_json_sha256(
            {
                "id": source.id,
                "version": source.row_version,
                "amount": source.amount,
                "currency_code": source.currency_code,
                "due_date": source.due_date,
                "task_id": source.task_id,
                "acceptance_reference": source.acceptance_reference,
            }
        )
        line = self._line(
            preparation,
            source_type=BillableSourceType.SCHEDULE_LINE,
            source_id=source.id,
            source_revision=str(source.row_version),
            source_content_hash=source_hash,
            description=source.name,
            source_date=source.due_date,
            quantity=Decimal("1"),
            unit="MILESTONE",
            unit_rate=source.amount,
            net_amount=source.amount,
            task_id=source.task_id,
        )
        return self._reserve(preparation, line, expected_row_version)

    def add_approved_time_source(
        self, preparation_id: str, *, time_entry_id: str, expected_row_version: int
    ) -> ProjectBillingPreparationLine:
        preparation = self._mutable_preparation(
            preparation_id, expected_row_version, BillingMethod.TIME_AND_MATERIALS
        )
        posting = self._labor_posting_repo.get_latest(time_entry_id)
        if posting is None or posting.project_id != preparation.project_id:
            raise NotFoundError("Approved time posting not found.", code="BILLING_APPROVED_TIME_NOT_FOUND")
        if posting.reversal_cost_entry_id:
            raise BusinessRuleError(
                "Reversed approved time cannot be billed.", code="BILLING_APPROVED_TIME_REVERSED"
            )
        self._require_source_date(preparation, posting.work_date)
        profile = self._require_active_profile(preparation.project_id)
        snapshot = self._rate_resolver.resolve(
            tenant_id=preparation.tenant_id,
            organization_id=preparation.organization_id,
            project_id=preparation.project_id,
            resource_id=posting.resource_id,
            rate_type=RateType.BILLING,
            as_of=posting.work_date,
            unit="HOUR",
            customer_party_id=profile.customer_party_id,
            contract_reference=profile.contract_reference,
        )
        self._require_currency(
            preparation.currency_code, snapshot.monetary_rate.money.currency.code
        )
        total = snapshot.monetary_rate.apply(DecimalQuantity.of(posting.hours, "HOUR")).rounded()
        line = self._line(
            preparation,
            source_type=BillableSourceType.APPROVED_TIME,
            source_id=posting.time_entry_id,
            source_revision=str(posting.source_revision),
            source_content_hash=posting.source_content_hash,
            description=f"Approved time {posting.time_entry_id}",
            source_date=posting.work_date,
            quantity=posting.hours,
            unit="HOUR",
            unit_rate=snapshot.monetary_rate.money.amount,
            net_amount=total.amount,
            task_id=posting.task_id,
            resource_id=posting.resource_id,
            rate_card_id=snapshot.rate_card_id,
            rate_line_id=snapshot.rate_line_id,
            rate_card_version=snapshot.rate_card_version,
        )
        return self._reserve(preparation, line, expected_row_version)

    def add_cost_plus_source(
        self, preparation_id: str, *, cost_entry_id: str, expected_row_version: int
    ) -> ProjectBillingPreparationLine:
        preparation = self._mutable_preparation(
            preparation_id, expected_row_version, BillingMethod.COST_PLUS
        )
        entry = self._cost_entry_repo.get(cost_entry_id)
        if entry is None or entry.project_id != preparation.project_id:
            raise NotFoundError("Posted cost entry not found.", code="BILLING_POSTED_COST_NOT_FOUND")
        if entry.status is not ProjectCostEntryStatus.POSTED or entry.posting_date is None:
            raise BusinessRuleError(
                "Only posted cost can be prepared for cost-plus billing.",
                code="BILLING_COST_NOT_POSTED",
            )
        if entry.amount <= 0:
            raise BusinessRuleError(
                "Cost-plus preparation requires a positive posted cost.",
                code="BILLING_COST_AMOUNT_INVALID",
            )
        self._require_source_date(preparation, entry.posting_date)
        profile = self._require_active_profile(preparation.project_id)
        self._require_currency(preparation.currency_code, entry.currency_code)
        multiplier = Decimal("1") + (profile.cost_plus_markup_percent / Decimal("100"))
        total = (Money.of(entry.amount, entry.currency_code) * multiplier).rounded()
        line = self._line(
            preparation,
            source_type=BillableSourceType.POSTED_COST,
            source_id=entry.id,
            source_revision=entry.source_revision,
            source_content_hash=entry.source_content_hash,
            description=entry.description,
            source_date=entry.posting_date,
            quantity=Decimal("1"),
            unit="COST",
            unit_rate=total.amount,
            net_amount=total.amount,
            task_id=entry.task_id,
            resource_id=entry.resource_id,
            source_amount=entry.amount,
            markup_percent=profile.cost_plus_markup_percent,
        )
        return self._reserve(preparation, line, expected_row_version)

    def _new_submission_context(self) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id())

    def submit_preparation(
        self, preparation_id: str, *, expected_row_version: int
    ) -> ProjectBillingPreparation:
        if self._submission_uow_factory is None:
            raise BusinessRuleError(
                "Billing preparation submission requires a configured transaction owner.",
                code="BILLING_PREPARATION_SUBMISSION_UOW_REQUIRED",
            )
        with self._submission_uow_factory.create(context=self._new_submission_context()) as uow:
            preparation = uow.billing.get_preparation(preparation_id)
            if preparation is None:
                raise NotFoundError(
                    "Billing preparation not found.", code="BILLING_PREPARATION_NOT_FOUND"
                )
            self._require(preparation.project_id, "finance.manage", "submit billing preparation")
            if preparation.row_version != expected_row_version:
                raise BusinessRuleError("Billing preparation changed.", code="STALE_WRITE")
            now = self._clock.now()
            principal = self._user_session.principal if self._user_session else None
            request = request_approval_using(
                approval_repo=uow.approvals,
                enterprise_audit_service=uow._enterprise_audit_service,
                request_type="project_billing_preparation.approve",
                entity_type="project_billing_preparation",
                entity_id=preparation.id,
                tenant_id=preparation.tenant_id,
                organization_id=preparation.organization_id,
                project_id=preparation.project_id,
                payload={"preparation_id": preparation.id, "expected_version": expected_row_version},
                requested_by_user_id=principal.user_id if principal else None,
                requested_by_username=principal.username if principal else None,
            )
            preparation.submit(
                submitted_by=self._actor_id(), submitted_at=now, approval_request_id=request.id
            )
            uow.billing.update_preparation(preparation, expected_row_version=expected_row_version)
            self._audit_using(uow, "submit", preparation)
            uow.commit()
        self._approval_service.publish_requested(request)
        domain_events.billing_preparations_changed.emit(preparation.project_id)
        return preparation

    def _apply_approval_decision(
        self, preparation_id: str, *, approved_by: str, expected_version: int, commit: bool
    ) -> ProjectBillingPreparation:
        preparation = self._require_preparation(preparation_id)
        preparation.approve(approved_by=approved_by, approved_at=self._clock.now())
        locks = self._billing_repo.list_source_locks(preparation.id)
        for lock in locks:
            lock.finalize(occurred_at=self._clock.now())
            self._billing_repo.update_source_lock(lock)
        self._billing_repo.update_preparation(preparation, expected_row_version=expected_version)
        self._audit("approve", preparation)
        if commit:
            self._session.commit()
            domain_events.billing_preparations_changed.emit(preparation.project_id)
        return preparation

    def _apply_rejection_decision(
        self,
        preparation_id: str,
        *,
        rejected_by: str,
        expected_version: int,
        notes: str,
        commit: bool,
    ) -> ProjectBillingPreparation:
        preparation = self._require_preparation(preparation_id)
        now = self._clock.now()
        preparation.reject(rejected_by=rejected_by, rejected_at=now, notes=notes)
        for lock in self._billing_repo.list_source_locks(preparation.id):
            lock.release(occurred_at=now)
            self._billing_repo.update_source_lock(lock)
        self._billing_repo.update_preparation(preparation, expected_row_version=expected_version)
        self._audit("reject", preparation)
        if commit:
            self._session.commit()
            domain_events.billing_preparations_changed.emit(preparation.project_id)
        return preparation

    def request_delivery(
        self, preparation_id: str, *, expected_row_version: int
    ) -> ProjectBillingPreparationPayload:
        preparation = self._require_preparation(preparation_id)
        self._require(preparation.project_id, "finance.manage", "request accounting delivery")
        payload = self.build_delivery_payload(preparation.id)
        preparation.request_delivery(occurred_at=self._clock.now())
        self._write(
            "request_delivery",
            preparation,
            lambda: self._billing_repo.update_preparation(
                preparation, expected_row_version=expected_row_version
            ),
        )
        return payload

    def build_delivery_payload(self, preparation_id: str) -> ProjectBillingPreparationPayload:
        preparation = self._require_preparation(preparation_id)
        self._require(preparation.project_id, "finance.read", "build accounting delivery payload")
        if preparation.status not in {
            BillingPreparationStatus.APPROVED,
            BillingPreparationStatus.DELIVERY_PENDING,
            BillingPreparationStatus.DELIVERED,
            BillingPreparationStatus.ACKNOWLEDGED,
            BillingPreparationStatus.RECONCILED,
        }:
            raise BusinessRuleError(
                "Only approved billing evidence can cross the accounting boundary.",
                code="BILLING_DELIVERY_NOT_APPROVED",
            )
        profile = self._require_active_profile(preparation.project_id, allow_closed=True)
        if not profile.customer_party_id or not preparation.approved_by or not preparation.approved_at:
            raise BusinessRuleError(
                "Approved billing evidence is incomplete.", code="BILLING_DELIVERY_INCOMPLETE"
            )
        lines = tuple(
            BillingPreparationLinePayload(
                line_id=line.id,
                source_type=line.source_type.value,
                source_id=line.source_id,
                source_revision=line.source_revision,
                source_content_hash=line.source_content_hash,
                description=line.description,
                source_date=line.source_date,
                quantity=format(line.quantity, "f"),
                unit=line.unit,
                unit_rate=format(line.unit_rate, "f"),
                net_amount=format(line.net_amount, "f"),
                currency_code=line.currency_code,
                task_id=line.task_id,
                resource_id=line.resource_id,
            )
            for line in self._billing_repo.list_preparation_lines(preparation.id)
        )
        return ProjectBillingPreparationPayload(
            schema_name="project_billing_preparation.v1",
            message_id=f"project-billing-preparation:{preparation.id}",
            tenant_id=preparation.tenant_id,
            organization_id=preparation.organization_id,
            project_id=preparation.project_id,
            preparation_id=preparation.id,
            preparation_number=preparation.preparation_number,
            billing_method=preparation.billing_method.value,
            period_start=preparation.period_start,
            period_end=preparation.period_end,
            currency_code=preparation.currency_code,
            customer_party_id=profile.customer_party_id,
            contract_reference=profile.contract_reference,
            external_customer_reference=profile.external_customer_reference,
            purchase_order_reference=profile.purchase_order_reference,
            payment_terms_days=profile.payment_terms_days,
            total_amount=format(preparation.total_amount, "f"),
            approved_by=preparation.approved_by,
            approved_at=preparation.approved_at,
            lines=lines,
        )

    def record_external_outcome(
        self,
        preparation_id: str,
        *,
        event_type: BillingExternalEventType | str,
        external_system: str,
        external_status: str,
        idempotency_key: str,
        occurred_at,
        external_invoice_reference: str | None = None,
        reconciliation_reference: str | None = None,
        message: str = "",
    ) -> ProjectBillingExternalEvent:
        preparation = self._require_preparation(preparation_id)
        self._require(preparation.project_id, "finance.manage", "record accounting outcome")
        existing = self._billing_repo.get_external_event_by_idempotency_key(
            external_system=external_system, idempotency_key=idempotency_key
        )
        if existing is not None:
            return existing
        resolved_type = BillingExternalEventType(event_type)
        event = ProjectBillingExternalEvent.create(
            tenant_id=preparation.tenant_id,
            organization_id=preparation.organization_id,
            project_id=preparation.project_id,
            preparation_id=preparation.id,
            event_type=resolved_type,
            external_system=external_system,
            external_status=external_status,
            idempotency_key=idempotency_key,
            occurred_at=occurred_at,
            external_invoice_reference=external_invoice_reference,
            reconciliation_reference=reconciliation_reference,
            message=message,
            recorded_at=self._clock.now(),
        )
        expected = preparation.row_version
        if resolved_type is BillingExternalEventType.DELIVERY_ACCEPTED:
            preparation.mark_delivered(occurred_at=occurred_at)
            preparation.acknowledge(occurred_at=occurred_at)
        elif resolved_type is BillingExternalEventType.RECONCILED:
            preparation.reconcile(occurred_at=occurred_at)
        return self._write(
            "external_outcome",
            event,
            lambda: (
                self._billing_repo.add_external_event(event),
                self._billing_repo.update_preparation(
                    preparation, expected_row_version=expected
                ) if preparation.row_version == expected else None,
            ),
        )

    def _reserve(
        self,
        preparation: ProjectBillingPreparation,
        line: ProjectBillingPreparationLine,
        expected_row_version: int,
    ) -> ProjectBillingPreparationLine:
        lock = ProjectBillingSourceLock.create(
            tenant_id=line.tenant_id,
            organization_id=line.organization_id,
            project_id=line.project_id,
            source_type=line.source_type,
            source_id=line.source_id,
            source_revision=line.source_revision,
            source_content_hash=line.source_content_hash,
            preparation_id=line.preparation_id,
            preparation_line_id=line.id,
            reserved_at=self._clock.now(),
        )
        current_lines = self._billing_repo.list_preparation_lines(preparation.id)
        preparation.replace_totals(
            line_count=len(current_lines) + 1,
            total_amount=sum((item.net_amount for item in current_lines), Decimal("0")) + line.net_amount,
            occurred_at=self._clock.now(),
        )
        try:
            return self._write(
                "reserve_source",
                line,
                lambda: (
                    self._billing_repo.reserve_source(line, lock),
                    self._billing_repo.update_preparation(
                        preparation, expected_row_version=expected_row_version
                    ),
                ),
            )
        except IntegrityError as exc:
            raise BusinessRuleError(
                "This billable source is already reserved by another preparation.",
                code="BILLING_SOURCE_ALREADY_RESERVED",
            ) from exc

    def _line(self, preparation: ProjectBillingPreparation, **values) -> ProjectBillingPreparationLine:
        return ProjectBillingPreparationLine.create(
            tenant_id=preparation.tenant_id,
            organization_id=preparation.organization_id,
            project_id=preparation.project_id,
            preparation_id=preparation.id,
            currency_code=preparation.currency_code,
            created_at=self._clock.now(),
            **values,
        )

    def _mutable_preparation(
        self, preparation_id: str, expected_version: int, method: BillingMethod
    ) -> ProjectBillingPreparation:
        preparation = self._require_preparation(preparation_id)
        self._require(preparation.project_id, "finance.manage", "add billable source")
        preparation.ensure_draft()
        if preparation.row_version != expected_version:
            raise BusinessRuleError("Billing preparation changed.", code="STALE_WRITE")
        if preparation.billing_method is not method:
            raise BusinessRuleError(
                f"This preparation requires {preparation.billing_method.value} sources.",
                code="BILLING_SOURCE_METHOD_MISMATCH",
            )
        return preparation

    def _require_source_date(self, preparation: ProjectBillingPreparation, source_date: date) -> None:
        if source_date < preparation.period_start or source_date > preparation.period_end:
            raise BusinessRuleError(
                "Billable source date is outside the preparation period.",
                code="BILLING_SOURCE_OUTSIDE_PERIOD",
            )

    @staticmethod
    def _require_currency(expected: str, actual: str) -> None:
        if expected != actual:
            raise BusinessRuleError(
                "Billable source currency must match the Project billing currency.",
                code="BILLING_SOURCE_CURRENCY_MISMATCH",
            )

    def _require_active_profile(self, project_id: str, *, allow_closed: bool = False):
        profile = self._billing_repo.get_profile(project_id)
        allowed = {BillingProfileStatus.ACTIVE}
        if allow_closed:
            allowed.add(BillingProfileStatus.CLOSED)
        if profile is None or profile.status not in allowed:
            raise BusinessRuleError(
                "An active Project billing profile is required.",
                code="BILLING_PROFILE_NOT_ACTIVE",
            )
        return profile

    def _require_financial_profile(self, project_id: str):
        profile = self._financial_profile_repo.get_by_project(project_id)
        if profile is None or not profile.is_billable:
            raise BusinessRuleError("The Project is not billable.", code="PROJECT_NOT_BILLABLE")
        return profile

    @staticmethod
    def _require_supported_method(method: BillingMethod) -> None:
        if method not in {
            BillingMethod.TIME_AND_MATERIALS,
            BillingMethod.FIXED_PRICE,
            BillingMethod.COST_PLUS,
        }:
            raise BusinessRuleError(
                "The Project billing method is not supported in this release.",
                code="BILLING_METHOD_NOT_SUPPORTED",
            )

    def _require_preparation(self, preparation_id: str) -> ProjectBillingPreparation:
        preparation = self._billing_repo.get_preparation(preparation_id)
        if preparation is None:
            raise NotFoundError(
                "Billing preparation not found.", code="BILLING_PREPARATION_NOT_FOUND"
            )
        return preparation

    def _require(self, project_id: str, permission: str, operation: str) -> None:
        require_permission(self._user_session, permission, operation_label=operation)
        require_project_permission(
            self._user_session, project_id, permission, operation_label=operation
        )

    def _actor_id(self) -> str:
        actor_id = getattr(getattr(self._user_session, "principal", None), "user_id", None)
        if not actor_id:
            raise BusinessRuleError(
                "An authenticated actor is required for billing changes.",
                code="BILLING_ACTOR_REQUIRED",
            )
        return str(actor_id)

    def _audit(self, operation: str, entity) -> None:
        self._audit_using(self, operation, entity)

    @staticmethod
    def _audit_using(owner, operation: str, entity) -> None:
        record_audit_entry(
            owner,
            operation=f"project_billing_preparation.{operation}",
            entity_type=type(entity).__name__,
            entity_id=entity.id,
            entity_parent_id=entity.project_id,
            module="project_management",
            old_value=None,
            new_value=json.dumps({"project_id": entity.project_id}, sort_keys=True),
            workspace_id=entity.project_id,
            source="application",
            severity="high",
            compliance_tag="financial",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )

    def _write(self, operation: str, entity, write, *, emit: bool = True):
        try:
            write()
            self._billing_repo.flush()
            self._audit(operation, entity)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        if emit:
            domain_events.billing_preparations_changed.emit(entity.project_id)
        return entity


__all__ = ["ProjectBillingPreparationService"]
