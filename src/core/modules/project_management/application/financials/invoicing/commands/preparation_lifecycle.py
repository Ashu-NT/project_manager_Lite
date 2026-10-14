from __future__ import annotations

from collections.abc import Callable
from datetime import date

from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.invoicing.billing_events import (
    BillingPreparationCreated,
    BillingPreparationStatusChanged,
    BillingPreparationStatusChangeType,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.invoicing.billing import (
    ProjectBillingRepository,
)
from src.core.modules.project_management.domain.financials.billing_preparation import (
    BillingPreparationStatus,
    ProjectBillingPreparation,
)
from src.core.modules.project_management.domain.financials.billing_profile import (
    BillingProfileStatus,
)
from src.core.modules.project_management.domain.financials.configuration import (
    BillingMethod,
)
from src.core.platform.application.finance.queries.financial_period_query import (
    FinancialPeriodQueryHandler,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.time.clock import CalendarClock


class PreparationLifecycleCommandHandler(ProjectManagementModuleGuardMixin):
    """Own this preparation command family in the caller's transaction."""

    def __init__(
        self,
        *,
        session: Session,
        billing_repo: ProjectBillingRepository,
        tenant_context_service: TenantContextService,
        clock: CalendarClock,
        financial_profile_repo: ProjectFinancialProfileRepository,
        financial_period_queries: FinancialPeriodQueryHandler,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        record_event: Callable[[object], None] | None = None,
    ) -> None:
        self._session = session
        self._billing_repo = billing_repo
        self._tenant_context_service = tenant_context_service
        self._clock = clock
        self._financial_profile_repo = financial_profile_repo
        self._financial_period_queries = financial_period_queries
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._record_event = record_event

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
        self._financial_period_queries.require_open_period_for_integration(period_start)
        self._financial_period_queries.require_open_period_for_integration(period_end)
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
        event = BillingPreparationCreated(
            tenant_id=preparation.tenant_id,
            organization_id=preparation.organization_id,
            project_id=preparation.project_id,
            billing_preparation_id=preparation.id,
            occurred_at=preparation.created_at,
        )
        return self._write(
            "create", preparation, lambda: self._billing_repo.add_preparation(preparation), event
        )

    def cancel_draft_preparation(
        self, preparation_id: str, *, expected_row_version: int
    ) -> ProjectBillingPreparation:
        preparation = self._require_preparation(preparation_id)
        self._require(preparation.project_id, "finance.manage", "cancel draft billing preparation")
        preparation.ensure_draft()
        if preparation.row_version != expected_row_version:
            raise BusinessRuleError("Billing preparation changed.", code="STALE_WRITE")
        now = self._clock.now()
        preparation.cancel(occurred_at=now)
        locks = self._billing_repo.list_source_locks(preparation.id)
        for lock in locks:
            lock.release(occurred_at=now)
        event = BillingPreparationStatusChanged(
            tenant_id=preparation.tenant_id,
            organization_id=preparation.organization_id,
            project_id=preparation.project_id,
            billing_preparation_id=preparation.id,
            change_type=BillingPreparationStatusChangeType.CANCELLED,
            occurred_at=now,
        )
        def persist_cancellation() -> None:
            for lock in locks:
                self._billing_repo.update_source_lock(lock)
            self._billing_repo.update_preparation(
                preparation, expected_row_version=expected_row_version
            )

        return self._write(
            "cancel_draft",
            preparation,
            persist_cancellation,
            event,
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

__all__ = ["PreparationLifecycleCommandHandler"]
