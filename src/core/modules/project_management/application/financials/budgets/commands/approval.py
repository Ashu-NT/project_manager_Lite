from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Final

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.budgets.budget_events import (
    BudgetStatusChanged,
    BudgetStatusChangeType,
    BudgetVersionCreated,
)
from src.core.modules.project_management.application.financials.budgets.dto.commands.budget_lifecycle import (
    FinancialVersionedBudgetCommand,
)
from src.core.modules.project_management.application.financials.budgets.dto.responses.budget_approval import (
    BudgetApprovalOutcome,
    BudgetApprovalResult,
)
from src.core.modules.project_management.application.financials.governance.successors.dto.responses.financial_successors import (
    ApprovedFinancialLineAdjustment,
    ApprovedFinancialSuccessorResult,
)
from src.core.modules.project_management.contracts.repositories.finance.budgets.budget import (
    ProjectBudgetRepository,
)
from src.core.modules.project_management.domain.financials.budget import (
    BudgetLine,
    BudgetStatus,
    ProjectBudget,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
)
from src.core.platform.domain.approval.policy import is_governance_required
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.time.clock import CalendarClock


class _Unset(Enum):
    """Typed sentinel distinguishing "argument omitted" from an explicit None."""

    TOKEN = 0


_UNSET: Final = _Unset.TOKEN

_OPEN_VERSION_CONSTRAINT = "uq_pf_budgets_one_open_per_project"
_APPROVED_CONSTRAINT = "uq_pf_budgets_one_approved_per_project"
_REVISION_CONSTRAINT = "uq_pf_budget_project_revision"


