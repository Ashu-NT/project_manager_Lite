from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.cost.entries.audit import (
    record_project_cost_entry_audit,
)
from src.core.modules.project_management.application.financials.cost.entries.cost_entry_events import (
    CostEntryRecorded,
    CostEntryReversed,
)
from src.core.modules.project_management.application.financials.rate_cards.rate_card_resolver import (
    RateCardResolver,
)
from src.core.modules.project_management.contracts.financial_sources.approved_time import (
    ApprovedTimeFinancialSource,
)
from src.core.modules.project_management.contracts.financial_sources.reference import (
    FinancialSourceReference,
    financial_source_content_hash,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectCostCodeRepository,
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.cost_entries.cost_entry import (
    ProjectCostEntryRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.cost_entries.labor_posting import (
    ApprovedTimeLaborPostingRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.modules.project_management.contracts.repositories.resources.resource import (
    ResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    TaskRepository,
)
from src.core.modules.project_management.domain.financials.configuration import (
    CostCodePolicy,
    FinancialProfileStatus,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntry,
    ProjectCostEntryKind,
    ProjectCostEntryStatus,
)
from src.core.modules.project_management.domain.financials.labor_posting import (
    ApprovedTimeLaborPosting,
)
from src.core.modules.project_management.domain.financials.rate_cards import RateType
from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.application.finance.queries.financial_period_query import (
    FinancialPeriodQueryHandler,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
)
from src.core.platform.domain.finance import Money
from src.core.shared.time.clock import CalendarClock

if TYPE_CHECKING:
    from src.core.modules.project_management.application.financials.cost.entries.approved_time_consumer import (
        ApprovedTimeExecutionContext,
    )


class ApprovedTimeCostEntryCommandHandler(ProjectManagementModuleGuardMixin):
    """Post approved-time revisions within the consumer's transaction."""

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
        financial_period_queries: FinancialPeriodQueryHandler,
        clock: CalendarClock,
        user_session=None,
        enterprise_audit_service=None,
        activity_service=None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None = None,
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
        self._financial_period_queries = financial_period_queries
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._activity_service = activity_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._rate_resolver = rate_resolver
        self._labor_posting_repo = labor_posting_repo
        self._record_event = record_event

    def apply_approved_time_source(
        self,
        source: ApprovedTimeFinancialSource,
        *,
        execution: ApprovedTimeExecutionContext,
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
        principal = execution.service_principal
        if (
            reference.tenant_id != context.tenant_id
            or reference.organization_id != context.organization_id
        ):
            raise BusinessRuleError(
                "Approved Time source is outside the active scope.",
                code="APPROVED_TIME_SCOPE_MISMATCH",
            )
        if (
            principal.tenant_id != reference.tenant_id
            or principal.organization_id != reference.organization_id
        ):
            raise BusinessRuleError(
                "Approved Time worker principal is outside the source scope.",
                code="APPROVED_TIME_WORKER_SCOPE_MISMATCH",
            )
        self._require_project(reference.project_id)
        profile = self._require_active_profile(reference.project_id)
        if not profile.default_cost_code_id:
            raise BusinessRuleError(
                "Project requires a default cost code before approved labor can post.",
                code="APPROVED_TIME_DEFAULT_COST_CODE_REQUIRED",
            )
        latest = self._labor_posting_repo.get_latest(
            source.time_entry_id, for_update=True
        )
        revision = int(reference.source_revision)
        if latest is not None:
            if (
                revision == latest.source_revision
                and reference.content_hash == latest.source_content_hash
            ):
                existing = self._entry_repo.get(latest.actual_cost_entry_id)
                if existing is None:
                    raise BusinessRuleError(
                        "Approved labor posting lost its ledger entry.",
                        code="APPROVED_TIME_LEDGER_INTEGRITY_FAILED",
                    )
                return ()
            if revision == latest.source_revision:
                raise BusinessRuleError(
                    "Approved Time revision was reused with different content.",
                    code="APPROVED_TIME_SOURCE_HASH_CONFLICT",
                )
            if revision < latest.source_revision:
                raise BusinessRuleError(
                    "Approved Time revision is older than the posted financial truth.",
                    code="APPROVED_TIME_STALE_REVISION",
                )
            if source.correction_of_revision != str(latest.source_revision):
                raise BusinessRuleError(
                    "Approved Time correction does not reference the latest posting.",
                    code="APPROVED_TIME_CORRECTION_CHAIN_INVALID",
                )
        elif revision != 1 or source.correction_of_revision is not None:
            raise BusinessRuleError(
                "First approved Time posting must be revision 1.",
                code="APPROVED_TIME_REVISION_GAP",
            )

        self._require_dimensions(
            project_id=reference.project_id,
            cost_code_id=profile.default_cost_code_id,
            transaction_date=source.work_date,
            task_id=source.task_id,
            resource_id=source.resource_id,
            organization_id=context.organization_id,
        )
        snapshot = self._rate_resolver.resolve_for_posting(
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
            raise BusinessRuleError(
                "Approved labor cost must be positive.",
                code="APPROVED_TIME_COST_INVALID",
            )
        period = self._financial_period_queries.require_open_period_for_integration(
            source.work_date
        )
        actor_id = principal.id
        now = self._clock.now()
        reversal = None
        if latest is not None:
            original = self._entry_repo.get(
                latest.actual_cost_entry_id, for_update=True
            )
            if original is None or original.status != ProjectCostEntryStatus.POSTED:
                raise BusinessRuleError(
                    "Prior approved labor posting is not reversible.",
                    code="APPROVED_TIME_PRIOR_POSTING_INVALID",
                )
            reversal_source = FinancialSourceReference(
                tenant_id=reference.tenant_id,
                organization_id=reference.organization_id,
                project_id=reference.project_id,
                source_module=reference.source_module,
                source_type=reference.source_type,
                source_id=reference.source_id,
                source_line_id=f"reversal:{latest.source_revision}",
                source_revision=reference.source_revision,
                content_hash=financial_source_content_hash(
                    {
                        "reverses_entry_id": original.id,
                        "replacement_hash": reference.content_hash,
                    }
                ),
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
            original.mark_reversed(
                reversal_entry_id=reversal.id, actor_id=actor_id, occurred_at=now
            )
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
            exchange_rate=Decimal(1),
            exchange_rate_date=source.work_date,
            exchange_rate_source="identity",
            exchange_rate_captured_at=now,
        )
        self._entry_repo.add(entry)
        self._labor_posting_repo.add(
            ApprovedTimeLaborPosting(
                id=generate_id(),
                tenant_id=reference.tenant_id,
                organization_id=reference.organization_id,
                project_id=reference.project_id,
                time_entry_id=source.time_entry_id,
                source_revision=revision,
                source_content_hash=reference.content_hash,
                approved_snapshot_id=source.approved_snapshot_id,
                timesheet_period_id=source.timesheet_period_id,
                actual_cost_entry_id=entry.id,
                reversal_cost_entry_id=reversal.id if reversal else None,
                hours=hours,
                work_date=source.work_date,
                rate_amount=rate_money.amount,
                rate_currency=rate_money.currency.code,
                rate_card_id=snapshot.rate_card_id,
                rate_line_id=snapshot.rate_line_id,
                rate_card_version=snapshot.rate_card_version,
                rate_line_version=snapshot.rate_line_version,
                rate_modifier=(
                    snapshot.modifier_applied.value
                    if snapshot.modifier_applied
                    else None
                ),
                rate_modifier_multiplier=snapshot.modifier_multiplier,
                rate_base_amount=snapshot.selected_base_rate.money.amount,
                rate_origin=snapshot.origin.value,
                rate_provenance_complete=True,
                rate_precedence_level=snapshot.precedence_level,
                rate_effective_date=snapshot.effective_date,
                rate_resolved_at=snapshot.resolved_at,
                approved_at=source.approved_at,
                resource_id=source.resource_id,
                task_id=source.task_id,
                employee_id=source.employee_id,
                created_at=now,
                worker_service_principal_id=principal.id,
                source_event_id=execution.source_event_id,
                correlation_id=execution.correlation_id,
                causation_id=execution.causation_id,
            )
        )
        self._entry_repo.flush()
        self._labor_posting_repo.flush()
        events: list[object] = []
        if reversal is not None and latest is not None and original is not None:
            self._record_approved_time_audit(
                "create_approved_time_reversal",
                reversal,
                execution=execution,
                prior_revision=latest.source_revision,
            )
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
        self._record_approved_time_audit(
            "post_approved_time",
            entry,
            execution=execution,
            prior_revision=latest.source_revision if latest is not None else None,
        )
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

    def _require_project(self, project_id: str) -> None:
        if self._project_repo.get(project_id) is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

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
            raise NotFoundError(
                "Cost code not found.", code="PROJECT_COST_ENTRY_COST_CODE_NOT_FOUND"
            )
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

    def _record_approved_time_audit(
        self,
        operation: str,
        entry: ProjectCostEntry,
        *,
        execution: ApprovedTimeExecutionContext,
        prior_revision: int | None,
    ) -> None:
        principal = execution.service_principal
        record_project_cost_entry_audit(
            self,
            operation=operation,
            entry=entry,
            actor_id=principal.id,
            actor_type="service_principal",
            actor_username=principal.name,
            request_id=execution.correlation_id,
            metadata={
                "consumer_name": execution.consumer_name,
                "service_account_user_id": principal.user_id,
                "source_event_id": execution.source_event_id,
                "source_revision": entry.source_revision,
                "prior_source_revision": prior_revision,
                "correlation_id": execution.correlation_id,
                "causation_id": execution.causation_id,
            },
        )


__all__ = ["ApprovedTimeCostEntryCommandHandler"]
