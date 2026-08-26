from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.modules.project_management.application.common.clock import Clock
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.forecasts.generation_models import (
    ForecastGenerationResult,
    ManualEtcEstimate,
    RiskContingencyEstimate,
)
from src.core.modules.project_management.contracts.repositories.finance.commitments.commitment import (
    ProjectCommitmentRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.cost_entries.cost_entry import (
    ProjectCostEntryRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectCostCodeRepository,
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.forecasts.forecast import (
    ProjectForecastRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.planned_costs.planned_cost import (
    ProjectPlannedCostVersionRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.register.register import (
    RegisterEntryRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import TaskRepository
from src.core.modules.project_management.domain.financials.commitment import (
    ProjectCommitmentLine,
    ProjectCommitmentLineState,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntry,
    ProjectCostEntryKind,
    ProjectCostEntryStatus,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastDecisionAction,
    ForecastDecisionReason,
    ForecastGenerationMode,
    ForecastLine,
    ForecastLineSourceKind,
    ForecastLineSourceType,
    ForecastSourceDecision,
    ProjectForecast,
)
from src.core.modules.project_management.domain.financials.configuration import CostCodePolicy
from src.core.modules.project_management.domain.financials.planned_cost import (
    ProjectPlannedCostLine,
    ProjectPlannedCostVersion,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntry,
    RegisterEntryStatus,
    RegisterEntryType,
)
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


_PAGE_SIZE = 200
_OPEN_CONSTRAINT = "uq_pf_forecasts_one_open_per_project"
_REVISION_CONSTRAINT = "uq_pf_forecast_project_revision"
_ACTIVE_RISK_STATUSES = {
    RegisterEntryStatus.OPEN,
    RegisterEntryStatus.IN_PROGRESS,
    RegisterEntryStatus.MITIGATED,
}
Dimension = tuple[str, str | None]


@dataclass(slots=True)
class _PlanSlice:
    source: ProjectPlannedCostLine
    remaining: Decimal


class ForecastGenerationService(ProjectManagementModuleGuardMixin):
    """Build one atomic ETC draft from canonical source snapshots."""

    def __init__(
        self,
        *,
        session: Session,
        forecast_repo: ProjectForecastRepository,
        project_repo: ProjectRepository,
        financial_profile_repo: ProjectFinancialProfileRepository,
        cost_code_repo: ProjectCostCodeRepository,
        task_repo: TaskRepository,
        planned_cost_repo: ProjectPlannedCostVersionRepository,
        commitment_repo: ProjectCommitmentRepository,
        cost_entry_repo: ProjectCostEntryRepository,
        register_repo: RegisterEntryRepository,
        clock: Clock,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None = None,
    ) -> None:
        self._session = session
        self._forecast_repo = forecast_repo
        self._project_repo = project_repo
        self._financial_profile_repo = financial_profile_repo
        self._cost_code_repo = cost_code_repo
        self._task_repo = task_repo
        self._planned_cost_repo = planned_cost_repo
        self._commitment_repo = commitment_repo
        self._cost_entry_repo = cost_entry_repo
        self._register_repo = register_repo
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service

    def generate_draft(
        self,
        project_id: str,
        *,
        name: str,
        as_of_date: date,
        generated_by: str,
        manual_estimates: tuple[ManualEtcEstimate, ...] = (),
        risk_contingencies: tuple[RiskContingencyEstimate, ...] = (),
        notes: str = "",
    ) -> ForecastGenerationResult:
        self._require_manage(project_id)
        if self._project_repo.get(project_id) is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        profile = self._financial_profile_repo.get_by_project(project_id)
        if profile is None:
            raise NotFoundError(
                "Project financial profile not found; configure finance before forecasting.",
                code="PROJECT_FINANCIAL_PROFILE_NOT_FOUND",
            )
        if as_of_date > self._clock.today():
            raise BusinessRuleError(
                "Forecast as-of date cannot be in the future.",
                code="PROJECT_FORECAST_AS_OF_FUTURE",
            )
        if self._forecast_repo.has_open_for_project(project_id):
            raise BusinessRuleError(
                "A draft or submitted forecast already exists for this project.",
                code="PROJECT_FORECAST_OPEN_VERSION_EXISTS",
            )

        context = self._require_context()
        currency = profile.currency_code
        planned_version = self._planned_version(project_id, as_of_date)
        planned_lines = (
            self._planned_cost_repo.list_lines(planned_version.id)
            if planned_version is not None
            else []
        )
        commitments = self._all_commitments(project_id)
        actuals = self._all_actuals(project_id)
        self._validate_manual_inputs(project_id, as_of_date, manual_estimates)
        risks = self._validated_risks(project_id, as_of_date, risk_contingencies)

        latest = self._forecast_repo.get_latest_for_project(project_id)
        now = self._clock.now()
        generation_mode = (
            ForecastGenerationMode.HYBRID
            if manual_estimates or risk_contingencies
            else ForecastGenerationMode.AUTOMATIC
        )
        forecast = ProjectForecast.create(
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            project_id=project_id,
            name=name,
            currency_code=currency,
            as_of_date=as_of_date,
            generation_mode=generation_mode,
            created_by=generated_by,
            revision=(latest.revision + 1) if latest else 1,
            notes=notes,
            created_at=now,
        )
        lines, decisions, totals = self._build_projection(
            forecast=forecast,
            planned_version=planned_version,
            planned_lines=planned_lines,
            commitments=commitments,
            actuals=actuals,
            manual_estimates=manual_estimates,
            risk_contingencies=risk_contingencies,
            risks=risks,
            generated_by=generated_by,
            now=now,
        )
        if not lines and not decisions:
            raise BusinessRuleError(
                "Forecast generation found no financial sources to snapshot.",
                code="PROJECT_FORECAST_NO_SOURCES",
            )

        try:
            self._forecast_repo.add(forecast)
            self._forecast_repo.flush()
            for line in lines:
                self._forecast_repo.add_line(line)
            self._forecast_repo.add_decisions(decisions)
            self._forecast_repo.flush()
            self._record_audit(forecast, totals, len(lines), len(decisions))
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            self._translate_conflict(exc)
        except Exception:
            self._session.rollback()
            raise
        return ForecastGenerationResult(
            forecast=forecast,
            lines=tuple(lines),
            decisions=tuple(decisions),
            **totals,
        )

    def _build_projection(
        self,
        *,
        forecast: ProjectForecast,
        planned_version: ProjectPlannedCostVersion | None,
        planned_lines: list[ProjectPlannedCostLine],
        commitments: list[ProjectCommitmentLine],
        actuals: list[ProjectCostEntry],
        manual_estimates: tuple[ManualEtcEstimate, ...],
        risk_contingencies: tuple[RiskContingencyEstimate, ...],
        risks: dict[str, RegisterEntry],
        generated_by: str,
        now: datetime,
    ) -> tuple[list[ForecastLine], list[ForecastSourceDecision], dict[str, Decimal]]:
        currency = forecast.currency_code
        for item in planned_lines:
            if item.currency_code != currency:
                raise BusinessRuleError(
                    "Planned-cost currency does not match the forecast currency.",
                    code="PROJECT_FORECAST_PLANNED_COST_CURRENCY_MISMATCH",
                )
        plan = [_PlanSlice(item, item.amount) for item in sorted(planned_lines, key=lambda x: x.id)]
        planned_total = sum((item.remaining for item in plan), Decimal("0"))
        actual_offsets: dict[Dimension, Decimal] = {}
        commitment_offsets: dict[Dimension, Decimal] = {}
        decisions: list[ForecastSourceDecision] = []

        for entry in actuals:
            amount = self._actual_amount(entry, currency)
            snapshot_at = entry.posted_at or entry.updated_at
            if entry.posting_date and entry.posting_date > forecast.as_of_date:
                decisions.append(self._decision(
                    forecast, entry.cost_code_id, entry.task_id,
                    ForecastLineSourceType.POSTED_ACTUAL, "project_cost_entry", entry.id,
                    ForecastDecisionAction.EXCLUDED, ForecastDecisionReason.AFTER_AS_OF,
                    abs(amount), Decimal("0"), abs(amount), snapshot_at, now,
                ))
                continue
            if entry.status == ProjectCostEntryStatus.REVERSED or entry.entry_kind == ProjectCostEntryKind.REVERSAL:
                decisions.append(self._decision(
                    forecast, entry.cost_code_id, entry.task_id,
                    ForecastLineSourceType.POSTED_ACTUAL, "project_cost_entry", entry.id,
                    ForecastDecisionAction.EXCLUDED, ForecastDecisionReason.REVERSED_ACTUAL,
                    abs(amount), Decimal("0"), abs(amount), snapshot_at, now,
                ))
                continue
            if amount < 0:
                key = (entry.cost_code_id, entry.task_id)
                actual_offsets[key] = actual_offsets.get(key, Decimal("0")) + amount
                decisions.append(self._decision(
                    forecast, entry.cost_code_id, entry.task_id,
                    ForecastLineSourceType.POSTED_ACTUAL, "project_cost_entry", entry.id,
                    ForecastDecisionAction.EXCLUDED, ForecastDecisionReason.ACTUAL_CREDIT,
                    abs(amount), Decimal("0"), abs(amount), snapshot_at, now,
                ))
            else:
                key = (entry.cost_code_id, entry.task_id)
                actual_offsets[key] = actual_offsets.get(key, Decimal("0")) + amount
                decisions.append(self._decision(
                    forecast, entry.cost_code_id, entry.task_id,
                    ForecastLineSourceType.POSTED_ACTUAL, "project_cost_entry", entry.id,
                    ForecastDecisionAction.OFFSET, ForecastDecisionReason.POSTED_ACTUAL_OFFSET,
                    amount, Decimal("0"), amount, snapshot_at, now,
                ))
        actual_offsets = {
            dimension: max(Decimal("0"), amount)
            for dimension, amount in actual_offsets.items()
        }
        posted_actual_total = sum(actual_offsets.values(), Decimal("0"))

        lines: list[ForecastLine] = []
        open_commitment_total = Decimal("0")
        for item in commitments:
            remaining = self._commitment_amount(item, currency)
            snapshot_at = item.updated_at
            if snapshot_at.date() > forecast.as_of_date:
                raise BusinessRuleError(
                    "A commitment was updated after the forecast as-of date; historical reconstruction is unavailable.",
                    code="PROJECT_FORECAST_COMMITMENT_AFTER_AS_OF",
                )
            if remaining <= 0:
                reason = (
                    ForecastDecisionReason.CLOSED_OR_CANCELLED
                    if item.state in {ProjectCommitmentLineState.CLOSED, ProjectCommitmentLineState.CANCELLED}
                    else ForecastDecisionReason.NO_REMAINING_AMOUNT
                )
                decisions.append(self._decision(
                    forecast, item.cost_code_id, item.task_id,
                    ForecastLineSourceType.OPEN_COMMITMENT, "project_commitment_line", item.id,
                    ForecastDecisionAction.EXCLUDED, reason,
                    max(Decimal("0"), self._commitment_gross_amount(item, currency)),
                    Decimal("0"), max(Decimal("0"), self._commitment_gross_amount(item, currency)),
                    snapshot_at, now,
                ))
                continue
            open_commitment_total += remaining
            key = (item.cost_code_id, item.task_id)
            commitment_offsets[key] = commitment_offsets.get(key, Decimal("0")) + remaining
            lines.append(self._line(
                forecast, item.cost_code_id, item.task_id,
                f"Open commitment {item.purchase_order_line_id}", remaining,
                ForecastLineSourceKind.AUTOMATIC, ForecastLineSourceType.OPEN_COMMITMENT,
                "project_commitment_line", item.id, snapshot_at, generated_by, now,
            ))
            decisions.append(self._decision(
                forecast, item.cost_code_id, item.task_id,
                ForecastLineSourceType.OPEN_COMMITMENT, "project_commitment_line", item.id,
                ForecastDecisionAction.INCLUDED, ForecastDecisionReason.OPEN_COMMITMENT,
                remaining, remaining, Decimal("0"), snapshot_at, now,
            ))

        self._apply_offsets(plan, actual_offsets)
        self._apply_offsets(plan, commitment_offsets)
        manual_by_dimension = {(item.cost_code_id, item.task_id): item for item in manual_estimates}
        manual_cost_scopes = {item.cost_code_id for item in manual_estimates if item.task_id is None}
        remaining_plan_total = Decimal("0")
        for item in plan:
            source = item.source
            overridden = (
                source.cost_code_id in manual_cost_scopes
                or (source.cost_code_id, source.task_id) in manual_by_dimension
            )
            included = Decimal("0") if overridden else item.remaining
            excluded = source.amount - included
            reason = (
                ForecastDecisionReason.MANUAL_OVERRIDE
                if overridden
                else ForecastDecisionReason.REMAINING_PLAN
                if included > 0
                else ForecastDecisionReason.NO_REMAINING_AMOUNT
            )
            action = (
                ForecastDecisionAction.INCLUDED
                if included > 0
                else ForecastDecisionAction.EXCLUDED
            )
            decisions.append(self._decision(
                forecast, source.cost_code_id, source.task_id,
                ForecastLineSourceType.REMAINING_PLAN, "project_planned_cost_line", source.id,
                action, reason, source.amount, included, excluded,
                planned_version.calculated_at if planned_version else now, now,
            ))
            if included > 0:
                remaining_plan_total += included
                lines.append(self._line(
                    forecast, source.cost_code_id, source.task_id,
                    "Remaining planned cost", included,
                    ForecastLineSourceKind.AUTOMATIC, ForecastLineSourceType.REMAINING_PLAN,
                    "project_planned_cost_line", source.id,
                    planned_version.calculated_at if planned_version else now,
                    generated_by, now,
                ))

        manual_total = Decimal("0")
        for item in manual_estimates:
            manual_total += item.amount
            reference_id = f"{item.cost_code_id}:{item.task_id or '*'}"
            if item.amount > 0:
                lines.append(self._line(
                    forecast, item.cost_code_id, item.task_id, item.description, item.amount,
                    ForecastLineSourceKind.MANUAL, ForecastLineSourceType.MANUAL_ESTIMATE,
                    "manual_etc_estimate", reference_id, now, generated_by, now,
                    item.period_start, item.period_end,
                ))
            decisions.append(self._decision(
                forecast, item.cost_code_id, item.task_id,
                ForecastLineSourceType.MANUAL_ESTIMATE, "manual_etc_estimate", reference_id,
                ForecastDecisionAction.INCLUDED if item.amount > 0 else ForecastDecisionAction.EXCLUDED,
                ForecastDecisionReason.MANUAL_OVERRIDE,
                item.amount, item.amount, Decimal("0"), now, now,
            ))

        risk_total = Decimal("0")
        for item in risk_contingencies:
            risk = risks[item.risk_id]
            risk_total += item.amount
            snapshot_at = risk.updated_at
            if item.amount > 0:
                lines.append(self._line(
                    forecast, item.cost_code_id, item.task_id,
                    item.description or f"Risk contingency: {risk.title}", item.amount,
                    ForecastLineSourceKind.MANUAL, ForecastLineSourceType.RISK,
                    "register_risk", risk.id, snapshot_at, generated_by, now,
                    item.period_start, item.period_end,
                ))
            decisions.append(self._decision(
                forecast, item.cost_code_id, item.task_id,
                ForecastLineSourceType.RISK, "register_risk", risk.id,
                ForecastDecisionAction.INCLUDED if item.amount > 0 else ForecastDecisionAction.EXCLUDED,
                ForecastDecisionReason.RISK_CONTINGENCY,
                item.amount, item.amount, Decimal("0"), snapshot_at, now,
            ))

        etc_total = open_commitment_total + remaining_plan_total + manual_total + risk_total
        return lines, decisions, {
            "planned_total": planned_total,
            "posted_actual_offset": posted_actual_total,
            "open_commitment_total": open_commitment_total,
            "remaining_plan_total": remaining_plan_total,
            "manual_etc_total": manual_total,
            "risk_contingency_total": risk_total,
            "etc_total": etc_total,
        }

    @staticmethod
    def _apply_offsets(plan: list[_PlanSlice], offsets: dict[Dimension, Decimal]) -> None:
        for (cost_code_id, task_id), amount in sorted(
            offsets.items(), key=lambda item: (item[0][0], item[0][1] or "")
        ):
            remaining_offset = max(Decimal("0"), amount)
            candidates = [
                item for item in plan
                if item.source.cost_code_id == cost_code_id
                and (task_id is None or item.source.task_id == task_id)
            ]
            candidates.sort(key=lambda item: (item.source.task_id or "", item.source.id))
            for item in candidates:
                applied = min(item.remaining, remaining_offset)
                item.remaining -= applied
                remaining_offset -= applied
                if remaining_offset <= 0:
                    break

    def _planned_version(
        self, project_id: str, as_of_date: date
    ) -> ProjectPlannedCostVersion | None:
        versions = [
            item for item in self._planned_cost_repo.list_for_project(project_id)
            if item.as_of <= as_of_date
        ]
        if not versions:
            return None
        version = max(versions, key=lambda item: (item.as_of, item.revision))
        if not (version.rates_complete and version.allocations_complete and version.cost_codes_complete):
            raise BusinessRuleError(
                "The selected planned-cost snapshot is incomplete and cannot drive a forecast.",
                code="PROJECT_FORECAST_PLANNED_COST_INCOMPLETE",
            )
        return version

    def _all_commitments(self, project_id: str) -> list[ProjectCommitmentLine]:
        result: list[ProjectCommitmentLine] = []
        offset = 0
        while True:
            rows, total = self._commitment_repo.list_lines_for_project(
                project_id, offset=offset, limit=_PAGE_SIZE
            )
            result.extend(rows)
            offset += len(rows)
            if not rows or offset >= total:
                return result

    def _all_actuals(self, project_id: str) -> list[ProjectCostEntry]:
        result: list[ProjectCostEntry] = []
        for status in (ProjectCostEntryStatus.POSTED, ProjectCostEntryStatus.REVERSED):
            offset = 0
            while True:
                rows, total = self._cost_entry_repo.list_for_project(
                    project_id, status=status, offset=offset, limit=_PAGE_SIZE
                )
                result.extend(rows)
                offset += len(rows)
                if not rows or offset >= total:
                    break
        return result

    def _validate_manual_inputs(
        self,
        project_id: str,
        as_of_date: date,
        items: tuple[ManualEtcEstimate, ...],
    ) -> None:
        dimensions: set[Dimension] = set()
        cost_scopes: set[str] = set()
        for item in items:
            key = (item.cost_code_id, item.task_id)
            if key in dimensions:
                raise BusinessRuleError(
                    "Only one manual ETC estimate is allowed per cost-code/task dimension.",
                    code="PROJECT_FORECAST_MANUAL_DUPLICATE",
                )
            if item.task_id is None:
                if item.cost_code_id in {code for code, _task in dimensions}:
                    raise BusinessRuleError(
                        "Cost-code and task-level manual ETC overrides cannot be mixed for one cost code.",
                        code="PROJECT_FORECAST_MANUAL_SCOPE_OVERLAP",
                    )
                cost_scopes.add(item.cost_code_id)
            elif item.cost_code_id in cost_scopes:
                raise BusinessRuleError(
                    "Cost-code and task-level manual ETC overrides cannot be mixed for one cost code.",
                    code="PROJECT_FORECAST_MANUAL_SCOPE_OVERLAP",
                )
            dimensions.add(key)
            self._require_dimension(
                project_id, item.cost_code_id, item.task_id, as_of_date
            )

    def _validated_risks(
        self,
        project_id: str,
        as_of_date: date,
        items: tuple[RiskContingencyEstimate, ...],
    ) -> dict[str, RegisterEntry]:
        result: dict[str, RegisterEntry] = {}
        for item in items:
            if item.risk_id in result:
                raise BusinessRuleError(
                    "A risk can appear only once in a generated forecast.",
                    code="PROJECT_FORECAST_RISK_DUPLICATE",
                )
            risk = self._register_repo.get(item.risk_id)
            if risk is None or risk.project_id != project_id or risk.entry_type != RegisterEntryType.RISK:
                raise NotFoundError(
                    "Active project risk not found.",
                    code="PROJECT_FORECAST_RISK_NOT_FOUND",
                )
            if risk.status not in _ACTIVE_RISK_STATUSES:
                raise BusinessRuleError(
                    "Closed, rejected, or approved register items cannot add forecast contingency.",
                    code="PROJECT_FORECAST_RISK_INACTIVE",
                )
            if risk.updated_at is None or risk.updated_at.date() > as_of_date:
                raise BusinessRuleError(
                    "Risk state is newer than the forecast as-of date.",
                    code="PROJECT_FORECAST_RISK_AFTER_AS_OF",
                )
            self._require_dimension(
                project_id, item.cost_code_id, item.task_id, as_of_date
            )
            result[item.risk_id] = risk
        return result

    def _require_dimension(
        self,
        project_id: str,
        cost_code_id: str,
        task_id: str | None,
        effective_on: date,
    ) -> None:
        cost_code = self._cost_code_repo.get(cost_code_id)
        if cost_code is None:
            raise NotFoundError(
                "Cost code not found.",
                code="PROJECT_FORECAST_LINE_COST_CODE_NOT_FOUND",
            )
        if not cost_code.is_effective_on(effective_on):
            raise BusinessRuleError(
                "Cost code is not active or effective for this date.",
                code="PROJECT_FORECAST_LINE_COST_CODE_INACTIVE",
            )
        profile = self._financial_profile_repo.get_by_project(project_id)
        if profile and profile.cost_code_policy == CostCodePolicy.RESTRICTED:
            allowed = {
                row.cost_code_id
                for row in self._cost_code_repo.list_restrictions(project_id)
            }
            if cost_code_id not in allowed:
                raise BusinessRuleError(
                    "This cost code is not permitted for this project.",
                    code="PROJECT_FORECAST_LINE_COST_CODE_NOT_PERMITTED",
                )
        if task_id is not None:
            task = self._task_repo.get(task_id)
            if task is None:
                raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
            if task.project_id != project_id:
                raise BusinessRuleError(
                    "Task does not belong to this project.",
                    code="PROJECT_FORECAST_LINE_TASK_PROJECT_MISMATCH",
                )

    @staticmethod
    def _actual_amount(entry: ProjectCostEntry, currency: str) -> Decimal:
        if entry.currency_code == currency:
            return entry.amount
        if entry.base_currency_code == currency and entry.base_amount is not None:
            return entry.base_amount
        raise BusinessRuleError(
            "Posted actual currency cannot be reconciled to the forecast currency.",
            code="PROJECT_FORECAST_ACTUAL_CURRENCY_MISMATCH",
        )

    @staticmethod
    def _commitment_amount(item: ProjectCommitmentLine, currency: str) -> Decimal:
        if item.state in {ProjectCommitmentLineState.CLOSED, ProjectCommitmentLineState.CANCELLED}:
            return Decimal("0")
        if item.currency_code == currency:
            return item.amount - item.matched_amount
        if item.base_currency_code == currency:
            matched_base = item.matched_amount * item.exchange_rate
            return max(Decimal("0"), item.base_amount - matched_base)
        raise BusinessRuleError(
            "Commitment currency cannot be reconciled to the forecast currency.",
            code="PROJECT_FORECAST_COMMITMENT_CURRENCY_MISMATCH",
        )

    @staticmethod
    def _commitment_gross_amount(item: ProjectCommitmentLine, currency: str) -> Decimal:
        if item.currency_code == currency:
            return item.amount - item.matched_amount
        if item.base_currency_code == currency:
            return item.base_amount - (item.matched_amount * item.exchange_rate)
        raise BusinessRuleError(
            "Commitment currency cannot be reconciled to the forecast currency.",
            code="PROJECT_FORECAST_COMMITMENT_CURRENCY_MISMATCH",
        )

    @staticmethod
    def _line(
        forecast: ProjectForecast,
        cost_code_id: str,
        task_id: str | None,
        description: str,
        amount: Decimal,
        source_kind: ForecastLineSourceKind,
        source_type: ForecastLineSourceType,
        source_reference_type: str,
        source_reference_id: str,
        source_snapshot_at: datetime,
        generated_by: str,
        now: datetime,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> ForecastLine:
        return ForecastLine.create(
            tenant_id=forecast.tenant_id,
            organization_id=forecast.organization_id,
            forecast_id=forecast.id,
            project_id=forecast.project_id,
            cost_code_id=cost_code_id,
            task_id=task_id,
            description=description,
            amount=amount,
            currency_code=forecast.currency_code,
            source_kind=source_kind,
            source_type=source_type,
            source_reference_type=source_reference_type,
            source_reference_id=source_reference_id,
            source_snapshot_at=source_snapshot_at,
            period_start=period_start,
            period_end=period_end,
            created_by=generated_by,
            created_at=now,
        )

    @staticmethod
    def _decision(
        forecast: ProjectForecast,
        cost_code_id: str,
        task_id: str | None,
        source_type: ForecastLineSourceType,
        source_reference_type: str,
        source_reference_id: str,
        action: ForecastDecisionAction,
        reason: ForecastDecisionReason,
        source_amount: Decimal,
        included_amount: Decimal,
        excluded_amount: Decimal,
        source_snapshot_at: datetime,
        now: datetime,
    ) -> ForecastSourceDecision:
        return ForecastSourceDecision.create(
            tenant_id=forecast.tenant_id,
            organization_id=forecast.organization_id,
            forecast_id=forecast.id,
            project_id=forecast.project_id,
            cost_code_id=cost_code_id,
            task_id=task_id,
            source_type=source_type,
            source_reference_type=source_reference_type,
            source_reference_id=source_reference_id,
            action=action,
            reason=reason,
            source_amount=source_amount,
            included_amount=included_amount,
            excluded_amount=excluded_amount,
            currency_code=forecast.currency_code,
            source_snapshot_at=source_snapshot_at,
            created_at=now,
        )

    def _require_manage(self, project_id: str) -> None:
        require_permission(
            self._user_session, "forecast.manage", operation_label="generate project forecast"
        )
        require_project_permission(
            self._user_session,
            project_id,
            "forecast.manage",
            operation_label="generate project forecast",
        )

    def _require_context(self):
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Active organization context is required to generate a forecast.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(
            operation_label="generate project forecast"
        )

    @staticmethod
    def _integrity_message(exc: IntegrityError) -> str:
        return str(getattr(exc, "orig", "") or exc).lower()

    def _translate_conflict(self, exc: IntegrityError) -> None:
        message = self._integrity_message(exc)
        if _REVISION_CONSTRAINT in message or "revision" in message:
            raise ConcurrencyError(
                "Another forecast revision was generated concurrently. Refresh and try again.",
                code="PROJECT_FORECAST_REVISION_CONFLICT",
            ) from exc
        if _OPEN_CONSTRAINT in message or "project_finance_forecasts" in message:
            raise BusinessRuleError(
                "A draft or submitted forecast already exists for this project.",
                code="PROJECT_FORECAST_OPEN_VERSION_EXISTS",
            ) from exc
        raise

    def _record_audit(
        self,
        forecast: ProjectForecast,
        totals: dict[str, Decimal],
        line_count: int,
        decision_count: int,
    ) -> None:
        record_audit_entry(
            self,
            operation="project_forecast.generate",
            entity_type="project_forecast",
            entity_id=forecast.id,
            entity_parent_id=forecast.project_id,
            module="project_management",
            old_value=None,
            new_value=json.dumps(
                {
                    "revision": forecast.revision,
                    "as_of_date": forecast.as_of_date.isoformat(),
                    "generation_mode": forecast.generation_mode.value,
                    "line_count": line_count,
                    "decision_count": decision_count,
                    **{key: str(value) for key, value in totals.items()},
                },
                sort_keys=True,
            ),
            workspace_id=forecast.project_id,
            source="application",
            severity="high",
            compliance_tag="financial",
            metadata={"action": "generate"},
            commit=False,
            fail_closed=True,
        )


__all__ = ["ForecastGenerationService"]
