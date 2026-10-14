from __future__ import annotations

from collections.abc import Callable

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
from src.core.modules.project_management.domain.financials.billing_preparation import (
    ProjectBillingPreparation,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.contract.repositories.approval.contracts import (
    ApprovalRepository,
)
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.time.clock import CalendarClock


class BillingPreparationApprovalCommandHandler(ProjectManagementModuleGuardMixin):
    """Own this preparation command family in the caller's transaction."""

    def __init__(
        self,
        *,
        session: Session,
        billing_repo: ProjectBillingRepository,
        tenant_context_service: TenantContextService,
        clock: CalendarClock,
        approval_repo: ApprovalRepository | None,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        record_event: Callable[[object], None] | None = None,
    ) -> None:
        self._session = session
        self._billing_repo = billing_repo
        self._tenant_context_service = tenant_context_service
        self._clock = clock
        self._approval_repo = approval_repo
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._record_event = record_event

    def _apply_approval_decision(
        self, preparation_id: str, *, approved_by: str, expected_version: int
    ) -> tuple[ProjectBillingPreparation, object]:
        preparation = self._require_preparation(preparation_id)
        self._require(
            preparation.project_id,
            "approval.decide",
            "approve billing preparation",
        )
        now = self._clock.now()
        preparation.approve(approved_by=approved_by, approved_at=now)
        locks = self._billing_repo.list_source_locks(preparation.id)
        for lock in locks:
            lock.finalize(occurred_at=now)
            self._billing_repo.update_source_lock(lock)
        self._billing_repo.update_preparation(preparation, expected_row_version=expected_version)
        self._audit("approve", preparation)
        event = BillingPreparationStatusChanged(
            tenant_id=preparation.tenant_id,
            organization_id=preparation.organization_id,
            project_id=preparation.project_id,
            billing_preparation_id=preparation.id,
            change_type=BillingPreparationStatusChangeType.APPROVED,
            occurred_at=now,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return preparation, event

    def _apply_rejection_decision(
        self,
        preparation_id: str,
        *,
        rejected_by: str,
        expected_version: int,
        notes: str,
    ) -> tuple[ProjectBillingPreparation, object]:
        preparation = self._require_preparation(preparation_id)
        self._require(
            preparation.project_id,
            "approval.decide",
            "reject billing preparation",
        )
        now = self._clock.now()
        preparation.reject(rejected_by=rejected_by, rejected_at=now, notes=notes)
        for lock in self._billing_repo.list_source_locks(preparation.id):
            lock.release(occurred_at=now)
            self._billing_repo.update_source_lock(lock)
        self._billing_repo.update_preparation(preparation, expected_row_version=expected_version)
        self._audit("reject", preparation)
        event = BillingPreparationStatusChanged(
            tenant_id=preparation.tenant_id,
            organization_id=preparation.organization_id,
            project_id=preparation.project_id,
            billing_preparation_id=preparation.id,
            change_type=BillingPreparationStatusChangeType.REJECTED,
            occurred_at=now,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return preparation, event

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

__all__ = ["BillingPreparationApprovalCommandHandler"]
