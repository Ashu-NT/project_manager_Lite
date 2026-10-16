from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.invoicing.billing_events import (
    BillingPreparationLineAdded,
    BillingPreparationLineRemoved,
)
from src.core.modules.project_management.application.financials.invoicing.dto.commands.billing_sources import (
    FinancialAddApprovedTimeBillingSourceCommand,
    FinancialAddCostPlusBillingSourceCommand,
    FinancialAddFixedPriceBillingSourceCommand,
    FinancialRemoveDraftBillingLineCommand,
)
from src.core.modules.project_management.application.financials.invoicing.dto.responses.billing import (
    FinancialBillingPreparationLineDto,
    FinancialBillingPreparationResponse,
)
from src.core.modules.project_management.application.financials.invoicing.mappers.billing import (
    map_billing_preparation,
    serialize_billing_preparation_line,
)
from src.core.modules.project_management.application.financials.rate_cards.rate_card_resolver import (
    RateCardResolver,
)
from src.core.modules.project_management.contracts.repositories.finance.cost_entries.cost_entry import (
    ProjectCostEntryRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.cost_entries.labor_posting import (
    ApprovedTimeLaborPostingRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.invoicing.billing import (
    ProjectBillingRepository,
)
from src.core.modules.project_management.domain.financials.billing_preparation import (
    BillableSourceType,
    ProjectBillingPreparation,
    ProjectBillingPreparationLine,
    ProjectBillingSourceLock,
)
from src.core.modules.project_management.domain.financials.billing_profile import (
    BillingProfileStatus,
    BillingScheduleLineStatus,
)
from src.core.modules.project_management.domain.financials.configuration import (
    BillingMethod,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntryStatus,
)
from src.core.modules.project_management.domain.financials.rate_cards import RateType
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.domain.finance import DecimalQuantity, Money
from src.core.platform.integration.canonical_json import canonical_json_sha256
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.time.clock import CalendarClock


class BillingPreparationSourceCommandHandler(ProjectManagementModuleGuardMixin):
    """Own this preparation command family in the caller's transaction."""

    def __init__(
        self,
        *,
        session: Session,
        billing_repo: ProjectBillingRepository,
        tenant_context_service: TenantContextService,
        clock: CalendarClock,
        cost_entry_repo: ProjectCostEntryRepository,
        labor_posting_repo: ApprovedTimeLaborPostingRepository,
        rate_resolver: RateCardResolver,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        record_event: Callable[[object], None] | None = None,
    ) -> None:
        self._session = session
        self._billing_repo = billing_repo
        self._tenant_context_service = tenant_context_service
        self._clock = clock
        self._cost_entry_repo = cost_entry_repo
        self._labor_posting_repo = labor_posting_repo
        self._rate_resolver = rate_resolver
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._record_event = record_event

    def add_fixed_price_source(self, command: FinancialAddFixedPriceBillingSourceCommand) -> FinancialBillingPreparationLineDto:
        preparation = self._mutable_preparation(
            command.preparation_id, command.expected_version, BillingMethod.FIXED_PRICE
        )
        source = self._billing_repo.get_schedule_line(command.schedule_line_id)
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
            quantity=Decimal(1),
            unit="MILESTONE",
            unit_rate=source.amount,
            net_amount=source.amount,
            task_id=source.task_id,
        )
        return serialize_billing_preparation_line(self._reserve(preparation, line, command.expected_version))

    def add_approved_time_source(self, command: FinancialAddApprovedTimeBillingSourceCommand) -> FinancialBillingPreparationLineDto:
        preparation = self._mutable_preparation(
            command.preparation_id, command.expected_version, BillingMethod.TIME_AND_MATERIALS
        )
        posting = self._labor_posting_repo.get_latest(command.time_entry_id)
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
            rate_line_version=snapshot.rate_line_version,
            rate_modifier=(snapshot.modifier_applied.value if snapshot.modifier_applied else None),
            rate_modifier_multiplier=snapshot.modifier_multiplier,
        )
        return serialize_billing_preparation_line(self._reserve(preparation, line, command.expected_version))

    def add_cost_plus_source(self, command: FinancialAddCostPlusBillingSourceCommand) -> FinancialBillingPreparationLineDto:
        preparation = self._mutable_preparation(
            command.preparation_id, command.expected_version, BillingMethod.COST_PLUS
        )
        entry = self._cost_entry_repo.get(command.cost_entry_id)
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
        multiplier = Decimal(1) + (profile.cost_plus_markup_percent / Decimal(100))
        total = (Money.of(entry.amount, entry.currency_code) * multiplier).rounded()
        line = self._line(
            preparation,
            source_type=BillableSourceType.POSTED_COST,
            source_id=entry.id,
            source_revision=entry.source_revision,
            source_content_hash=entry.source_content_hash,
            description=entry.description,
            source_date=entry.posting_date,
            quantity=Decimal(1),
            unit="COST",
            unit_rate=total.amount,
            net_amount=total.amount,
            task_id=entry.task_id,
            resource_id=entry.resource_id,
            source_amount=entry.amount,
            markup_percent=profile.cost_plus_markup_percent,
        )
        return serialize_billing_preparation_line(self._reserve(preparation, line, command.expected_version))

    def remove_draft_line(self, command: FinancialRemoveDraftBillingLineCommand) -> FinancialBillingPreparationResponse:
        preparation = self._require_preparation(command.preparation_id)
        self._require(preparation.project_id, "finance.manage", "remove draft billing source")
        preparation.ensure_draft()
        if preparation.row_version != command.expected_version:
            raise BusinessRuleError("Billing preparation changed.", code="STALE_WRITE")
        lines = self._billing_repo.list_preparation_lines(command.preparation_id)
        line = next((item for item in lines if item.id == command.line_id), None)
        if line is None:
            raise NotFoundError("Billing preparation line not found.", code="BILLING_LINE_NOT_FOUND")
        now = self._clock.now()
        remaining = [item for item in lines if item.id != command.line_id]
        preparation.replace_totals(
            line_count=len(remaining),
            total_amount=sum((item.net_amount for item in remaining), Decimal(0)),
            occurred_at=now,
        )
        event = BillingPreparationLineRemoved(
            tenant_id=preparation.tenant_id,
            organization_id=preparation.organization_id,
            project_id=preparation.project_id,
            billing_preparation_id=preparation.id,
            preparation_line_id=line.id,
            source_type=line.source_type,
            occurred_at=now,
        )
        return map_billing_preparation(self._write(
            "remove_draft_line",
            preparation,
            lambda: (
                self._billing_repo.remove_draft_line(preparation.id, line.id),
                self._billing_repo.update_preparation(
                    preparation, expected_row_version=command.expected_version
                ),
            ),
            event,
        ))

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
        now = self._clock.now()
        preparation.replace_totals(
            line_count=len(current_lines) + 1,
            total_amount=sum((item.net_amount for item in current_lines), Decimal(0)) + line.net_amount,
            occurred_at=now,
        )
        event = BillingPreparationLineAdded(
            tenant_id=line.tenant_id,
            organization_id=line.organization_id,
            project_id=line.project_id,
            billing_preparation_id=line.preparation_id,
            preparation_line_id=line.id,
            source_type=line.source_type,
            occurred_at=now,
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
                event,
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

    def _audit(self, operation: str, entity) -> None:
        self._audit_using(self, operation, entity)

    @staticmethod
    def _audit_using(owner, operation: str, entity) -> None:
        full_operation = f"project_billing_preparation.{operation}"
        record_audit_entry(
            owner,
            operation=full_operation,
            entity_type=type(entity).__name__,
            entity_id=entity.id,
            entity_parent_id=entity.project_id,
            module="project_management",
            category="FINANCIAL",
            after_data={"project_id": entity.project_id},
            workspace_id=entity.project_id,
            source="application",
            severity="high",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )
        record_activity(
            owner,
            action=full_operation,
            entity_type=type(entity).__name__,
            entity_id=entity.id,
            parent_entity_id=entity.project_id,
            module="project_management",
            workspace_id=entity.project_id,
            details={"action": operation},
            commit=False,
        )

    def _write(self, operation: str, entity, write, events: object):
        write()
        self._billing_repo.flush()
        self._audit(operation, entity)
        if self._record_event is not None:
            for event in (events if isinstance(events, tuple) else (events,)):
                self._record_event(event)
        self._session.flush()
        return entity

__all__ = ["BillingPreparationSourceCommandHandler"]
