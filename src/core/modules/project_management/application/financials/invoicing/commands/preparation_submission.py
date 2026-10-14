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
from src.core.modules.project_management.contracts.approval import (
    pm_reviewer_permission,
)
from src.core.modules.project_management.contracts.repositories.finance.invoicing.billing import (
    ProjectBillingRepository,
)
from src.core.modules.project_management.domain.financials.billing_preparation import (
    ProjectBillingPreparation,
)
from src.core.platform.application.approval.approval_mutation_participant import (
    request_approval_using,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.contract.repositories.approval.contracts import (
    ApprovalRepository,
)
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.time.clock import CalendarClock


class BillingPreparationSubmissionCommandHandler(ProjectManagementModuleGuardMixin):
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

    def submit_preparation(
        self, preparation_id: str, *, expected_row_version: int
    ) -> ProjectBillingPreparation:
        if self._approval_repo is None or self._record_event is None:
            raise BusinessRuleError(
                "Billing preparation submission requires the Finance governance command boundary.",
                code="BILLING_PREPARATION_COMMAND_BOUNDARY_REQUIRED",
            )
        preparation = self._require_preparation(preparation_id)
        self._require(preparation.project_id, "finance.manage", "submit billing preparation")
        if preparation.row_version != expected_row_version:
            raise BusinessRuleError("Billing preparation changed.", code="STALE_WRITE")
        now = self._clock.now()
        principal = self._user_session.principal if self._user_session else None
        request = request_approval_using(
            approval_repo=self._approval_repo,
            enterprise_audit_service=self._enterprise_audit_service,
            clock=self._clock,
            record_event=self._record_event,
            request_type="project_billing_preparation.approve",
            decision_permission=pm_reviewer_permission("project_billing_preparation.approve"),
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
        self._billing_repo.update_preparation(preparation, expected_row_version=expected_row_version)
        self._audit("submit", preparation)
        event = BillingPreparationStatusChanged(
            tenant_id=preparation.tenant_id,
            organization_id=preparation.organization_id,
            project_id=preparation.project_id,
            billing_preparation_id=preparation.id,
            change_type=BillingPreparationStatusChangeType.SUBMITTED,
            occurred_at=now,
        )
        self._record_event(event)
        self._session.flush()
        return preparation

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

__all__ = ["BillingPreparationSubmissionCommandHandler"]
