from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.application.financials.financial_changes._command_values import (
    command_amount,
    command_date,
    command_impact_type,
    optional_command_date,
)
from src.core.modules.project_management.application.financials.financial_changes.dto.commands.change_draft import (
    FinancialCreateChangeCommand,
    FinancialUpdateChangeCommand,
)
from src.core.modules.project_management.application.financials.financial_changes.dto.commands.change_impacts import (
    FinancialChangeImpactCommand,
    FinancialRemoveChangeImpactCommand,
    FinancialUpdateChangeImpactCommand,
)
from src.core.modules.project_management.application.financials.financial_changes.dto.responses.mutations import (
    FinancialChangeMutationDto,
)
from src.core.modules.project_management.application.financials.financial_changes.financial_change_events import (
    FinancialChangeEventType,
)
from src.core.modules.project_management.application.financials.financial_changes.mappers.responses import (
    map_change,
)
from src.core.modules.project_management.application.financials.financial_changes.policy import (
    FinancialChangeAuditPolicy,
    FinancialChangeValidationPolicy,
)
from src.core.modules.project_management.contracts.ports.scheduling.schedule_change import (
    ApprovedScheduleChangePort,
)
from src.core.modules.project_management.contracts.repositories.finance.budgets.budget import (
    ProjectBudgetRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectCostCodeRepository,
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.financial_changes.financial_change import (
    FinancialChangeRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.forecasts.forecast import (
    ProjectForecastRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    TaskRepository,
)
from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpact,
    FinancialChangeImpactType,
    FinancialChangeRequest,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
)
from src.core.shared.time.clock import CalendarClock

_REVISION_CONSTRAINT = "uq_pf_change_project_revision"


class FinancialChangeDraftCommandHandler(
    FinancialChangeValidationPolicy, FinancialChangeAuditPolicy
):
    """Edit draft change requests and impacts in the caller-owned transaction."""

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
        clock: CalendarClock,
        record_event: Callable[[object], None] | None = None,
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
        self._clock = clock
        self._record_event = record_event
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service

    def create_change(self, command: FinancialCreateChangeCommand) -> FinancialChangeMutationDto:
        created_by = self._command_actor_id()
        effective_date = command_date(command.effective_date, "Effective date")
        self._require_project_permission(
            command.project_id, "financial_change.manage", "create financial change"
        )
        if self._project_repo.get(command.project_id) is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        profile = self._financial_profile_repo.get_by_project(command.project_id)
        if profile is None:
            raise NotFoundError(
                "Project financial profile not found; configure finance before change control.",
                code="PROJECT_FINANCIAL_PROFILE_NOT_FOUND",
            )
        context = self._require_context("create financial change")
        latest = self._change_repo.get_latest_for_project(command.project_id)
        base_budget = self._budget_repo.get_approved_for_project(command.project_id)
        base_forecast = self._forecast_repo.get_approved_for_project(command.project_id)
        now = self._clock.now()
        change = FinancialChangeRequest.create(
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            project_id=command.project_id,
            title=command.title,
            reason=command.reason,
            description=command.description,
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
        return map_change(change)

    def update_change(self, command: FinancialUpdateChangeCommand) -> FinancialChangeMutationDto:
        effective_date = command_date(command.effective_date, "Effective date")
        change = self._require_mutable_change(
            command.change_id, command.expected_version, "update financial change"
        )
        now = self._clock.now()
        change.update_draft(
            title=command.title,
            reason=command.reason,
            description=command.description,
            effective_date=effective_date,
            updated_at=now,
        )
        for impact in self._change_repo.list_impacts(change.id):
            if impact.cost_code_id:
                self._require_cost_code(
                    change.project_id, impact.cost_code_id, effective_date
                )
        self._change_repo.update(change, expected_row_version=command.expected_version)
        self._audit_change("update", change)
        self._session.flush()
        self._emit_change_event(change, FinancialChangeEventType.UPDATED)
        return map_change(change)

    def add_impact(self, command: FinancialChangeImpactCommand) -> FinancialChangeMutationDto:
        amount = command_amount(command.amount)
        impact_type = command_impact_type(command.impact_type)
        change = self._require_mutable_change(
            command.change_id, command.expected_change_version, "add financial change impact"
        )
        resolved_currency = (command.currency_code or None) or (
            change.currency_code if amount != 0 else None
        )
        if resolved_currency and resolved_currency != change.currency_code:
            raise BusinessRuleError(
                "Financial change impact currency must match the project finance currency.",
                code="FINANCIAL_CHANGE_CURRENCY_MISMATCH",
            )
        if command.cost_code_id:
            self._require_cost_code(
                change.project_id, command.cost_code_id, change.effective_date
            )
        task = self._require_task(change.project_id, command.task_id) if command.task_id else None
        impact = FinancialChangeImpact.create(
            tenant_id=change.tenant_id,
            organization_id=change.organization_id,
            change_request_id=change.id,
            project_id=change.project_id,
            impact_type=impact_type,
            description=command.description,
            amount=amount,
            currency_code=resolved_currency,
            cost_code_id=command.cost_code_id,
            task_id=command.task_id,
            target_line_id=command.target_line_id,
            target_task_version=(
                task.version
                if task is not None
                and impact_type is FinancialChangeImpactType.SCHEDULE
                else None
            ),
            schedule_start=optional_command_date(command.schedule_start),
            schedule_finish=optional_command_date(command.schedule_finish),
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
        self._change_repo.update(change, expected_row_version=command.expected_change_version)
        self._audit_impact("add", change, impact)
        self._session.flush()
        self._emit_change_event(
            change, FinancialChangeEventType.IMPACT_ADDED, impact_id=impact.id
        )
        return map_change(change, impact=impact)

    def update_impact(self, command: FinancialUpdateChangeImpactCommand) -> FinancialChangeMutationDto:
        amount = command_amount(command.amount)
        impact_type = command_impact_type(command.impact_type)
        impact = self._require_impact(command.impact_id)
        if impact.impact_type is not impact_type:
            raise BusinessRuleError(
                "Financial change impact type is immutable.",
                code="FINANCIAL_CHANGE_IMPACT_TYPE_IMMUTABLE",
            )
        change = self._require_mutable_change(
            impact.change_request_id,
            command.expected_change_version,
            "update financial change impact",
        )
        if impact.row_version != command.expected_impact_version:
            raise ConcurrencyError(
                "Financial change impact was updated since you opened it.",
                code="STALE_WRITE",
            )
        resolved_currency = (command.currency_code or None) or (
            change.currency_code if amount != 0 else None
        )
        if resolved_currency and resolved_currency != change.currency_code:
            raise BusinessRuleError(
                "Financial change impact currency must match the project finance currency.",
                code="FINANCIAL_CHANGE_CURRENCY_MISMATCH",
            )
        if command.cost_code_id:
            self._require_cost_code(
                change.project_id, command.cost_code_id, change.effective_date
            )
        task = self._require_task(change.project_id, command.task_id) if command.task_id else None
        now = self._clock.now()
        impact.update_draft(
            description=command.description,
            amount=amount,
            currency_code=resolved_currency,
            cost_code_id=command.cost_code_id,
            task_id=command.task_id,
            target_line_id=command.target_line_id,
            target_task_version=(
                task.version
                if task is not None
                and impact.impact_type is FinancialChangeImpactType.SCHEDULE
                else None
            ),
            schedule_start=optional_command_date(command.schedule_start),
            schedule_finish=optional_command_date(command.schedule_finish),
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
            impact, expected_row_version=command.expected_impact_version
        )
        change.touch(updated_at=now)
        self._change_repo.update(change, expected_row_version=command.expected_change_version)
        self._audit_impact("update", change, impact)
        self._session.flush()
        self._emit_change_event(
            change, FinancialChangeEventType.IMPACT_UPDATED, impact_id=impact.id
        )
        return map_change(change, impact=impact)

    def remove_impact(self, command: FinancialRemoveChangeImpactCommand) -> FinancialChangeMutationDto:
        impact = self._require_impact(command.impact_id)
        change = self._require_mutable_change(
            impact.change_request_id,
            command.expected_change_version,
            "remove financial change impact",
        )
        if impact.applied_reference_id:
            raise BusinessRuleError(
                "Applied financial change impacts cannot be removed.",
                code="FINANCIAL_CHANGE_IMPACT_APPLIED",
            )
        self._audit_impact("remove", change, impact)
        self._change_repo.delete_impact(
            impact.id, expected_row_version=command.expected_impact_version
        )
        change.touch(updated_at=self._clock.now())
        self._change_repo.update(change, expected_row_version=command.expected_change_version)
        self._session.flush()
        self._emit_change_event(
            change, FinancialChangeEventType.IMPACT_REMOVED, impact_id=impact.id
        )
        return map_change(change)


__all__ = ["FinancialChangeDraftCommandHandler"]
