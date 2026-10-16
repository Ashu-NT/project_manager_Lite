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
    BillingScheduleLineAdded,
    BillingScheduleLineMarkedReady,
)
from src.core.modules.project_management.application.financials.invoicing.dto.commands.billing_schedule import (
    FinancialAddBillingScheduleLineCommand,
    FinancialMarkBillingScheduleLineReadyCommand,
)
from src.core.modules.project_management.application.financials.invoicing.dto.responses.billing import (
    FinancialBillingScheduleLineDto,
)
from src.core.modules.project_management.application.financials.invoicing.mappers.billing import (
    serialize_billing_schedule_line,
)
from src.core.modules.project_management.contracts.repositories.finance.invoicing.billing import (
    ProjectBillingRepository,
)
from src.core.modules.project_management.domain.financials.billing_profile import (
    BillingProfileStatus,
    ProjectBillingProfile,
    ProjectBillingScheduleLine,
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


class ProjectBillingScheduleCommandHandler(ProjectManagementModuleGuardMixin):
    """Own schedule-line provisioning and readiness in the caller's transaction."""

    def __init__(
        self,
        *,
        session: Session,
        billing_repo: ProjectBillingRepository,
        tenant_context_service: TenantContextService,
        clock: CalendarClock,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        record_event: Callable[[object], None] | None = None,
    ) -> None:
        self._session = session
        self._billing_repo = billing_repo
        self._tenant_context_service = tenant_context_service
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._record_event = record_event

    def add_schedule_line(self, command: FinancialAddBillingScheduleLineCommand) -> FinancialBillingScheduleLineDto:
        self._require(command.project_id, "finance.manage", "add billing schedule line")
        profile = self._require_profile(command.project_id)
        if profile.status is BillingProfileStatus.CLOSED:
            raise BusinessRuleError(
                "A closed billing profile cannot accept schedule lines.",
                code="BILLING_PROFILE_CLOSED",
            )
        actor_id = self._actor_id()
        line = ProjectBillingScheduleLine.create(
            tenant_id=profile.tenant_id,
            organization_id=profile.organization_id,
            project_id=command.project_id,
            billing_profile_id=profile.id,
            name=command.name,
            amount=command.amount,
            currency_code=profile.currency_code,
            due_date=command.due_date,
            task_id=command.task_id,
            acceptance_reference=command.acceptance_reference,
            created_by=actor_id,
            created_at=self._clock.now(),
        )
        event = BillingScheduleLineAdded(
            tenant_id=line.tenant_id,
            organization_id=line.organization_id,
            project_id=line.project_id,
            billing_profile_id=line.billing_profile_id,
            schedule_line_id=line.id,
            occurred_at=line.created_at,
        )
        return serialize_billing_schedule_line(self._persist(
            "schedule_line.create", line, lambda: self._billing_repo.add_schedule_line(line), event
        ))

    def mark_schedule_line_ready(self, command: FinancialMarkBillingScheduleLineReadyCommand) -> FinancialBillingScheduleLineDto:
        line = self._require_schedule_line(command.line_id)
        self._require(line.project_id, "finance.manage", "mark billing schedule line ready")
        now = self._clock.now()
        line.mark_ready(actor_id=self._actor_id(), occurred_at=now)
        event = BillingScheduleLineMarkedReady(
            tenant_id=line.tenant_id,
            organization_id=line.organization_id,
            project_id=line.project_id,
            billing_profile_id=line.billing_profile_id,
            schedule_line_id=line.id,
            occurred_at=now,
        )
        return serialize_billing_schedule_line(self._persist(
            "schedule_line.ready",
            line,
            lambda: self._billing_repo.update_schedule_line(
                line, expected_row_version=command.expected_version
            ),
            event,
        ))

    def _require_profile(self, project_id: str) -> ProjectBillingProfile:
        profile = self._billing_repo.get_profile(project_id)
        if profile is None:
            raise NotFoundError(
                "Project billing profile not found.", code="BILLING_PROFILE_NOT_FOUND"
            )
        return profile

    def _require_schedule_line(self, line_id: str) -> ProjectBillingScheduleLine:
        line = self._billing_repo.get_schedule_line(line_id)
        if line is None:
            raise NotFoundError(
                "Billing schedule line not found.", code="BILLING_SCHEDULE_LINE_NOT_FOUND"
            )
        return line

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

    def _persist(self, operation: str, entity, write, event: object):
        write()
        self._billing_repo.flush()
        full_operation = f"project_billing.{operation}"
        record_audit_entry(
            self,
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
            self,
            action=full_operation,
            entity_type=type(entity).__name__,
            entity_id=entity.id,
            parent_entity_id=entity.project_id,
            module="project_management",
            workspace_id=entity.project_id,
            details={"action": operation},
            commit=False,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return entity

__all__ = ["ProjectBillingScheduleCommandHandler"]
