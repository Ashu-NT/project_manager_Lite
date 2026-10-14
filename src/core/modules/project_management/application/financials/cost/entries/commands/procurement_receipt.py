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
)
from src.core.modules.project_management.contracts.financial_sources.procurement import (
    ProcurementReceiptAccrualFinancialSource,
)
from src.core.modules.project_management.contracts.financial_sources.reference import (
    FinancialSourceReference,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectCostCodeRepository,
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.cost_entries.cost_entry import (
    ProjectCostEntryRepository,
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
)
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
from src.core.shared.time.clock import CalendarClock

if TYPE_CHECKING:
    from src.core.modules.project_management.application.financials.integration.procurement_consumer import (
        ProcurementExecutionContext,
    )


class ProcurementReceiptCostEntryCommandHandler(ProjectManagementModuleGuardMixin):
    """Post trusted receipt facts within the consumer's transaction."""

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
        self._record_event = record_event

    def apply_procurement_receipt_source(
        self,
        source: ProcurementReceiptAccrualFinancialSource,
        *,
        execution: ProcurementExecutionContext,
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
        existing = self._entry_repo.get_by_source_identity(reference, for_update=True)
        if existing is not None:
            if existing.idempotency_key == reference.idempotency_key:
                return self._resolve_replay(existing, reference), ()
            raise BusinessRuleError(
                "A changed receipt revision requires an explicit correction contract.",
                code="PROCUREMENT_RECEIPT_CORRECTION_CONTRACT_REQUIRED",
            )
        period = self._financial_period_queries.require_open_period_for_integration(
            posting_date
        )
        actor_id = execution.service_principal.id
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
            exchange_rate=Decimal(1),
            exchange_rate_date=posting_date,
            exchange_rate_source="identity",
            exchange_rate_captured_at=now,
        )
        self._entry_repo.add(entry)
        self._entry_repo.flush()
        self._record_procurement_audit(
            "post_procurement_receipt",
            entry,
            execution=execution,
        )
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

    def _record_procurement_audit(
        self,
        operation: str,
        entry: ProjectCostEntry,
        *,
        execution: ProcurementExecutionContext,
    ) -> None:
        principal = execution.service_principal
        record_project_cost_entry_audit(
            self,
            operation=operation,
            entry=entry,
            actor_id=principal.id,
            actor_type="service_principal",
            actor_username=principal.name,
            request_id=execution.correlation_id or execution.source_event_id,
            metadata={
                "consumer_name": execution.consumer_name,
                "service_account_user_id": principal.user_id,
                "source_event_id": execution.source_event_id,
                "source_event_type": execution.source_event_type,
                "source_aggregate_id": execution.source_aggregate_id,
                "source_revision": execution.source_revision,
                "correlation_id": execution.correlation_id,
                "causation_id": execution.causation_id,
            },
        )


__all__ = ["ProcurementReceiptCostEntryCommandHandler"]
