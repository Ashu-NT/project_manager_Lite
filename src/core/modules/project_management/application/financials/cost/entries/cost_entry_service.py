from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.modules.project_management.application.common.clock import Clock
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.cost.entries.cost_entry_events import (
    CostEntryRecorded,
    CostEntryRemoved,
    CostEntryReversed,
    CostEntryStatusChangeType,
    CostEntryStatusChanged,
    CostEntryUpdated,
)
from src.core.modules.project_management.application.financials.cost.entries.approval_result import (
    CostEntryApprovalOutcome,
    CostEntryApprovalResult,
)
from src.core.modules.project_management.contracts.financial_sources.approved_time import (
    ApprovedTimeFinancialSource,
)
from src.core.modules.project_management.contracts.financial_sources.procurement import (
    ProcurementReceiptAccrualFinancialSource,
)
from src.core.modules.project_management.contracts.financial_sources.reference import (
    FinancialPostingPurpose,
    FinancialSourceModule,
    FinancialSourceReference,
    FinancialSourceType,
    financial_source_content_hash,
)
from src.core.modules.project_management.contracts.repositories.finance.cost_entries.labor_posting import ApprovedTimeLaborPostingRepository
from src.core.modules.project_management.contracts.repositories.finance.cost_entries.cost_entry import (
    ProjectCostEntryRepository,
)
from src.core.modules.project_management.contracts.reads.financials.sorting import (
    normalize_cost_entry_sort,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectCostCodeRepository,
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.resources.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.tasks.task import TaskRepository
from src.core.modules.project_management.domain.financials.configuration import (
    CostCodePolicy,
    FinancialProfileStatus,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntry,
    ProjectCostEntryKind,
    ProjectCostEntryStatus,
)
from src.core.modules.project_management.domain.financials.labor_posting import ApprovedTimeLaborPosting
from src.core.modules.project_management.domain.financials.rate_cards import RateType
from src.core.modules.project_management.application.financials.rate_cards.rate_card_resolver import RateCardResolver
from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.application.finance.financial_period_service import FinancialPeriodService
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.domain.approval.policy import is_governance_required
from src.core.platform.finance import EXCHANGE_RATE_STORAGE, Money, MoneyPayload
from src.core.shared.audit import record_audit_entry


class ProjectCostEntryService(ProjectManagementModuleGuardMixin):
    """Command boundary for canonical project actuals and reversals."""

    def __init__(
        self,
        *,
        session: Session,
        entry_repo: ProjectCostEntryRepository,
        project_repo: ProjectRepository,
        financial_profile_repo: ProjectFinancialProfileRepository,
        cost_code_repo: ProjectCostCodeRepository,
        task_repo: TaskRepository,
        resource_repo: ResourceRepository,
        financial_period_service: FinancialPeriodService,
        clock: Clock,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None = None,
        approval_service=None,
        rate_resolver: RateCardResolver | None = None,
        labor_posting_repo: ApprovedTimeLaborPostingRepository | None = None,
        record_event: Callable[[object], None] | None = None,
    ) -> None:
        self._session = session
        self._entry_repo = entry_repo
        self._project_repo = project_repo
        self._financial_profile_repo = financial_profile_repo
        self._cost_code_repo = cost_code_repo
        self._task_repo = task_repo
        self._resource_repo = resource_repo
        self._financial_period_service = financial_period_service
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._approval_service = approval_service
        self._rate_resolver = rate_resolver
        self._labor_posting_repo = labor_posting_repo
        self._record_event = record_event

    def apply_approved_time_source(
        self, source: ApprovedTimeFinancialSource
    ) -> tuple[object, ...]:
        """Apply one trusted inbox delivery without committing the consumer transaction.
        Returns the real typed Cost Entry DomainEvent(s) produced -- a true replay (identical
        revision+content already posted) returns an empty tuple. A correction that supersedes a
        prior revision produces two genuine facts: the prior entry was reversed, and the new
        corrected entry was recorded -- both returned."""
        if self._rate_resolver is None or self._labor_posting_repo is None:
            raise BusinessRuleError(
                "Approved Time financial consumer is not configured.",
                code="APPROVED_TIME_CONSUMER_NOT_CONFIGURED",
            )
        context = self._require_full_context("post approved time labor cost")
        reference = source.reference
        if reference.tenant_id != context.tenant_id or reference.organization_id != context.organization_id:
            raise BusinessRuleError("Approved Time source is outside the active scope.", code="APPROVED_TIME_SCOPE_MISMATCH")
        self._require_project(reference.project_id)
        profile = self._require_active_profile(reference.project_id)
        if not profile.default_cost_code_id:
            raise BusinessRuleError(
                "Project requires a default cost code before approved labor can post.",
                code="APPROVED_TIME_DEFAULT_COST_CODE_REQUIRED",
            )
        latest = self._labor_posting_repo.get_latest(source.time_entry_id, for_update=True)
        revision = int(reference.source_revision)
        if latest is not None:
            if revision == latest.source_revision and reference.content_hash == latest.source_content_hash:
                existing = self._entry_repo.get(latest.actual_cost_entry_id)
                if existing is None:
                    raise BusinessRuleError("Approved labor posting lost its ledger entry.", code="APPROVED_TIME_LEDGER_INTEGRITY_FAILED")
                return ()
            if revision <= latest.source_revision:
                raise BusinessRuleError("Approved Time revision is stale or conflicting.", code="APPROVED_TIME_REVISION_CONFLICT")
            if source.correction_of_revision != str(latest.source_revision):
                raise BusinessRuleError("Approved Time correction does not reference the latest posting.", code="APPROVED_TIME_CORRECTION_CHAIN_INVALID")
        elif revision != 1 or source.correction_of_revision is not None:
            raise BusinessRuleError("First approved Time posting must be revision 1.", code="APPROVED_TIME_REVISION_GAP")

        self._require_dimensions(
            project_id=reference.project_id,
            cost_code_id=profile.default_cost_code_id,
            transaction_date=source.work_date,
            task_id=source.task_id,
            resource_id=source.resource_id,
            organization_id=context.organization_id,
        )
        snapshot = self._rate_resolver.resolve(
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            project_id=reference.project_id,
            resource_id=source.resource_id,
            rate_type=RateType.COST,
            as_of=source.work_date,
            unit="HOUR",
        )
        rate_money = snapshot.monetary_rate.money
        if rate_money.currency.code != context.organization.base_currency:
            raise BusinessRuleError(
                "Cross-currency approved labor requires an enterprise FX provider.",
                code="APPROVED_TIME_FX_PROVIDER_REQUIRED",
            )
        hours = source.hours.to_domain().value
        money = Money.of(hours * rate_money.amount, rate_money.currency.code).rounded()
        if money.amount <= 0:
            raise BusinessRuleError("Approved labor cost must be positive.", code="APPROVED_TIME_COST_INVALID")
        period = self._financial_period_service.require_open_period_for_integration(
            source.work_date
        )
        actor_id = "integration:project_finance"
        now = self._clock.now()
        reversal = None
        if latest is not None:
            original = self._entry_repo.get(latest.actual_cost_entry_id, for_update=True)
            if original is None or original.status != ProjectCostEntryStatus.POSTED:
                raise BusinessRuleError("Prior approved labor posting is not reversible.", code="APPROVED_TIME_PRIOR_POSTING_INVALID")
            reversal_source = FinancialSourceReference(
                tenant_id=reference.tenant_id,
                organization_id=reference.organization_id,
                project_id=reference.project_id,
                source_module=reference.source_module,
                source_type=reference.source_type,
                source_id=reference.source_id,
                source_line_id=f"reversal:{latest.source_revision}",
                source_revision=reference.source_revision,
                content_hash=financial_source_content_hash({"reverses_entry_id": original.id, "replacement_hash": reference.content_hash}),
                posting_purpose=reference.posting_purpose,
            )
            reversal = ProjectCostEntry.create_posted_reversal(
                original=original,
                reversal_id=generate_id(),
                description=f"Approved Time correction reversal for {source.time_entry_id}",
                source=reversal_source,
                posting_date=source.work_date,
                financial_period_id=period.id,
                actor_id=actor_id,
                occurred_at=now,
            )
            self._entry_repo.add(reversal)
            self._entry_repo.flush()
            original_version = original.row_version
            original.mark_reversed(reversal_entry_id=reversal.id, actor_id=actor_id, occurred_at=now)
            self._entry_repo.update(original, expected_row_version=original_version)

        entry = ProjectCostEntry.create_draft(
            tenant_id=reference.tenant_id,
            organization_id=reference.organization_id,
            project_id=reference.project_id,
            description=f"Approved labor for {source.work_date.isoformat()}",
            kind=ProjectCostEntryKind.ACTUAL,
            money=money,
            transaction_date=source.work_date,
            cost_code_id=profile.default_cost_code_id,
            task_id=source.task_id,
            resource_id=source.resource_id,
            source=reference,
            actor_id=actor_id,
            occurred_at=now,
        )
        entry.submit(actor_id=actor_id, occurred_at=now)
        entry.approve(actor_id=actor_id, occurred_at=now)
        entry.post(
            actor_id=actor_id,
            occurred_at=now,
            posting_date=source.work_date,
            financial_period_id=period.id,
            base_money=money,
            exchange_rate=Decimal("1"),
            exchange_rate_date=source.work_date,
            exchange_rate_source="identity",
            exchange_rate_captured_at=now,
        )
        self._entry_repo.add(entry)
        self._labor_posting_repo.add(ApprovedTimeLaborPosting(
            id=generate_id(), tenant_id=reference.tenant_id,
            organization_id=reference.organization_id, project_id=reference.project_id,
            time_entry_id=source.time_entry_id, source_revision=revision,
            source_content_hash=reference.content_hash,
            approved_snapshot_id=source.approved_snapshot_id,
            timesheet_period_id=source.timesheet_period_id,
            actual_cost_entry_id=entry.id,
            reversal_cost_entry_id=reversal.id if reversal else None,
            hours=hours, work_date=source.work_date, rate_amount=rate_money.amount,
            rate_currency=rate_money.currency.code, rate_card_id=snapshot.rate_card_id,
            rate_line_id=snapshot.rate_line_id, rate_card_version=snapshot.rate_card_version,
            rate_precedence_level=snapshot.precedence_level,
            rate_effective_date=snapshot.effective_date, rate_resolved_at=snapshot.resolved_at,
            approved_at=source.approved_at, resource_id=source.resource_id,
            task_id=source.task_id, employee_id=source.employee_id, created_at=now,
        ))
        self._entry_repo.flush()
        self._labor_posting_repo.flush()
        events: list[object] = []
        if reversal is not None:
            self._record_audit("create_approved_time_reversal", reversal)
            reversal_event = CostEntryReversed(
                tenant_id=original.tenant_id,
                organization_id=original.organization_id,
                project_id=original.project_id,
                cost_entry_id=reversal.id,
                reverses_entry_id=original.id,
                occurred_at=now,
            )
            if self._record_event is not None:
                self._record_event(reversal_event)
            events.append(reversal_event)
        self._record_audit("post_approved_time", entry)
        recorded_event = CostEntryRecorded(
            tenant_id=entry.tenant_id,
            organization_id=entry.organization_id,
            project_id=entry.project_id,
            cost_entry_id=entry.id,
            status=entry.status,
            occurred_at=now,
        )
        if self._record_event is not None:
            self._record_event(recorded_event)
        events.append(recorded_event)
        return tuple(events)

    def apply_procurement_receipt_source(
        self, source: ProcurementReceiptAccrualFinancialSource
    ) -> tuple[ProjectCostEntry, tuple[object, ...]]:
        """Post one trusted Procurement receipt fact without committing the inbox transaction.
        Returns the entry (its id is needed by the caller to match it to a Commitment line) and
        the real typed Cost Entry DomainEvent(s) produced -- a true replay returns an empty
        event tuple."""
        context = self._require_full_context("post Procurement receipt accrual")
        reference = source.reference
        if (
            reference.tenant_id != context.tenant_id
            or reference.organization_id != context.organization_id
        ):
            raise BusinessRuleError(
                "Procurement receipt source is outside the active scope.",
                code="PROCUREMENT_RECEIPT_SCOPE_MISMATCH",
            )
        self._require_project(reference.project_id)
        profile = self._require_active_profile(reference.project_id)
        if not profile.default_cost_code_id:
            raise BusinessRuleError(
                "Project requires a default cost code before receipt accruals can post.",
                code="PROCUREMENT_RECEIPT_DEFAULT_COST_CODE_REQUIRED",
            )
        posting_date = source.posted_at.date()
        self._require_dimensions(
            project_id=reference.project_id,
            cost_code_id=profile.default_cost_code_id,
            transaction_date=posting_date,
            task_id=source.task_id,
            resource_id=None,
            organization_id=context.organization_id,
        )
        quantity = source.accepted_quantity.to_domain()
        rate = source.unit_cost.to_domain()
        money = rate.apply(quantity).rounded()
        if money.currency.code != context.organization.base_currency:
            raise BusinessRuleError(
                "Cross-currency receipt accruals require an enterprise FX provider.",
                code="PROCUREMENT_RECEIPT_FX_PROVIDER_REQUIRED",
            )
        if money.amount <= 0:
            raise BusinessRuleError(
                "Procurement receipt accrual must be positive.",
                code="PROCUREMENT_RECEIPT_AMOUNT_INVALID",
            )
        existing = self._entry_repo.get_by_idempotency_key(reference.idempotency_key)
        if existing is not None:
            return self._resolve_replay(existing, reference), ()
        period = self._financial_period_service.require_open_period_for_integration(
            posting_date
        )
        actor_id = "integration:project_finance"
        now = self._clock.now()
        entry = ProjectCostEntry.create_draft(
            tenant_id=reference.tenant_id,
            organization_id=reference.organization_id,
            project_id=reference.project_id,
            description=f"Receipt accrual {source.receipt_number}",
            kind=ProjectCostEntryKind.ACTUAL,
            money=money,
            transaction_date=posting_date,
            cost_code_id=profile.default_cost_code_id,
            task_id=source.task_id,
            resource_id=None,
            source=reference,
            actor_id=actor_id,
            occurred_at=now,
        )
        entry.submit(actor_id=actor_id, occurred_at=now)
        entry.approve(actor_id=actor_id, occurred_at=now)
        entry.post(
            actor_id=actor_id,
            occurred_at=now,
            posting_date=posting_date,
            financial_period_id=period.id,
            base_money=money,
            exchange_rate=Decimal("1"),
            exchange_rate_date=posting_date,
            exchange_rate_source="identity",
            exchange_rate_captured_at=now,
        )
        self._entry_repo.add(entry)
        self._entry_repo.flush()
        self._record_audit("post_procurement_receipt", entry)
        event = CostEntryRecorded(
            tenant_id=entry.tenant_id,
            organization_id=entry.organization_id,
            project_id=entry.project_id,
            cost_entry_id=entry.id,
            status=entry.status,
            occurred_at=now,
        )
        if self._record_event is not None:
            self._record_event(event)
        return entry, (event,)

    def get_entry(self, entry_id: str) -> ProjectCostEntry:
        require_permission(self._user_session, "finance.read", operation_label="view project cost entry")
        entry = self._require_entry(entry_id)
        require_project_permission(
            self._user_session,
            entry.project_id,
            "finance.read",
            operation_label="view project cost entry",
        )
        return entry

    def list_for_project(
        self,
        project_id: str,
        *,
        status: ProjectCostEntryStatus | str | None = None,
        offset: int = 0,
        limit: int = 50,
        sort_key: str = "metaText",
        sort_direction: str = "desc",
    ) -> tuple[list[ProjectCostEntry], int]:
        require_permission(self._user_session, "finance.read", operation_label="list project cost entries")
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="list project cost entries",
        )
        try:
            resolved_status = ProjectCostEntryStatus(status) if status is not None else None
        except ValueError as exc:
            raise ValidationError(
                "Project cost entry status is invalid.",
                code="PROJECT_COST_ENTRY_STATUS_INVALID",
            ) from exc
        return self._entry_repo.list_for_project(
            project_id,
            status=resolved_status,
            offset=offset,
            limit=limit,
            sort=normalize_cost_entry_sort(
                key=sort_key,
                direction=sort_direction,
            ),
        )

    def create_manual_entry(
        self,
        *,
        project_id: str,
        command_id: str,
        description: str,
        amount: Decimal,
        currency_code: str,
        transaction_date: date,
        cost_code_id: str,
        entry_kind: ProjectCostEntryKind | str = ProjectCostEntryKind.ACTUAL,
        task_id: str | None = None,
        resource_id: str | None = None,
    ) -> ProjectCostEntry:
        self._require_command_permission(project_id, "project_cost.create", "create project cost entry")
        context = self._require_scope("create project cost entry")
        self._require_project(project_id)
        profile = self._require_active_profile(project_id)
        del profile
        kind = self._resolve_draft_kind(entry_kind)
        money = Money.of(amount, currency_code)
        self._require_dimensions(
            project_id=project_id,
            cost_code_id=cost_code_id,
            transaction_date=transaction_date,
            task_id=task_id,
            resource_id=resource_id,
            organization_id=context.organization_id,
        )
        source = self._manual_source(
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            project_id=project_id,
            command_id=command_id,
            content=self._manual_content(
                description=description,
                kind=kind,
                money=money,
                transaction_date=transaction_date,
                cost_code_id=cost_code_id,
                task_id=task_id,
                resource_id=resource_id,
            ),
        )
        existing = self._entry_repo.get_by_idempotency_key(source.idempotency_key)
        if existing is not None:
            return self._resolve_replay(existing, source)
        actor_id = self._actor_id()
        now = self._clock.now()
        entry = ProjectCostEntry.create_draft(
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            project_id=project_id,
            description=description,
            kind=kind,
            money=money,
            transaction_date=transaction_date,
            cost_code_id=cost_code_id,
            task_id=task_id,
            resource_id=resource_id,
            source=source,
            actor_id=actor_id,
            occurred_at=now,
        )
        try:
            self._entry_repo.add(entry)
            self._entry_repo.flush()
        except IntegrityError as exc:
            self._session.rollback()
            concurrent = self._entry_repo.get_by_idempotency_key(source.idempotency_key)
            if concurrent is not None:
                return self._resolve_replay(concurrent, source)
            raise BusinessRuleError(
                "Project cost entry conflicts with an existing financial source.",
                code="PROJECT_COST_ENTRY_SOURCE_CONFLICT",
            ) from exc
        self._record_audit("create", entry)
        event = CostEntryRecorded(
            tenant_id=entry.tenant_id,
            organization_id=entry.organization_id,
            project_id=entry.project_id,
            cost_entry_id=entry.id,
            status=entry.status,
            occurred_at=now,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return entry

    def update_draft(
        self,
        entry_id: str,
        *,
        expected_version: int,
        description: str,
        amount: Decimal,
        currency_code: str,
        transaction_date: date,
        cost_code_id: str,
        task_id: str | None = None,
        resource_id: str | None = None,
    ) -> ProjectCostEntry:
        entry = self._require_entry(entry_id)
        self._require_command_permission(
            entry.project_id, "project_cost.update_draft", "update project cost entry draft"
        )
        self._require_expected_version(entry, expected_version)
        context = self._require_scope("update project cost entry draft")
        money = Money.of(amount, currency_code)
        self._require_dimensions(
            project_id=entry.project_id,
            cost_code_id=cost_code_id,
            transaction_date=transaction_date,
            task_id=task_id,
            resource_id=resource_id,
            organization_id=context.organization_id,
        )
        content_hash = financial_source_content_hash(
            self._manual_content(
                description=description,
                kind=entry.entry_kind,
                money=money,
                transaction_date=transaction_date,
                cost_code_id=cost_code_id,
                task_id=task_id,
                resource_id=resource_id,
            )
        )
        actor_id = self._actor_id()
        entry.update_draft(
            description=description,
            amount=money.amount,
            currency_code=money.currency.code,
            transaction_date=transaction_date,
            cost_code_id=cost_code_id,
            task_id=task_id,
            resource_id=resource_id,
            source_content_hash=content_hash,
            updated_by=actor_id,
            updated_at=self._clock.now(),
        )
        self._entry_repo.update(entry, expected_row_version=expected_version)
        self._record_audit("update_draft", entry)
        event = CostEntryUpdated(
            tenant_id=entry.tenant_id,
            organization_id=entry.organization_id,
            project_id=entry.project_id,
            cost_entry_id=entry.id,
            occurred_at=entry.updated_at,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return entry

    def delete_draft(self, entry_id: str, *, expected_version: int) -> None:
        entry = self._require_entry(entry_id)
        self._require_command_permission(
            entry.project_id, "project_cost.update_draft", "delete project cost entry draft"
        )
        self._require_expected_version(entry, expected_version)
        if not entry.is_draft:
            raise BusinessRuleError(
                "Only a draft project cost entry can be deleted.",
                code="PROJECT_COST_ENTRY_DELETE_FORBIDDEN",
            )
        self._entry_repo.delete_draft(entry.id, expected_row_version=expected_version)
        self._record_audit("delete_draft", entry)
        event = CostEntryRemoved(
            tenant_id=entry.tenant_id,
            organization_id=entry.organization_id,
            project_id=entry.project_id,
            cost_entry_id=entry.id,
            occurred_at=self._clock.now(),
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()

    def submit(self, entry_id: str, *, expected_version: int) -> ProjectCostEntry:
        entry = self._require_entry(entry_id)
        self._require_command_permission(entry.project_id, "project_cost.submit", "submit project cost entry")
        self._require_expected_version(entry, expected_version)
        entry.submit(actor_id=self._actor_id(), occurred_at=self._clock.now())
        self._entry_repo.update(entry, expected_row_version=expected_version)
        self._record_audit("submit", entry)
        event = CostEntryStatusChanged(
            tenant_id=entry.tenant_id,
            organization_id=entry.organization_id,
            project_id=entry.project_id,
            cost_entry_id=entry.id,
            change_type=CostEntryStatusChangeType.SUBMITTED,
            occurred_at=entry.updated_at,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return entry

    def approve(
        self,
        entry_id: str,
        *,
        expected_version: int,
        notes: str = "",
    ) -> CostEntryApprovalResult:
        entry = self._require_entry(entry_id)
        governed = self._approval_service is not None and is_governance_required(
            "project_cost.approve"
        )
        permission = "approval.request" if governed else "project_cost.approve"
        operation = "request project cost approval" if governed else "approve project cost entry"
        self._require_command_permission(entry.project_id, permission, operation)
        self._require_expected_version(entry, expected_version)
        if entry.status != ProjectCostEntryStatus.SUBMITTED:
            raise BusinessRuleError(
                "Only a submitted project cost entry can be approved.",
                code="PROJECT_COST_ENTRY_APPROVE_INVALID",
            )
        if governed:
            request = self._approval_service.request_change(
                request_type="project_cost.approve",
                entity_type="project_cost_entry",
                entity_id=entry.id,
                project_id=entry.project_id,
                payload={
                    "entry_id": entry.id,
                    "expected_version": expected_version,
                    "notes": notes,
                },
            )
            return CostEntryApprovalResult(
                outcome=CostEntryApprovalOutcome.PENDING_APPROVAL,
                entry_id=entry.id,
                project_id=entry.project_id,
                status=entry.status,
                row_version=entry.row_version,
                approval_request_id=request.id,
            )
        approved, _event = self._apply_approval_decision(
            entry_id=entry.id,
            expected_version=expected_version,
            actor_id=self._actor_id(),
        )
        return CostEntryApprovalResult(
            outcome=CostEntryApprovalOutcome.APPLIED,
            entry_id=approved.id,
            project_id=approved.project_id,
            status=approved.status,
            row_version=approved.row_version,
        )

    def reject(
        self,
        entry_id: str,
        *,
        expected_version: int,
        notes: str = "",
    ) -> ProjectCostEntry:
        entry = self._require_entry(entry_id)
        self._require_command_permission(entry.project_id, "project_cost.approve", "reject project cost entry")
        rejected, _event = self._apply_rejection_decision(
            entry_id=entry.id,
            expected_version=expected_version,
            actor_id=self._actor_id(),
            notes=notes,
        )
        return rejected

    def post(
        self,
        entry_id: str,
        *,
        expected_version: int,
        posting_date: date,
        exchange_rate: Decimal | None = None,
        exchange_rate_date: date | None = None,
        exchange_rate_source: str | None = None,
        exchange_rate_captured_at: datetime | None = None,
    ) -> ProjectCostEntry:
        entry = self._require_entry(entry_id)
        self._require_command_permission(entry.project_id, "project_cost.post", "post project cost entry")
        self._require_expected_version(entry, expected_version)
        profile = self._require_active_profile(entry.project_id)
        del profile
        period = self._financial_period_service.require_open_period_for_date(posting_date)
        context = self._require_full_context("post project cost entry")
        base_currency = context.organization.base_currency
        rate, rate_date, rate_source, captured_at = self._resolve_fx_snapshot(
            entry=entry,
            base_currency=base_currency,
            posting_date=posting_date,
            exchange_rate=exchange_rate,
            exchange_rate_date=exchange_rate_date,
            exchange_rate_source=exchange_rate_source,
            exchange_rate_captured_at=exchange_rate_captured_at,
        )
        base_money = Money.of(entry.amount * rate, base_currency).rounded()
        entry.post(
            actor_id=self._actor_id(),
            occurred_at=self._clock.now(),
            posting_date=posting_date,
            financial_period_id=period.id,
            base_money=base_money,
            exchange_rate=rate,
            exchange_rate_date=rate_date,
            exchange_rate_source=rate_source,
            exchange_rate_captured_at=captured_at,
        )
        self._entry_repo.update(entry, expected_row_version=expected_version)
        self._record_audit("post", entry)
        event = CostEntryStatusChanged(
            tenant_id=entry.tenant_id,
            organization_id=entry.organization_id,
            project_id=entry.project_id,
            cost_entry_id=entry.id,
            change_type=CostEntryStatusChangeType.POSTED,
            occurred_at=entry.updated_at,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return entry

    def reverse(
        self,
        entry_id: str,
        *,
        expected_version: int,
        command_id: str,
        posting_date: date,
        reason: str,
    ) -> ProjectCostEntry:
        entry = self._require_entry(entry_id, for_update=True)
        self._require_command_permission(entry.project_id, "project_cost.reverse", "reverse project cost entry")
        source = self._manual_source(
            tenant_id=entry.tenant_id,
            organization_id=entry.organization_id,
            project_id=entry.project_id,
            command_id=command_id,
            content={
                "operation": "reverse",
                "entry_id": entry.id,
                "expected_version": expected_version,
                "posting_date": posting_date.isoformat(),
                "reason": str(reason or "").strip(),
            },
        )
        existing = self._entry_repo.get_by_idempotency_key(source.idempotency_key)
        if existing is not None:
            return self._resolve_replay(existing, source)
        self._require_expected_version(entry, expected_version)
        period = self._financial_period_service.require_open_period_for_date(posting_date)
        actor_id = self._actor_id()
        now = self._clock.now()
        reversal_id = generate_id()
        reversal = ProjectCostEntry.create_posted_reversal(
            original=entry,
            reversal_id=reversal_id,
            description=str(reason or "").strip() or f"Reversal of {entry.description}",
            source=source,
            posting_date=posting_date,
            financial_period_id=period.id,
            actor_id=actor_id,
            occurred_at=now,
        )
        try:
            with self._session.begin_nested():
                self._entry_repo.add(reversal)
                self._entry_repo.flush()
                entry.mark_reversed(
                    reversal_entry_id=reversal.id,
                    actor_id=actor_id,
                    occurred_at=now,
                )
                self._entry_repo.update(entry, expected_row_version=expected_version)
                self._entry_repo.flush()
        except IntegrityError as exc:
            raise BusinessRuleError(
                "This project cost entry has already been reversed or the reversal source conflicts.",
                code="PROJECT_COST_ENTRY_REVERSAL_CONFLICT",
            ) from exc
        self._record_audit("reverse_original", entry)
        self._record_audit("create_reversal", reversal)
        event = CostEntryReversed(
            tenant_id=entry.tenant_id,
            organization_id=entry.organization_id,
            project_id=entry.project_id,
            cost_entry_id=reversal.id,
            reverses_entry_id=entry.id,
            occurred_at=now,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return reversal

    def _apply_approval_decision(
        self,
        *,
        entry_id: str,
        expected_version: int,
        actor_id: str,
    ) -> tuple[ProjectCostEntry, CostEntryStatusChanged]:
        entry = self._require_entry(entry_id)
        self._require_expected_version(entry, expected_version)
        entry.approve(actor_id=actor_id, occurred_at=self._clock.now())
        self._entry_repo.update(entry, expected_row_version=expected_version)
        self._record_audit("approve", entry)
        event = CostEntryStatusChanged(
            tenant_id=entry.tenant_id,
            organization_id=entry.organization_id,
            project_id=entry.project_id,
            cost_entry_id=entry.id,
            change_type=CostEntryStatusChangeType.APPROVED,
            occurred_at=entry.updated_at,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return entry, event

    def _apply_rejection_decision(
        self,
        *,
        entry_id: str,
        expected_version: int,
        actor_id: str,
        notes: str,
    ) -> tuple[ProjectCostEntry, CostEntryStatusChanged]:
        entry = self._require_entry(entry_id)
        self._require_expected_version(entry, expected_version)
        entry.reject(actor_id=actor_id, occurred_at=self._clock.now(), notes=notes)
        self._entry_repo.update(entry, expected_row_version=expected_version)
        self._record_audit("reject", entry)
        event = CostEntryStatusChanged(
            tenant_id=entry.tenant_id,
            organization_id=entry.organization_id,
            project_id=entry.project_id,
            cost_entry_id=entry.id,
            change_type=CostEntryStatusChangeType.REJECTED,
            occurred_at=entry.updated_at,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return entry, event

    def _require_dimensions(
        self,
        *,
        project_id: str,
        cost_code_id: str,
        transaction_date: date,
        task_id: str | None,
        resource_id: str | None,
        organization_id: str,
    ) -> None:
        cost_code = self._cost_code_repo.get(cost_code_id)
        if cost_code is None:
            raise NotFoundError("Cost code not found.", code="PROJECT_COST_ENTRY_COST_CODE_NOT_FOUND")
        if not cost_code.is_effective_on(transaction_date):
            raise BusinessRuleError(
                "Cost code is not active or effective on the transaction date.",
                code="PROJECT_COST_ENTRY_COST_CODE_INACTIVE",
            )
        profile = self._require_active_profile(project_id)
        if profile.cost_code_policy == CostCodePolicy.RESTRICTED:
            allowed = {
                restriction.cost_code_id
                for restriction in self._cost_code_repo.list_restrictions(project_id)
            }
            if cost_code_id not in allowed:
                raise BusinessRuleError(
                    "This cost code is not permitted for the project.",
                    code="PROJECT_COST_ENTRY_COST_CODE_NOT_PERMITTED",
                )
        if task_id:
            task = self._task_repo.get(task_id)
            if task is None:
                raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
            if task.project_id != project_id:
                raise BusinessRuleError(
                    "Task does not belong to the project.",
                    code="PROJECT_COST_ENTRY_TASK_PROJECT_MISMATCH",
                )
        if resource_id:
            resource = self._resource_repo.get(resource_id)
            if resource is None:
                raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")
            if resource.organization_id != organization_id:
                raise BusinessRuleError(
                    "Resource does not belong to the active organization.",
                    code="PROJECT_COST_ENTRY_RESOURCE_SCOPE_MISMATCH",
                )

    def _require_active_profile(self, project_id: str):
        profile = self._financial_profile_repo.get_by_project(project_id)
        if profile is None:
            raise NotFoundError(
                "Project financial profile is required before recording actual costs.",
                code="PROJECT_FINANCIAL_PROFILE_NOT_FOUND",
            )
        if profile.status != FinancialProfileStatus.ACTIVE:
            raise BusinessRuleError(
                "Project financial profile must be active for actual-cost commands.",
                code="PROJECT_FINANCIAL_PROFILE_NOT_ACTIVE",
            )
        return profile

    def _resolve_fx_snapshot(
        self,
        *,
        entry: ProjectCostEntry,
        base_currency: str,
        posting_date: date,
        exchange_rate: Decimal | None,
        exchange_rate_date: date | None,
        exchange_rate_source: str | None,
        exchange_rate_captured_at: datetime | None,
    ) -> tuple[Decimal, date, str, datetime]:
        if entry.currency_code == base_currency:
            if exchange_rate not in (None, Decimal("1"), 1, "1"):
                raise ValidationError(
                    "Identity-currency postings must use an exchange rate of 1.",
                    code="PROJECT_COST_ENTRY_IDENTITY_RATE_INVALID",
                )
            return Decimal("1"), posting_date, "identity", self._clock.now()
        if (
            exchange_rate is None
            or exchange_rate_date is None
            or not str(exchange_rate_source or "").strip()
            or exchange_rate_captured_at is None
        ):
            raise ValidationError(
                "Cross-currency postings require a complete exchange-rate snapshot.",
                code="PROJECT_COST_ENTRY_FX_SNAPSHOT_REQUIRED",
            )
        rate = EXCHANGE_RATE_STORAGE.validate(exchange_rate)
        if rate <= 0:
            raise ValidationError(
                "Exchange rate must be positive.",
                code="PROJECT_COST_ENTRY_EXCHANGE_RATE_INVALID",
            )
        if exchange_rate_captured_at.tzinfo is None or exchange_rate_captured_at.utcoffset() is None:
            raise ValidationError(
                "Exchange-rate capture timestamp must include a timezone.",
                code="PROJECT_COST_ENTRY_FX_CAPTURE_TIME_INVALID",
            )
        return rate, exchange_rate_date, str(exchange_rate_source).strip(), exchange_rate_captured_at

    @staticmethod
    def _manual_content(
        *,
        description: str,
        kind: ProjectCostEntryKind,
        money: Money,
        transaction_date: date,
        cost_code_id: str,
        task_id: str | None,
        resource_id: str | None,
    ) -> dict[str, object]:
        return {
            "description": str(description or "").strip(),
            "entry_kind": kind.value,
            "amount": MoneyPayload.from_domain(money).amount,
            "currency_code": money.currency.code,
            "transaction_date": transaction_date.isoformat(),
            "cost_code_id": str(cost_code_id or "").strip(),
            "task_id": str(task_id or "").strip() or None,
            "resource_id": str(resource_id or "").strip() or None,
        }

    @staticmethod
    def _manual_source(
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        command_id: str,
        content: dict[str, object],
    ) -> FinancialSourceReference:
        return FinancialSourceReference(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            source_module=FinancialSourceModule.PROJECT_MANAGEMENT,
            source_type=FinancialSourceType.MANUAL_COMMAND,
            source_id=command_id,
            source_revision="1",
            content_hash=financial_source_content_hash(content),
            posting_purpose=FinancialPostingPurpose.MANUAL_ACTUAL,
        )

    @staticmethod
    def _resolve_draft_kind(value: ProjectCostEntryKind | str) -> ProjectCostEntryKind:
        try:
            kind = ProjectCostEntryKind(value)
        except ValueError as exc:
            raise ValidationError(
                "Project cost entry kind is invalid.",
                code="PROJECT_COST_ENTRY_KIND_INVALID",
            ) from exc
        if kind == ProjectCostEntryKind.REVERSAL:
            raise ValidationError(
                "Reversals can only be created through the reversal command.",
                code="PROJECT_COST_ENTRY_DRAFT_REVERSAL_FORBIDDEN",
            )
        return kind

    @staticmethod
    def _resolve_replay(
        existing: ProjectCostEntry, source: FinancialSourceReference
    ) -> ProjectCostEntry:
        if (
            existing.project_id == source.project_id
            and existing.source_content_hash == source.content_hash
        ):
            return existing
        raise BusinessRuleError(
            "The financial source identity was already used with different content or scope.",
            code="PROJECT_COST_ENTRY_SOURCE_REPLAY_CONFLICT",
        )

    def _require_entry(self, entry_id: str, *, for_update: bool = False) -> ProjectCostEntry:
        entry = self._entry_repo.get(entry_id, for_update=for_update)
        if entry is None:
            raise NotFoundError("Project cost entry not found.", code="PROJECT_COST_ENTRY_NOT_FOUND")
        return entry

    def _require_project(self, project_id: str) -> None:
        if self._project_repo.get(project_id) is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

    @staticmethod
    def _require_expected_version(entry: ProjectCostEntry, expected_version: int) -> None:
        if entry.row_version != expected_version:
            raise ConcurrencyError(
                "Project cost entry changed since you opened it.",
                code="STALE_WRITE",
            )

    def _require_command_permission(self, project_id: str, permission: str, operation: str) -> None:
        require_permission(self._user_session, permission, operation_label=operation)
        require_project_permission(
            self._user_session,
            project_id,
            permission,
            operation_label=operation,
        )

    def _require_scope(self, operation_label: str):
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                f"Active organization context is required to {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(operation_label=operation_label)

    def _require_full_context(self, operation_label: str):
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                f"Active organization context is required to {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        context = self._tenant_context_service.require_organization_context(
            operation_label=operation_label
        )
        if context.organization is None:
            raise BusinessRuleError(
                "Active organization is required for project cost posting.",
                code="ORGANIZATION_CONTEXT_REQUIRED",
            )
        return context

    def _actor_id(self) -> str:
        principal = getattr(self._user_session, "principal", None)
        actor_id = getattr(principal, "user_id", None)
        if not actor_id:
            raise BusinessRuleError(
                "An authenticated actor is required for project cost commands.",
                code="PROJECT_COST_ENTRY_ACTOR_REQUIRED",
            )
        return str(actor_id)

    def _record_audit(self, operation: str, entry: ProjectCostEntry) -> None:
        try:
            record_audit_entry(
                self,
                operation=f"project_cost_entry.{operation}",
                entity_type="project_cost_entry",
                entity_id=entry.id,
                entity_parent_id=entry.project_id,
                module="project_management",
                old_value=None,
                new_value=json.dumps({
                    "status": entry.status.value,
                    "entry_kind": entry.entry_kind.value,
                    "amount": MoneyPayload.from_domain(entry.money).amount,
                    "currency_code": entry.currency_code,
                    "base_amount": (
                        MoneyPayload.from_domain(entry.base_money).amount
                        if entry.base_money is not None
                        else None
                    ),
                    "base_currency_code": entry.base_currency_code,
                    "transaction_date": entry.transaction_date.isoformat(),
                    "posting_date": entry.posting_date.isoformat() if entry.posting_date else None,
                    "financial_period_id": entry.financial_period_id,
                    "cost_code_id": entry.cost_code_id,
                    "task_id": entry.task_id,
                    "resource_id": entry.resource_id,
                    "source_module": entry.source_module.value,
                    "source_type": entry.source_type.value,
                    "source_id": entry.source_id,
                    "source_revision": entry.source_revision,
                    "reverses_entry_id": entry.reverses_entry_id,
                    "reversed_by_entry_id": entry.reversed_by_entry_id,
                    "row_version": entry.row_version,
                }, sort_keys=True),
                workspace_id=entry.project_id,
                source="application",
                severity="high",
                compliance_tag="financial",
                metadata={"action": operation},
                commit=False,
                fail_closed=True,
            )
        except Exception:
            self._session.rollback()
            raise


__all__ = ["ProjectCostEntryService"]