class BudgetApprovalCommands(ProjectManagementModuleGuardMixin):
    """Approval decisions and approved financial-change participation."""

    def __init__(
        self,
        *,
        session: Session,
        budget_repo: ProjectBudgetRepository,
        clock: CalendarClock,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None = None,
        approval_commands=None,
        record_event: Callable[[object], None] | None = None,
    ) -> None:
        self._session = session
        self._budget_repo = budget_repo
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._approval_commands = approval_commands
        self._record_event = record_event


    def approve_budget(
        self, budget_id: str, *, approved_by: str, notes: str = "", expected_version: int
    ) -> BudgetApprovalResult:
        budget = self._require_budget(budget_id)
        governed = self._is_approval_governed()
        # A governed requester needs approval.request, while only a direct
        # approver needs budget.approve. Collapsing these checks would prevent
        # valid governance-only reviewers from submitting a decision request.
        if governed:
            require_permission(
                self._user_session, "approval.request", operation_label="request budget approval"
            )
            require_project_permission(
                self._user_session,
                budget.project_id,
                "approval.request",
                operation_label="request budget approval",
            )
        else:
            require_permission(
                self._user_session, "budget.approve", operation_label="approve project budget"
            )
            require_project_permission(
                self._user_session,
                budget.project_id,
                "budget.approve",
                operation_label="approve project budget",
            )
        if budget.row_version != expected_version:
            raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
        if governed:
            req = self._approval_commands.request_change(
                request_type="budget.approve",
                entity_type="project_budget",
                entity_id=budget_id,
                project_id=budget.project_id,
                payload={
                    "budget_id": budget_id,
                    "expected_version": expected_version,
                    "notes": notes,
                },
            )
            return BudgetApprovalResult(
                outcome=BudgetApprovalOutcome.PENDING_APPROVAL,
                budget_id=budget.id,
                project_id=budget.project_id,
                budget_status=budget.status,
                row_version=budget.row_version,
                approval_request_id=req.id,
            )
        approved, _events = self._apply_approval_decision(
            budget_id=budget_id,
            approved_by=approved_by,
            expected_version=expected_version,
            notes=notes,
        )
        return BudgetApprovalResult(
            outcome=BudgetApprovalOutcome.APPLIED,
            budget_id=approved.id,
            project_id=approved.project_id,
            budget_status=approved.status,
            row_version=approved.row_version,
        )


    def request_budget_approval(self, command: FinancialVersionedBudgetCommand) -> BudgetApprovalResult:
        """Create a Platform Approval request for a submitted Budget.

        This command is intentionally independent of the optional governance
        policy toggle. The desktop workflow always means "request approval";
        only a Platform Approval participant may apply its decision.
        """
        budget_id = command.budget_id
        notes = command.notes
        expected_version = command.expected_version
        if self._approval_commands is None:
            raise BusinessRuleError(
                "Platform Approval is not configured for Budget decisions.",
                code="PROJECT_BUDGET_APPROVAL_UNAVAILABLE",
            )
        require_permission(
            self._user_session,
            "approval.request",
            operation_label="request budget approval",
        )
        budget = self._require_budget(budget_id)
        require_project_permission(
            self._user_session,
            budget.project_id,
            "approval.request",
            operation_label="request budget approval",
        )
        if budget.row_version != expected_version:
            raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
        if budget.status != BudgetStatus.SUBMITTED:
            raise BusinessRuleError(
                "Only a submitted Budget can be sent for approval.",
                code="PROJECT_BUDGET_APPROVAL_STATUS_INVALID",
            )
        request = self._approval_commands.request_change(
            request_type="budget.approve",
            entity_type="project_budget",
            entity_id=budget.id,
            project_id=budget.project_id,
            payload={
                "budget_id": budget.id,
                "expected_version": expected_version,
                "notes": notes,
            },
        )
        return BudgetApprovalResult(
            outcome=BudgetApprovalOutcome.PENDING_APPROVAL,
            budget_id=budget.id,
            project_id=budget.project_id,
            budget_status=budget.status,
            row_version=budget.row_version,
            approval_request_id=request.id,
        )


    def reject_budget(
        self,
        budget_id: str,
        *,
        rejected_by: str,
        expected_version: int,
        notes: str = "",
    ) -> ProjectBudget:
        require_permission(self._user_session, "budget.approve", operation_label="reject project budget")
        budget = self._require_budget(budget_id)
        require_project_permission(
            self._user_session,
            budget.project_id,
            "budget.approve",
            operation_label="reject project budget",
        )
        rejected, _event = self._apply_rejection_decision(
            budget_id=budget_id,
            rejected_by=rejected_by,
            expected_version=expected_version,
            notes=notes,
        )
        return rejected


    def _apply_approval_decision(
        self, *, budget_id: str, approved_by: str, expected_version: int, notes: str
    ) -> tuple[ProjectBudget, tuple[object, ...]]:
        budget = self._require_budget(budget_id)
        now = self._clock.now()
        previous = self._budget_repo.get_approved_for_project(budget.project_id)
        events: list[object] = []
        try:
            with self._session.begin_nested():
                if previous is not None:
                    previous_expected_version = previous.row_version
                    previous.supersede(superseded_by=approved_by, superseded_at=now)
                    self._budget_repo.update(previous, expected_row_version=previous_expected_version)
                    self._budget_repo.flush()
                    events.append(
                        BudgetStatusChanged(
                            tenant_id=previous.tenant_id,
                            organization_id=previous.organization_id,
                            project_id=previous.project_id,
                            budget_id=previous.id,
                            change_type=BudgetStatusChangeType.SUPERSEDED,
                            occurred_at=now,
                        )
                    )
                budget_expected_version = expected_version
                budget.approve(approved_by=approved_by, approved_at=now, notes=notes)
                self._budget_repo.update(budget, expected_row_version=budget_expected_version)
                self._budget_repo.flush()
        except IntegrityError as exc:
            if self._is_approval_conflict(exc):
                raise BusinessRuleError(
                    "Another budget version was approved for this project concurrently.",
                    code="PROJECT_BUDGET_APPROVAL_CONFLICT",
                ) from exc
            raise
        self._record_budget_audit(operation="approve", budget=budget)
        events.append(
            BudgetStatusChanged(
                tenant_id=budget.tenant_id,
                organization_id=budget.organization_id,
                project_id=budget.project_id,
                budget_id=budget.id,
                change_type=BudgetStatusChangeType.APPROVED,
                occurred_at=now,
            )
        )
        event_tuple = tuple(events)
        if self._record_event is not None:
            for event in event_tuple:
                self._record_event(event)
        self._session.flush()
        return budget, event_tuple


    def _apply_approved_financial_change(
        self,
        *,
        base_budget_id: str,
        expected_base_revision: int,
        project_id: str,
        name: str,
        reason: str,
        actor_id: str,
        adjustments: tuple[ApprovedFinancialLineAdjustment, ...],
        occurred_at: datetime,
    ) -> ApprovedFinancialSuccessorResult:
        """Apply an already-approved Change through the Budget authority."""
        base = self._require_budget(base_budget_id)
        if (
            base.project_id != project_id
            or base.status is not BudgetStatus.APPROVED
            or base.revision != expected_base_revision
        ):
            raise ConcurrencyError(
                "The approved budget changed after this financial change was drafted.",
                code="FINANCIAL_CHANGE_BUDGET_BASE_STALE",
            )
        current = self._budget_repo.get_approved_for_project(project_id)
        if current is None or current.id != base.id or current.revision != base.revision:
            raise ConcurrencyError(
                "The approved budget changed after this financial change was drafted.",
                code="FINANCIAL_CHANGE_BUDGET_BASE_STALE",
            )
        if self._budget_repo.has_open_for_project(project_id):
            raise BusinessRuleError(
                "An open budget version must be resolved before applying a financial change.",
                code="FINANCIAL_CHANGE_OPEN_BUDGET_EXISTS",
            )
        by_target = {row.target_line_id: row for row in adjustments if row.target_line_id}
        latest = self._budget_repo.get_latest_for_project(project_id)
        successor = ProjectBudget.create(
            tenant_id=base.tenant_id,
            organization_id=base.organization_id,
            project_id=project_id,
            predecessor_budget_id=base.id,
            name=name,
            currency_code=base.currency_code,
            revision=(latest.revision + 1) if latest else 1,
            created_at=occurred_at,
        )
        successor.update_notes(reason)
        successor.submit(submitted_by=actor_id, submitted_at=occurred_at, notes=reason)
        successor.approve(approved_by=actor_id, approved_at=occurred_at, notes=reason)
        base_version = base.row_version
        base.supersede(superseded_by=actor_id, superseded_at=occurred_at)
        self._budget_repo.update(base, expected_row_version=base_version)
        self._budget_repo.flush()
        self._budget_repo.add(successor)
        self._budget_repo.flush()
        references: list[tuple[str, str]] = []
        for source in self._budget_repo.list_lines(base.id):
            adjustment = by_target.get(source.id)
            amount = source.amount + (adjustment.amount if adjustment else Decimal(0))
            if amount < 0:
                raise BusinessRuleError(
                    "Budget change would make a successor line negative.",
                    code="FINANCIAL_CHANGE_BUDGET_NEGATIVE_RESULT",
                )
            line = BudgetLine.create(
                tenant_id=base.tenant_id,
                organization_id=base.organization_id,
                budget_id=successor.id,
                project_id=project_id,
                cost_code_id=source.cost_code_id,
                task_id=source.task_id,
                description=adjustment.description if adjustment else source.description,
                amount=amount,
                currency_code=base.currency_code,
                created_at=occurred_at,
            )
            self._budget_repo.add_line(line)
            if adjustment:
                references.append((adjustment.impact_id, line.id))
        for adjustment in adjustments:
            if adjustment.target_line_id:
                continue
            line = BudgetLine.create(
                tenant_id=base.tenant_id,
                organization_id=base.organization_id,
                budget_id=successor.id,
                project_id=project_id,
                cost_code_id=adjustment.cost_code_id,
                task_id=adjustment.task_id,
                description=adjustment.description,
                amount=adjustment.amount,
                currency_code=base.currency_code,
                created_at=occurred_at,
            )
            self._budget_repo.add_line(line)
            references.append((adjustment.impact_id, line.id))
        self._budget_repo.flush()
        self._record_budget_audit(operation="apply_financial_change", budget=successor)
        events: tuple[object, ...] = (
            BudgetVersionCreated(
                tenant_id=successor.tenant_id,
                organization_id=successor.organization_id,
                project_id=successor.project_id,
                budget_id=successor.id,
                status=successor.status,
                predecessor_budget_id=successor.predecessor_budget_id,
                occurred_at=occurred_at,
            ),
            BudgetStatusChanged(
                tenant_id=base.tenant_id,
                organization_id=base.organization_id,
                project_id=base.project_id,
                budget_id=base.id,
                change_type=BudgetStatusChangeType.SUPERSEDED,
                occurred_at=occurred_at,
            ),
        )
        if self._record_event is not None:
            for event in events:
                self._record_event(event)
        return ApprovedFinancialSuccessorResult(
            version_id=successor.id, line_references=tuple(references), domain_events=events
        )


    def _apply_rejection_decision(
        self, *, budget_id: str, rejected_by: str, expected_version: int, notes: str
    ) -> tuple[ProjectBudget, object]:
        budget = self._require_budget(budget_id)
        if budget.row_version != expected_version:
            raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
        now = self._clock.now()
        budget.reject(rejected_by=rejected_by, rejected_at=now, notes=notes)
        self._budget_repo.update(budget, expected_row_version=expected_version)
        self._record_budget_audit(operation="reject", budget=budget)
        event = BudgetStatusChanged(
            tenant_id=budget.tenant_id,
            organization_id=budget.organization_id,
            project_id=budget.project_id,
            budget_id=budget.id,
            change_type=BudgetStatusChangeType.REJECTED,
            occurred_at=now,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return budget, event


    def _is_approval_governed(self) -> bool:
        return self._approval_commands is not None and is_governance_required("budget.approve")


    @staticmethod
    def _integrity_message(exc: IntegrityError) -> str:
        # Deliberately NOT `str(exc)`/`.statement` — both embed the full
        # failing SQL statement, whose column list always contains the
        # literal word "revision" for this table regardless of which
        # constraint actually failed, which would make every conflict here
        # misidentify as a revision conflict. `.orig` (the raw DBAPI
        # exception) carries only the constraint/column text that actually
        # violated — precise on both SQLite (columns) and PostgreSQL
        # (named constraint).
        orig_message = str(getattr(exc, "orig", "") or "")
        return (orig_message or str(exc)).lower()


    @classmethod
    def _is_approval_conflict(cls, exc: IntegrityError) -> bool:
        message = cls._integrity_message(exc)
        # Reachable only from _apply_approval_decision, which never inserts
        # a new open (draft/submitted) row — any unique violation on this
        # table reached from here is necessarily the one-approved-per-
        # project index, so a bare table-name match is unambiguous (SQLite
        # never surfaces the partial index's name in its error text).
        return _APPROVED_CONSTRAINT in message or "project_finance_budgets" in message


    def _require_budget(self, budget_id: str) -> ProjectBudget:
        budget = self._budget_repo.get(budget_id)
        if budget is None:
            raise NotFoundError("Project budget not found.", code="PROJECT_BUDGET_NOT_FOUND")
        return budget


    def _record_budget_audit(self, *, operation: str, budget: ProjectBudget) -> None:
        full_operation = f"project_budget.{operation}"
        record_audit_entry(
            self,
            operation=full_operation,
            entity_type="project_budget",
            entity_id=budget.id,
            entity_parent_id=budget.project_id,
            module="project_management",
            category="FINANCIAL",
            after_data=self._budget_audit_value(budget),
            workspace_id=budget.project_id,
            source="application",
            severity="high",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )
        record_activity(
            self,
            action=full_operation,
            entity_type="project_budget",
            entity_id=budget.id,
            parent_entity_id=budget.project_id,
            module="project_management",
            workspace_id=budget.project_id,
            details={"action": operation},
            commit=False,
        )


    @staticmethod
    def _budget_audit_value(budget: ProjectBudget) -> dict[str, Any]:
        return {
            "name": budget.name,
            "status": budget.status.value,
            "revision": budget.revision,
            "currency_code": budget.currency_code,
            "row_version": budget.row_version,
        }



__all__ = ["BudgetApprovalCommands"]
