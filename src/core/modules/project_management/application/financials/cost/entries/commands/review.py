from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.cost.entries.approval_result import (
    CostEntryApprovalOutcome,
    CostEntryApprovalResult,
)
from src.core.modules.project_management.application.financials.cost.entries.audit import (
    record_project_cost_entry_audit,
)
from src.core.modules.project_management.application.financials.cost.entries.capabilities import (
    is_manual_actual_entry,
)
from src.core.modules.project_management.application.financials.cost.entries.cost_entry_events import (
    CostEntryStatusChanged,
    CostEntryStatusChangeType,
)
from src.core.modules.project_management.contracts.repositories.finance.cost_entries.cost_entry import (
    ProjectCostEntryRepository,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntry,
    ProjectCostEntryStatus,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
)
from src.core.platform.domain.approval.policy import is_governance_required
from src.core.shared.time.clock import CalendarClock


class ProjectCostEntryReviewCommandHandler(ProjectManagementModuleGuardMixin):
    """Caller-owned actual-cost review commands."""

    def __init__(
        self,
        *,
        session: Session,
        entry_repo: ProjectCostEntryRepository,
        clock: CalendarClock,
        user_session=None,
        enterprise_audit_service=None,
        activity_service=None,
        module_catalog_service=None,
        approval_commands=None,
        record_event: Callable[[object], None] | None = None,
    ) -> None:
        self._session = session
        self._entry_repo = entry_repo
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._activity_service = activity_service
        self._module_catalog_service = module_catalog_service
        self._approval_commands = approval_commands
        self._record_event = record_event

    def approve(
        self,
        entry_id: str,
        *,
        expected_version: int,
        notes: str = "",
    ) -> CostEntryApprovalResult:
        entry = self._require_entry(entry_id)
        self._require_manual_interactive_entry(entry, operation="approve")
        governed = self._approval_commands is not None and is_governance_required(
            "project_cost.approve"
        )
        permission = "approval.request" if governed else "project_cost.approve"
        operation = (
            "request project cost approval"
            if governed
            else "approve project cost entry"
        )
        self._require_command_permission(entry.project_id, permission, operation)
        self._require_expected_version(entry, expected_version)
        if entry.status != ProjectCostEntryStatus.SUBMITTED:
            raise BusinessRuleError(
                "Only a submitted project cost entry can be approved.",
                code="PROJECT_COST_ENTRY_APPROVE_INVALID",
            )
        if governed:
            request = self._approval_commands.request_change(
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
        self._require_manual_interactive_entry(entry, operation="reject")
        if self._approval_commands is not None and is_governance_required(
            "project_cost.approve"
        ):
            raise BusinessRuleError(
                "Governed actuals must be rejected through Platform Approval.",
                code="PROJECT_COST_ENTRY_PLATFORM_DECISION_REQUIRED",
            )
        self._require_command_permission(
            entry.project_id, "project_cost.approve", "reject project cost entry"
        )
        rejected, _event = self._apply_rejection_decision(
            entry_id=entry.id,
            expected_version=expected_version,
            actor_id=self._actor_id(),
            notes=notes,
        )
        return rejected

    def _require_entry(
        self, entry_id: str, *, for_update: bool = False
    ) -> ProjectCostEntry:
        entry = self._entry_repo.get(entry_id, for_update=for_update)
        if entry is None:
            raise NotFoundError(
                "Project cost entry not found.", code="PROJECT_COST_ENTRY_NOT_FOUND"
            )
        return entry

    @staticmethod
    def _require_manual_interactive_entry(
        entry: ProjectCostEntry, *, operation: str
    ) -> None:
        if not is_manual_actual_entry(entry):
            raise BusinessRuleError(
                f"Source-owned actuals cannot use the {operation} command in Project Finance.",
                code="PROJECT_COST_ENTRY_SOURCE_OWNED",
            )

    def _require_command_permission(
        self, project_id: str, permission: str, operation: str
    ) -> None:
        require_permission(self._user_session, permission, operation_label=operation)
        require_project_permission(
            self._user_session,
            project_id,
            permission,
            operation_label=operation,
        )

    @staticmethod
    def _require_expected_version(
        entry: ProjectCostEntry, expected_version: int
    ) -> None:
        if entry.row_version != expected_version:
            raise ConcurrencyError(
                "Project cost entry changed since you opened it.",
                code="STALE_WRITE",
            )

    def _apply_approval_decision(
        self,
        *,
        entry_id: str,
        expected_version: int,
        actor_id: str,
    ) -> tuple[ProjectCostEntry, CostEntryStatusChanged]:
        entry = self._require_entry(entry_id)
        self._require_manual_interactive_entry(entry, operation="approve")
        self._require_expected_version(entry, expected_version)
        self._require_independent_decision(entry, actor_id)
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

    def _actor_id(self) -> str:
        principal = getattr(self._user_session, "principal", None)
        actor_id = getattr(principal, "user_id", None)
        if not actor_id:
            raise BusinessRuleError(
                "An authenticated actor is required for project cost commands.",
                code="PROJECT_COST_ENTRY_ACTOR_REQUIRED",
            )
        return str(actor_id)

    def _apply_rejection_decision(
        self,
        *,
        entry_id: str,
        expected_version: int,
        actor_id: str,
        notes: str,
    ) -> tuple[ProjectCostEntry, CostEntryStatusChanged]:
        entry = self._require_entry(entry_id)
        self._require_manual_interactive_entry(entry, operation="reject")
        self._require_expected_version(entry, expected_version)
        self._require_independent_decision(entry, actor_id)
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

    @staticmethod
    def _require_independent_decision(entry: ProjectCostEntry, actor_id: str) -> None:
        if not entry.submitted_by or entry.submitted_by == actor_id:
            raise BusinessRuleError(
                "The submitter cannot approve or reject their own actual.",
                code="PROJECT_COST_ENTRY_SELF_DECISION_FORBIDDEN",
            )

    def _record_audit(self, operation: str, entry: ProjectCostEntry) -> None:
        record_project_cost_entry_audit(self, operation=operation, entry=entry)


__all__ = ["ProjectCostEntryReviewCommandHandler"]
