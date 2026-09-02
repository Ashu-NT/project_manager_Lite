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
from src.core.modules.project_management.application.financials.budgets.budget_service import (
    BudgetService,
)
from src.core.modules.project_management.application.financials.forecasts.version_service import (
    ForecastVersionService,
)
from src.core.modules.project_management.application.financials.financial_changes.financial_change_events import (
    FinancialChangeChanged,
    FinancialChangeEventType,
)
from src.core.modules.project_management.application.financials.successor_models import (
    ApprovedFinancialLineAdjustment,
)
from src.core.modules.project_management.contracts.ports.schedule_change import (
    ApprovedScheduleChangePort,
    ApprovedTaskScheduleChange,
)
from src.core.modules.project_management.contracts.repositories.finance.budgets.budget import (
    ProjectBudgetRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.financial_changes.financial_change import (
    FinancialChangeRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectCostCodeRepository,
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.forecasts.forecast import (
    ProjectForecastRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.tasks.task import TaskRepository
from src.core.modules.project_management.domain.financials.budget import ProjectBudget
from src.core.modules.project_management.domain.financials.configuration import CostCodePolicy
from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpact,
    FinancialChangeImpactType,
    FinancialChangeRequest,
    FinancialChangeStatus,
)
from src.core.modules.project_management.domain.financials.forecast import ProjectForecast
from src.core.platform.application.approval.approval_mutation_participant import (
    request_approval_using,
)
from src.core.platform.application.approval.approval_service import ApprovalService
from src.core.platform.contract.repositories.approval.contracts import ApprovalRepository
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
)
from src.core.shared.audit import record_audit_entry


_REVISION_CONSTRAINT = "uq_pf_change_project_revision"


class FinancialChangeService(ProjectManagementModuleGuardMixin):
    """Governed financial change orders with atomic canonical version application."""

    def __init__(
        self,
        *,
        session: Session,
        change_repo: FinancialChangeRepository,
        budget_repo: ProjectBudgetRepository,
        forecast_repo: ProjectForecastRepository,
        project_repo: ProjectRepository,
        financial_profile_repo: ProjectFinancialProfileRepository,
        cost_code_repo: ProjectCostCodeRepository,
        task_repo: TaskRepository,
        task_service: ApprovedScheduleChangePort,
        budget_authority: BudgetService | None = None,
        forecast_authority: ForecastVersionService | None = None,
        approval_service: ApprovalService | None,
        clock: Clock,
        approval_repo: ApprovalRepository | None = None,
        record_event: Callable[[object], None] | None = None,
        approval_requested_staged: Callable[[object], None] | None = None,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None = None,
    ) -> None:
        self._session = session
        self._change_repo = change_repo
        self._budget_repo = budget_repo
        self._forecast_repo = forecast_repo
        self._project_repo = project_repo
        self._financial_profile_repo = financial_profile_repo
        self._cost_code_repo = cost_code_repo
        self._task_repo = task_repo
        self._task_service = task_service
        self._budget_authority = budget_authority
        self._forecast_authority = forecast_authority
        self._approval_service = approval_service
        self._clock = clock
        self._approval_repo = approval_repo
        self._record_event = record_event
        self._approval_requested_staged = approval_requested_staged
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service

    def get_change(self, change_id: str) -> FinancialChangeRequest:
        require_permission(
            self._user_session, "finance.read", operation_label="view financial change"
        )
        change = self._require_change(change_id)
        require_project_permission(
            self._user_session,
            change.project_id,
            "finance.read",
            operation_label="view financial change",
        )
        return change

    def list_changes(self, project_id: str) -> list[FinancialChangeRequest]:
        self._require_project_permission(project_id, "finance.read", "list financial changes")
        return self._change_repo.list_for_project(project_id)

    def list_impacts(self, change_id: str) -> list[FinancialChangeImpact]:
        change = self.get_change(change_id)
        return self._change_repo.list_impacts(change.id)

    def create_change(
        self,
        project_id: str,
        *,
        title: str,
        reason: str,
        effective_date: date,
        created_by: str,
        description: str = "",
    ) -> FinancialChangeRequest:
        self._require_project_permission(
            project_id, "financial_change.manage", "create financial change"
        )
        if self._project_repo.get(project_id) is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        profile = self._financial_profile_repo.get_by_project(project_id)
        if profile is None:
            raise NotFoundError(
                "Project financial profile not found; configure finance before change control.",
                code="PROJECT_FINANCIAL_PROFILE_NOT_FOUND",
            )
        context = self._require_context("create financial change")
        latest = self._change_repo.get_latest_for_project(project_id)
        base_budget = self._budget_repo.get_approved_for_project(project_id)
        base_forecast = self._forecast_repo.get_approved_for_project(project_id)
        now = self._clock.now()
        change = FinancialChangeRequest.create(
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            project_id=project_id,
            title=title,
            reason=reason,
            description=description,
            effective_date=effective_date,
            currency_code=profile.currency_code,
            created_by=created_by,
            revision=(latest.revision + 1) if latest else 1,
            base_budget_id=base_budget.id if base_budget else None,
            base_budget_revision=base_budget.revision if base_budget else None,
            base_forecast_id=base_forecast.id if base_forecast else None,
            base_forecast_revision=base_forecast.revision if base_forecast else None,
            created_at=now,
        )
        try:
            self._change_repo.add(change)
            self._change_repo.flush()
            self._audit_change("create", change)
            self._session.flush()
        except IntegrityError as exc:
            if _REVISION_CONSTRAINT in str(getattr(exc, "orig", "")).lower():
                raise ConcurrencyError(
                    "Another financial change revision was created concurrently.",
                    code="FINANCIAL_CHANGE_REVISION_CONFLICT",
                ) from exc
            raise
        self._emit_change_event(change, FinancialChangeEventType.CREATED)
        return change

    def update_change(
        self,
        change_id: str,
        *,
        title: str,
        reason: str,
        description: str,
        effective_date: date,
        expected_version: int,
    ) -> FinancialChangeRequest:
        change = self._require_mutable_change(
            change_id, expected_version, "update financial change"
        )
        now = self._clock.now()
        change.update_draft(
            title=title,
            reason=reason,
            description=description,
            effective_date=effective_date,
            updated_at=now,
        )
        for impact in self._change_repo.list_impacts(change.id):
            if impact.cost_code_id:
                self._require_cost_code(change.project_id, impact.cost_code_id, effective_date)
        self._change_repo.update(change, expected_row_version=expected_version)
        self._audit_change("update", change)
        self._session.flush()
        self._emit_change_event(change, FinancialChangeEventType.UPDATED)
        return change

    def add_impact(
        self,
        change_id: str,
        *,
        impact_type: FinancialChangeImpactType,
        description: str,
        expected_change_version: int,
        amount: Decimal = Decimal("0"),
        currency_code: str | None = None,
        cost_code_id: str | None = None,
        task_id: str | None = None,
        target_line_id: str | None = None,
        schedule_start: date | None = None,
        schedule_finish: date | None = None,
    ) -> FinancialChangeImpact:
        change = self._require_mutable_change(
            change_id, expected_change_version, "add financial change impact"
        )
        resolved_currency = currency_code or (change.currency_code if amount != 0 else None)
        if resolved_currency and resolved_currency != change.currency_code:
            raise BusinessRuleError(
                "Financial change impact currency must match the project finance currency.",
                code="FINANCIAL_CHANGE_CURRENCY_MISMATCH",
            )
        if cost_code_id:
            self._require_cost_code(change.project_id, cost_code_id, change.effective_date)
        task = self._require_task(change.project_id, task_id) if task_id else None
        impact = FinancialChangeImpact.create(
            tenant_id=change.tenant_id,
            organization_id=change.organization_id,
            change_request_id=change.id,
            project_id=change.project_id,
            impact_type=impact_type,
            description=description,
            amount=amount,
            currency_code=resolved_currency,
            cost_code_id=cost_code_id,
            task_id=task_id,
            target_line_id=target_line_id,
            target_task_version=(
                task.version
                if task is not None
                and impact_type is FinancialChangeImpactType.SCHEDULE
                else None
            ),
            schedule_start=schedule_start,
            schedule_finish=schedule_finish,
            created_at=self._clock.now(),
        )
        self._validate_target(change, impact)
        if impact.impact_type is FinancialChangeImpactType.SCHEDULE:
            self._task_service._validate_approved_schedule_changes(
                self._schedule_commands(change, [impact])
            )
        existing = self._change_repo.list_impacts(change.id)
        if impact.target_line_id and any(
            row.impact_type is impact.impact_type
            and row.target_line_id == impact.target_line_id
            for row in existing
        ):
            raise BusinessRuleError(
                "Only one impact may target a canonical line in one change request.",
                code="FINANCIAL_CHANGE_DUPLICATE_TARGET",
            )
        if impact.impact_type is FinancialChangeImpactType.SCHEDULE and any(
            row.impact_type is FinancialChangeImpactType.SCHEDULE
            and row.task_id == impact.task_id
            for row in existing
        ):
            raise BusinessRuleError(
                "A financial change may adjust each task schedule only once.",
                code="FINANCIAL_CHANGE_DUPLICATE_SCHEDULE_TARGET",
            )
        now = self._clock.now()
        self._change_repo.add_impact(impact)
        change.touch(updated_at=now)
        self._change_repo.update(change, expected_row_version=expected_change_version)
        self._audit_impact("add", change, impact)
        self._session.flush()
        self._emit_change_event(
            change, FinancialChangeEventType.IMPACT_ADDED, impact_id=impact.id
        )
        return impact

    def update_impact(
        self,
        impact_id: str,
        *,
        impact_type: FinancialChangeImpactType,
        description: str,
        expected_impact_version: int,
        expected_change_version: int,
        amount: Decimal = Decimal("0"),
        currency_code: str | None = None,
        cost_code_id: str | None = None,
        task_id: str | None = None,
        target_line_id: str | None = None,
        schedule_start: date | None = None,
        schedule_finish: date | None = None,
    ) -> FinancialChangeImpact:
        impact = self._require_impact(impact_id)
        if impact.impact_type is not impact_type:
            raise BusinessRuleError(
                "Financial change impact type is immutable.",
                code="FINANCIAL_CHANGE_IMPACT_TYPE_IMMUTABLE",
            )
        change = self._require_mutable_change(
            impact.change_request_id,
            expected_change_version,
            "update financial change impact",
        )
        if impact.row_version != expected_impact_version:
            raise ConcurrencyError(
                "Financial change impact was updated since you opened it.", code="STALE_WRITE"
            )
        resolved_currency = currency_code or (change.currency_code if amount != 0 else None)
        if resolved_currency and resolved_currency != change.currency_code:
            raise BusinessRuleError(
                "Financial change impact currency must match the project finance currency.",
                code="FINANCIAL_CHANGE_CURRENCY_MISMATCH",
            )
        if cost_code_id:
            self._require_cost_code(change.project_id, cost_code_id, change.effective_date)
        task = self._require_task(change.project_id, task_id) if task_id else None
        now = self._clock.now()
        impact.update_draft(
            description=description,
            amount=amount,
            currency_code=resolved_currency,
            cost_code_id=cost_code_id,
            task_id=task_id,
            target_line_id=target_line_id,
            target_task_version=(
                task.version
                if task is not None
                and impact.impact_type is FinancialChangeImpactType.SCHEDULE
                else None
            ),
            schedule_start=schedule_start,
            schedule_finish=schedule_finish,
            updated_at=now,
        )
        self._validate_target(change, impact)
        if impact.impact_type is FinancialChangeImpactType.SCHEDULE:
            self._task_service._validate_approved_schedule_changes(
                self._schedule_commands(change, [impact])
            )
        for row in self._change_repo.list_impacts(change.id):
            if row.id == impact.id:
                continue
            if (
                impact.target_line_id
                and row.impact_type is impact.impact_type
                and row.target_line_id == impact.target_line_id
            ):
                raise BusinessRuleError(
                    "Only one impact may target a canonical line in one change request.",
                    code="FINANCIAL_CHANGE_DUPLICATE_TARGET",
                )
            if (
                impact.impact_type is FinancialChangeImpactType.SCHEDULE
                and row.impact_type is FinancialChangeImpactType.SCHEDULE
                and row.task_id == impact.task_id
            ):
                raise BusinessRuleError(
                    "A financial change may adjust each task schedule only once.",
                    code="FINANCIAL_CHANGE_DUPLICATE_SCHEDULE_TARGET",
                )
        self._change_repo.update_impact(
            impact, expected_row_version=expected_impact_version
        )
        change.touch(updated_at=now)
        self._change_repo.update(change, expected_row_version=expected_change_version)
        self._audit_impact("update", change, impact)
        self._session.flush()
        self._emit_change_event(
            change, FinancialChangeEventType.IMPACT_UPDATED, impact_id=impact.id
        )
        return impact

    def remove_impact(
        self,
        impact_id: str,
        *,
        expected_impact_version: int,
        expected_change_version: int,
    ) -> FinancialChangeRequest:
        impact = self._require_impact(impact_id)
        change = self._require_mutable_change(
            impact.change_request_id,
            expected_change_version,
            "remove financial change impact",
        )
        if impact.applied_reference_id:
            raise BusinessRuleError(
                "Applied financial change impacts cannot be removed.",
                code="FINANCIAL_CHANGE_IMPACT_APPLIED",
            )
        self._audit_impact("remove", change, impact)
        self._change_repo.delete_impact(
            impact.id, expected_row_version=expected_impact_version
        )
        change.touch(updated_at=self._clock.now())
        self._change_repo.update(change, expected_row_version=expected_change_version)
        self._session.flush()
        self._emit_change_event(
            change, FinancialChangeEventType.IMPACT_REMOVED, impact_id=impact.id
        )
        return change

    def submit_change(
        self,
        change_id: str,
        *,
        submitted_by: str,
        expected_version: int,
    ) -> FinancialChangeRequest:

        if self._approval_repo is None or self._record_event is None:
            raise BusinessRuleError(
                "Financial change submission requires the Finance governance command boundary.",
                code="FINANCIAL_CHANGE_COMMAND_BOUNDARY_REQUIRED",
            )
        change = self._require_change(change_id)
        self._require_project_permission(
            change.project_id, "financial_change.manage", "submit financial change"
        )
        change.ensure_draft()
        if change.row_version != expected_version:
            raise ConcurrencyError(
                "Financial change was updated since you opened it.", code="STALE_WRITE"
            )
        require_permission(
            self._user_session,
            "approval.request",
            operation_label="submit financial change for approval",
        )
        require_project_permission(
            self._user_session,
            change.project_id,
            "approval.request",
            operation_label="submit financial change for approval",
        )
        impacts = self._change_repo.list_impacts(change.id)
        if not impacts:
            raise BusinessRuleError(
                "Cannot submit a financial change without impacts.",
                code="FINANCIAL_CHANGE_EMPTY",
            )
        types = {row.impact_type for row in impacts}
        if FinancialChangeImpactType.BUDGET in types:
            current_budget = self._budget_repo.get_approved_for_project(change.project_id)
            if (
                current_budget is None
                or current_budget.id != change.base_budget_id
                or current_budget.revision != change.base_budget_revision
            ):
                raise ConcurrencyError(
                    "The approved budget changed after this financial change was drafted.",
                    code="FINANCIAL_CHANGE_BUDGET_BASE_STALE",
                )
            if self._budget_repo.has_open_for_project(change.project_id):
                raise BusinessRuleError(
                    "An open budget version must be resolved before applying a financial change.",
                    code="FINANCIAL_CHANGE_OPEN_BUDGET_EXISTS",
                )
        if FinancialChangeImpactType.FORECAST in types:
            current_forecast = self._forecast_repo.get_approved_for_project(change.project_id)
            if (
                current_forecast is None
                or current_forecast.id != change.base_forecast_id
                or current_forecast.revision != change.base_forecast_revision
            ):
                raise ConcurrencyError(
                    "The approved forecast changed after this financial change was drafted.",
                    code="FINANCIAL_CHANGE_FORECAST_BASE_STALE",
                )
            if self._forecast_repo.has_open_for_project(change.project_id):
                raise BusinessRuleError(
                    "An open forecast version must be resolved before applying a financial change.",
                    code="FINANCIAL_CHANGE_OPEN_FORECAST_EXISTS",
                )
        self._task_service._validate_approved_schedule_changes(
            self._schedule_commands(change, impacts)
        )
        scope = self._require_context("submit financial change for approval")
        principal = self._user_session.principal if self._user_session else None
        approval = request_approval_using(
            approval_repo=self._approval_repo,
            enterprise_audit_service=self._enterprise_audit_service,
            clock=self._clock,
            record_event=self._record_event,
            request_type="financial_change.apply",
            entity_type="financial_change_request",
            entity_id=change.id,
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=change.project_id,
            payload={"change_id": change.id},
            requested_by_user_id=principal.user_id if principal else None,
            requested_by_username=principal.username if principal else None,
        )
        change.submit(
            approval_request_id=approval.id,
            submitted_by=submitted_by,
            submitted_at=self._clock.now(),
        )
        self._change_repo.update(change, expected_row_version=expected_version)
        self._audit_change("submit", change)
        self._session.flush()
        if self._approval_requested_staged is not None:
            self._approval_requested_staged(approval)
        self._emit_change_event(change, FinancialChangeEventType.SUBMITTED)
        return change

    def _apply_approval_decision(
        self,
        *,
        change_id: str,
        approval_request_id: str,
        applied_by: str,
    ) -> FinancialChangeRequest:
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
        budget_id = self._apply_budget_successor(change, impacts, applied_by, now)
        forecast_id = self._apply_forecast_successor(change, impacts, applied_by, now)
        schedule_count = self._apply_schedule_changes(change, impacts, applied_by)
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
        return change

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
    ) -> str | None:
        relevant = [
            row for row in impacts if row.impact_type is FinancialChangeImpactType.BUDGET
        ]
        if not relevant:
            return None
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
        return result.version_id

    def _apply_forecast_successor(
        self,
        change: FinancialChangeRequest,
        impacts: list[FinancialChangeImpact],
        actor: str,
        now: datetime,
    ) -> str | None:
        relevant = [
            row for row in impacts if row.impact_type is FinancialChangeImpactType.FORECAST
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
    ) -> int:
        relevant = [
            row for row in impacts if row.impact_type is FinancialChangeImpactType.SCHEDULE
        ]
        if not relevant:
            return 0
        commands = self._schedule_commands(change, relevant)
        applied = self._task_service._apply_approved_schedule_changes(
            commands, actor_id=actor, commit=False
        )
        occurred_at = self._clock.now()
        for result in applied:
            self._change_repo.update_impact_application(
                result.reference_id,
                applied_reference_type="task",
                applied_reference_id=result.task_id,
            )
            self._audit_version("task", result.task_id, change, occurred_at)
        return len(applied)

    @staticmethod
    def _schedule_commands(
        change: FinancialChangeRequest,
        impacts: list[FinancialChangeImpact],
    ) -> list[ApprovedTaskScheduleChange]:
        return [
            ApprovedTaskScheduleChange(
                reference_id=impact.id,
                project_id=change.project_id,
                task_id=impact.task_id or "",
                expected_version=impact.target_task_version or 0,
                start_date=impact.schedule_start,
                finish_date=impact.schedule_finish,
            )
            for impact in impacts
            if impact.impact_type is FinancialChangeImpactType.SCHEDULE
        ]

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

    def _validate_target(
        self, change: FinancialChangeRequest, impact: FinancialChangeImpact
    ) -> None:
        if not impact.target_line_id:
            return
        if impact.impact_type is FinancialChangeImpactType.BUDGET:
            line = self._budget_repo.get_line(impact.target_line_id)
            if line is None or line.budget_id != change.base_budget_id:
                raise NotFoundError(
                    "Target approved budget line not found.",
                    code="FINANCIAL_CHANGE_BUDGET_TARGET_NOT_FOUND",
                )
        elif impact.impact_type is FinancialChangeImpactType.FORECAST:
            line = self._forecast_repo.get_line(impact.target_line_id)
            if line is None or line.forecast_id != change.base_forecast_id:
                raise NotFoundError(
                    "Target approved forecast line not found.",
                    code="FINANCIAL_CHANGE_FORECAST_TARGET_NOT_FOUND",
                )
        else:
            raise BusinessRuleError(
                "Only budget and forecast impacts may target canonical financial lines.",
                code="FINANCIAL_CHANGE_TARGET_TYPE_INVALID",
            )
        if line.project_id != change.project_id:
            raise BusinessRuleError(
                "Target line does not belong to the financial change project.",
                code="FINANCIAL_CHANGE_TARGET_PROJECT_MISMATCH",
            )
        if line.cost_code_id != impact.cost_code_id or line.task_id != impact.task_id:
            raise BusinessRuleError(
                "Impact dimensions must match the target canonical line.",
                code="FINANCIAL_CHANGE_TARGET_DIMENSION_MISMATCH",
            )

    def _validate_application_bases(
        self,
        change: FinancialChangeRequest,
        impacts: list[FinancialChangeImpact],
    ) -> None:
        types = {row.impact_type for row in impacts}
        if FinancialChangeImpactType.BUDGET in types:
            self._require_base_budget(change)
            if self._budget_repo.has_open_for_project(change.project_id):
                raise BusinessRuleError(
                    "An open budget version must be resolved before applying a financial change.",
                    code="FINANCIAL_CHANGE_OPEN_BUDGET_EXISTS",
                )
        if FinancialChangeImpactType.FORECAST in types:
            self._require_base_forecast(change)
            if self._forecast_repo.has_open_for_project(change.project_id):
                raise BusinessRuleError(
                    "An open forecast version must be resolved before applying a financial change.",
                    code="FINANCIAL_CHANGE_OPEN_FORECAST_EXISTS",
                )
        schedule_commands = self._schedule_commands(change, impacts)
        self._task_service._validate_approved_schedule_changes(schedule_commands)

    def _require_base_budget(self, change: FinancialChangeRequest) -> ProjectBudget:
        current = self._budget_repo.get_approved_for_project(change.project_id)
        if (
            current is None
            or current.id != change.base_budget_id
            or current.revision != change.base_budget_revision
        ):
            raise ConcurrencyError(
                "The approved budget changed after this financial change was drafted.",
                code="FINANCIAL_CHANGE_BUDGET_BASE_STALE",
            )
        return current

    def _require_base_forecast(self, change: FinancialChangeRequest) -> ProjectForecast:
        current = self._forecast_repo.get_approved_for_project(change.project_id)
        if (
            current is None
            or current.id != change.base_forecast_id
            or current.revision != change.base_forecast_revision
        ):
            raise ConcurrencyError(
                "The approved forecast changed after this financial change was drafted.",
                code="FINANCIAL_CHANGE_FORECAST_BASE_STALE",
            )
        return current

    def _require_mutable_change(
        self, change_id: str, expected_version: int, operation: str
    ) -> FinancialChangeRequest:
        change = self._require_change(change_id)
        self._require_project_permission(
            change.project_id, "financial_change.manage", operation
        )
        change.ensure_draft()
        if change.row_version != expected_version:
            raise ConcurrencyError(
                "Financial change was updated since you opened it.", code="STALE_WRITE"
            )
        return change

    def _require_change(self, change_id: str) -> FinancialChangeRequest:
        change = self._change_repo.get(change_id)
        if change is None:
            raise NotFoundError(
                "Financial change not found.", code="FINANCIAL_CHANGE_NOT_FOUND"
            )
        return change

    def _require_impact(self, impact_id: str) -> FinancialChangeImpact:
        impact = self._change_repo.get_impact(impact_id)
        if impact is None:
            raise NotFoundError(
                "Financial change impact not found.",
                code="FINANCIAL_CHANGE_IMPACT_NOT_FOUND",
            )
        return impact

    def _emit_change_event(
        self,
        change: FinancialChangeRequest,
        change_type: FinancialChangeEventType,
        *,
        impact_id: str | None = None,
    ) -> None:
        if self._record_event is None:
            return
        self._record_event(
            FinancialChangeChanged(
                tenant_id=change.tenant_id,
                organization_id=change.organization_id,
                project_id=change.project_id,
                change_id=change.id,
                change_type=change_type,
                impact_id=impact_id,
                occurred_at=change.updated_at,
            )
        )

    def _require_cost_code(
        self, project_id: str, cost_code_id: str, effective_date: date
    ) -> None:
        cost_code = self._cost_code_repo.get(cost_code_id)
        if cost_code is None:
            raise NotFoundError("Cost code not found.", code="COST_CODE_NOT_FOUND")
        if not cost_code.is_effective_on(effective_date):
            raise BusinessRuleError(
                "Cost code is not effective on the financial change date.",
                code="FINANCIAL_CHANGE_COST_CODE_INACTIVE",
            )
        profile = self._financial_profile_repo.get_by_project(project_id)
        if profile and profile.cost_code_policy is CostCodePolicy.RESTRICTED:
            allowed = {
                row.cost_code_id for row in self._cost_code_repo.list_restrictions(project_id)
            }
            if cost_code_id not in allowed:
                raise BusinessRuleError(
                    "Cost code is not permitted for this project.",
                    code="FINANCIAL_CHANGE_COST_CODE_NOT_PERMITTED",
                )

    def _require_task(self, project_id: str, task_id: str):
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        if task.project_id != project_id:
            raise BusinessRuleError(
                "Task does not belong to the financial change project.",
                code="FINANCIAL_CHANGE_TASK_PROJECT_MISMATCH",
            )
        return task

    def _require_project_permission(
        self, project_id: str, permission: str, operation: str
    ) -> None:
        require_permission(self._user_session, permission, operation_label=operation)
        require_project_permission(
            self._user_session, project_id, permission, operation_label=operation
        )

    def _require_context(self, operation: str):
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Active organization context is required for financial change control.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(operation_label=operation)

    def _audit_change(self, operation: str, change: FinancialChangeRequest) -> None:
        self._audit_change_using(self, operation, change)

    @staticmethod
    def _audit_change_using(owner, operation: str, change: FinancialChangeRequest) -> None:
        """Record the change audit through the current transaction-bound owner."""
        record_audit_entry(
            owner,
            operation=f"financial_change.{operation}",
            entity_type="financial_change_request",
            entity_id=change.id,
            entity_parent_id=change.project_id,
            module="project_management",
            old_value=None,
            new_value=json.dumps(
                {
                    "revision": change.revision,
                    "status": change.status.value,
                    "base_budget_id": change.base_budget_id,
                    "base_forecast_id": change.base_forecast_id,
                    "applied_budget_id": change.applied_budget_id,
                    "applied_forecast_id": change.applied_forecast_id,
                    "applied_schedule_count": change.applied_schedule_count,
                },
                sort_keys=True,
            ),
            workspace_id=change.project_id,
            source="application",
            severity="high",
            compliance_tag="financial",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )

    def _audit_impact(
        self, operation: str, change: FinancialChangeRequest, impact: FinancialChangeImpact
    ) -> None:
        record_audit_entry(
            self,
            operation=f"financial_change_impact.{operation}",
            entity_type="financial_change_impact",
            entity_id=impact.id,
            entity_parent_id=change.id,
            module="project_management",
            old_value=None,
            new_value=json.dumps(
                {
                    "impact_type": impact.impact_type.value,
                    "amount": str(impact.amount),
                    "currency_code": impact.currency_code,
                    "target_line_id": impact.target_line_id,
                    "target_task_version": impact.target_task_version,
                },
                sort_keys=True,
            ),
            workspace_id=change.project_id,
            source="application",
            severity="high",
            compliance_tag="financial",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )

    def _audit_version(
        self,
        entity_type: str,
        entity_id: str,
        change: FinancialChangeRequest,
        occurred_at: datetime,
    ) -> None:
        record_audit_entry(
            self,
            operation=f"{entity_type}.apply_financial_change",
            entity_type=entity_type,
            entity_id=entity_id,
            entity_parent_id=change.project_id,
            module="project_management",
            old_value=None,
            new_value=json.dumps(
                {"financial_change_id": change.id, "applied_at": occurred_at.isoformat()},
                sort_keys=True,
            ),
            workspace_id=change.project_id,
            source="application",
            severity="high",
            compliance_tag="financial",
            metadata={"action": "apply_financial_change"},
            commit=False,
            fail_closed=True,
        )

__all__ = ["FinancialChangeService"]
