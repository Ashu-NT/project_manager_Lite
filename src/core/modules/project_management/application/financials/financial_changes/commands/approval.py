from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.financials.financial_changes.policy import (
    ApprovedBudgetChangeAuthority,
    ApprovedForecastChangeAuthority,
    FinancialChangeAuditPolicy,
    FinancialChangeValidationPolicy,
)
from src.core.modules.project_management.application.financials.shared.successor_models import (
    ApprovedFinancialLineAdjustment,
)
from src.core.modules.project_management.contracts.ports.scheduling.schedule_change import (
    ApprovedScheduleChangePort,
)
from src.core.modules.project_management.contracts.repositories.finance.budgets.budget import (
    ProjectBudgetRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.financial_changes.financial_change import (
    FinancialChangeRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.forecasts.forecast import (
    ProjectForecastRepository,
)
from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpact,
    FinancialChangeImpactType,
    FinancialChangeRequest,
    FinancialChangeStatus,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
)
from src.core.shared.time.clock import CalendarClock


class FinancialChangeApprovalCommandHandler(
    FinancialChangeValidationPolicy, FinancialChangeAuditPolicy
):
    """Internal approval participant commands on the deciding caller's session.

    Successor authorities and the scheduling port must join that same transaction.
    The approval participant, not this handler, publishes the returned events.
    """

    def __init__(
        self,
        *,
        session: Session,
        change_repo: FinancialChangeRepository,
        budget_repo: ProjectBudgetRepository,
        forecast_repo: ProjectForecastRepository,
        task_service: ApprovedScheduleChangePort,
        clock: CalendarClock,
        budget_authority: ApprovedBudgetChangeAuthority | None = None,
        forecast_authority: ApprovedForecastChangeAuthority | None = None,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
    ) -> None:
        self._session = session
        self._change_repo = change_repo
        self._budget_repo = budget_repo
        self._forecast_repo = forecast_repo
        self._task_service = task_service
        self._clock = clock
        self._budget_authority = budget_authority
        self._forecast_authority = forecast_authority
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service

    def _apply_approval_decision(
        self,
        *,
        change_id: str,
        approval_request_id: str,
        applied_by: str,
    ) -> tuple[FinancialChangeRequest, tuple[object, ...]]:
        change = self._require_change(change_id)
        if (
            change.status is not FinancialChangeStatus.PENDING_APPROVAL
            or change.approval_request_id != approval_request_id
        ):
            raise BusinessRuleError(
                "Financial change approval request does not match the pending change.",
                code="FINANCIAL_CHANGE_APPROVAL_MISMATCH",
            )
        impacts = self._change_repo.list_impacts(change.id)
        self._validate_application_bases(change, impacts)
        now = self._clock.now()
        expected_version = change.row_version
        budget_id, budget_events = self._apply_budget_successor(
            change, impacts, applied_by, now
        )
        forecast_id = self._apply_forecast_successor(change, impacts, applied_by, now)
        schedule_count, schedule_events = self._apply_schedule_changes(
            change, impacts, applied_by
        )
        change.apply(
            applied_by=applied_by,
            applied_at=now,
            applied_budget_id=budget_id,
            applied_forecast_id=forecast_id,
            applied_schedule_count=schedule_count,
        )
        self._change_repo.update(change, expected_row_version=expected_version)
        self._audit_change("apply", change)
        self._session.flush()
        return change, budget_events + schedule_events

    def _apply_rejection_decision(
        self,
        *,
        change_id: str,
        approval_request_id: str,
        rejected_by: str,
        notes: str,
    ) -> FinancialChangeRequest:
        change = self._require_change(change_id)
        if change.approval_request_id != approval_request_id:
            raise BusinessRuleError(
                "Financial change approval request does not match the pending change.",
                code="FINANCIAL_CHANGE_APPROVAL_MISMATCH",
            )
        expected_version = change.row_version
        change.reject(
            rejected_by=rejected_by,
            rejected_at=self._clock.now(),
            notes=notes,
        )
        self._change_repo.update(change, expected_row_version=expected_version)
        self._audit_change("reject", change)
        self._session.flush()
        return change

    def _apply_budget_successor(
        self,
        change: FinancialChangeRequest,
        impacts: list[FinancialChangeImpact],
        actor: str,
        now: datetime,
    ) -> tuple[str | None, tuple[object, ...]]:
        relevant = [
            row
            for row in impacts
            if row.impact_type is FinancialChangeImpactType.BUDGET
        ]
        if not relevant:
            return None, ()
        if self._budget_authority is None:
            raise BusinessRuleError(
                "Budget authority is unavailable for financial change application.",
                code="FINANCIAL_CHANGE_BUDGET_AUTHORITY_REQUIRED",
            )
        result = self._budget_authority._apply_approved_financial_change(
            base_budget_id=change.base_budget_id or "",
            expected_base_revision=change.base_budget_revision or 0,
            project_id=change.project_id,
            name=f"Change {change.revision}: {change.title}",
            reason=f"Applied financial change {change.id}: {change.reason}",
            actor_id=actor,
            adjustments=tuple(self._line_adjustment(row) for row in relevant),
            occurred_at=now,
        )
        for impact_id, line_id in result.line_references:
            self._change_repo.update_impact_application(
                impact_id,
                applied_reference_type="budget_line",
                applied_reference_id=line_id,
            )
        self._audit_version("project_budget", result.version_id, change, now)
        return result.version_id, result.domain_events

    def _apply_forecast_successor(
        self,
        change: FinancialChangeRequest,
        impacts: list[FinancialChangeImpact],
        actor: str,
        now: datetime,
    ) -> str | None:
        relevant = [
            row
            for row in impacts
            if row.impact_type is FinancialChangeImpactType.FORECAST
        ]
        if not relevant:
            return None
        if self._forecast_authority is None:
            raise BusinessRuleError(
                "Forecast authority is unavailable for financial change application.",
                code="FINANCIAL_CHANGE_FORECAST_AUTHORITY_REQUIRED",
            )
        result = self._forecast_authority._apply_approved_financial_change(
            base_forecast_id=change.base_forecast_id or "",
            expected_base_revision=change.base_forecast_revision or 0,
            project_id=change.project_id,
            name=f"Change {change.revision}: {change.title}",
            reason=f"Applied financial change {change.id}: {change.reason}",
            actor_id=actor,
            as_of_date=change.effective_date,
            adjustments=tuple(self._line_adjustment(row) for row in relevant),
            occurred_at=now,
        )
        for impact_id, line_id in result.line_references:
            self._change_repo.update_impact_application(
                impact_id,
                applied_reference_type="forecast_line",
                applied_reference_id=line_id,
            )
        self._audit_version("project_forecast", result.version_id, change, now)
        return result.version_id

    def _apply_schedule_changes(
        self,
        change: FinancialChangeRequest,
        impacts: list[FinancialChangeImpact],
        actor: str,
    ) -> tuple[int, tuple[object, ...]]:
        relevant = [
            row
            for row in impacts
            if row.impact_type is FinancialChangeImpactType.SCHEDULE
        ]
        if not relevant:
            return 0, ()
        commands = self._schedule_commands(change, relevant)
        applied = self._task_service._apply_approved_schedule_changes(
            commands, actor_id=actor
        )
        task_events = self._task_service._take_pending_task_events()
        occurred_at = self._clock.now()
        for result in applied:
            self._change_repo.update_impact_application(
                result.reference_id,
                applied_reference_type="task",
                applied_reference_id=result.task_id,
            )
            self._audit_version("task", result.task_id, change, occurred_at)
        return len(applied), task_events

    @staticmethod
    def _line_adjustment(
        impact: FinancialChangeImpact,
    ) -> ApprovedFinancialLineAdjustment:
        return ApprovedFinancialLineAdjustment(
            impact_id=impact.id,
            description=impact.description,
            amount=impact.amount,
            cost_code_id=impact.cost_code_id or "",
            task_id=impact.task_id,
            target_line_id=impact.target_line_id,
        )


__all__ = ["FinancialChangeApprovalCommandHandler"]
