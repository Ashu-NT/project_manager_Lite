from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Final

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.forecasts.approval_result import (
    ForecastApprovalRequestResult,
)
from src.core.modules.project_management.application.financials.forecasts.forecast_events import (
    ForecastVersionChanged,
    ForecastVersionChangeType,
)
from src.core.modules.project_management.application.financials.shared.successor_models import (
    ApprovedFinancialLineAdjustment,
    ApprovedFinancialSuccessorResult,
)
from src.core.modules.project_management.contracts.repositories.finance.forecasts.forecast import (
    ProjectForecastRepository,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastDecisionAction,
    ForecastDecisionReason,
    ForecastGenerationMode,
    ForecastLine,
    ForecastLineSourceKind,
    ForecastLineSourceType,
    ForecastSourceDecision,
    ForecastStatus,
    ProjectForecast,
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
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.time.clock import CalendarClock

_OPEN_CONSTRAINT = "uq_pf_forecasts_one_open_per_project"
_APPROVED_CONSTRAINT = "uq_pf_forecasts_one_approved_per_project"
_REVISION_CONSTRAINT = "uq_pf_forecast_project_revision"
class _Unset(Enum):
    """Typed sentinel distinguishing "argument omitted" from an explicit None."""

    TOKEN = 0


_UNSET: Final = _Unset.TOKEN


class ForecastApprovalCommands(ProjectManagementModuleGuardMixin):
    """Approval decisions and approved financial-change participation."""

    def __init__(
        self,
        *,
        session: Session,
        forecast_repo: ProjectForecastRepository,
        clock: CalendarClock,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None = None,
        record_event: Callable[[object], None] | None = None,
        approval_commands=None,
    ) -> None:
        self._session = session
        self._forecast_repo = forecast_repo
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._record_event = record_event
        self._approval_commands = approval_commands


    def _emit_version_event(
        self, forecast: ProjectForecast, *, change_type: ForecastVersionChangeType, occurred_at: datetime
    ) -> None:
        if self._record_event is None:
            return
        self._record_event(
            ForecastVersionChanged(
                tenant_id=forecast.tenant_id,
                organization_id=forecast.organization_id,
                project_id=forecast.project_id,
                forecast_id=forecast.id,
                change_type=change_type,
                occurred_at=occurred_at,
            )
        )


    def approve_forecast(
        self,
        forecast_id: str,
        *,
        approved_by: str,
        expected_version: int,
        notes: str = "",
    ) -> ProjectForecast:
        forecast = self._require_forecast(forecast_id)
        self._require_project_permission(
            forecast.project_id, "forecast.approve", "approve project forecast"
        )
        if forecast.row_version != expected_version:
            raise ConcurrencyError("Forecast changed since you opened it.", code="STALE_WRITE")
        return self._apply_approval_decision(
            forecast_id=forecast_id,
            approved_by=approved_by,
            expected_version=expected_version,
            notes=notes,
        )


    def request_forecast_approval(
        self, forecast_id: str, *, expected_version: int, notes: str = ""
    ) -> ForecastApprovalRequestResult:
        if self._approval_commands is None:
            raise BusinessRuleError(
                "Platform Approval is not configured for Forecast decisions.",
                code="PROJECT_FORECAST_APPROVAL_UNAVAILABLE",
            )
        forecast = self._require_forecast(forecast_id)
        self._require_project_permission(
            forecast.project_id, "approval.request", "request project forecast approval"
        )
        if forecast.row_version != expected_version:
            raise ConcurrencyError("Forecast changed since you opened it.", code="STALE_WRITE")
        if forecast.status != ForecastStatus.SUBMITTED:
            raise BusinessRuleError(
                "Only a submitted Forecast can be sent for approval.",
                code="PROJECT_FORECAST_APPROVAL_STATUS_INVALID",
            )
        request = self._approval_commands.request_change(
            request_type="forecast.approve",
            entity_type="project_forecast",
            entity_id=forecast.id,
            project_id=forecast.project_id,
            payload={
                "forecast_id": forecast.id,
                "expected_version": expected_version,
                "notes": notes,
            },
        )
        return ForecastApprovalRequestResult(
            forecast_id=forecast.id,
            project_id=forecast.project_id,
            forecast_status=forecast.status,
            row_version=forecast.row_version,
            approval_request_id=request.id,
        )


    def reject_forecast(
        self,
        forecast_id: str,
        *,
        rejected_by: str,
        expected_version: int,
        notes: str = "",
    ) -> ProjectForecast:
        forecast = self._require_forecast(forecast_id)
        self._require_project_permission(
            forecast.project_id, "forecast.approve", "reject project forecast"
        )
        if forecast.row_version != expected_version:
            raise ConcurrencyError("Forecast changed since you opened it.", code="STALE_WRITE")
        return self._apply_rejection_decision(
            forecast_id=forecast_id,
            rejected_by=rejected_by,
            expected_version=expected_version,
            notes=notes,
        )


    def _apply_approval_decision(
        self, *, forecast_id: str, approved_by: str, expected_version: int, notes: str
    ) -> ProjectForecast:
        forecast = self._require_forecast(forecast_id)
        if forecast.row_version != expected_version:
            raise ConcurrencyError("Forecast changed since you opened it.", code="STALE_WRITE")
        now = self._clock.now()
        previous = self._forecast_repo.get_approved_for_project(forecast.project_id)
        try:
            if previous is not None:
                previous_version = previous.row_version
                previous.supersede(superseded_by=approved_by, superseded_at=now)
                self._forecast_repo.update(previous, expected_row_version=previous_version)
                self._forecast_repo.flush()
            forecast.approve(approved_by=approved_by, approved_at=now, notes=notes)
            self._forecast_repo.update(forecast, expected_row_version=expected_version)
            self._forecast_repo.flush()
        except IntegrityError as exc:
            if self._is_approval_conflict(exc):
                raise BusinessRuleError(
                    "Another forecast version was approved concurrently.",
                    code="PROJECT_FORECAST_APPROVAL_CONFLICT",
                ) from exc
            raise
        self._record_forecast_audit("approve", forecast)
        self._session.flush()
        self._emit_version_event(
            forecast, change_type=ForecastVersionChangeType.APPROVED, occurred_at=now
        )
        return forecast


    def _apply_approved_financial_change(
        self,
        *,
        base_forecast_id: str,
        expected_base_revision: int,
        project_id: str,
        name: str,
        reason: str,
        actor_id: str,
        as_of_date: date,
        adjustments: tuple[ApprovedFinancialLineAdjustment, ...],
        occurred_at: datetime,
    ) -> ApprovedFinancialSuccessorResult:
        """Apply an already-approved Change through the Forecast authority."""
        base = self._require_forecast(base_forecast_id)
        if (
            base.project_id != project_id
            or base.status is not ForecastStatus.APPROVED
            or base.revision != expected_base_revision
        ):
            raise ConcurrencyError(
                "The approved forecast changed after this financial change was drafted.",
                code="FINANCIAL_CHANGE_FORECAST_BASE_STALE",
            )
        current = self._forecast_repo.get_approved_for_project(project_id)
        if current is None or current.id != base.id or current.revision != base.revision:
            raise ConcurrencyError(
                "The approved forecast changed after this financial change was drafted.",
                code="FINANCIAL_CHANGE_FORECAST_BASE_STALE",
            )
        if self._forecast_repo.has_open_for_project(project_id):
            raise BusinessRuleError(
                "An open forecast version must be resolved before applying a financial change.",
                code="FINANCIAL_CHANGE_OPEN_FORECAST_EXISTS",
            )
        by_target = {row.target_line_id: row for row in adjustments if row.target_line_id}
        latest = self._forecast_repo.get_latest_for_project(project_id)
        successor = ProjectForecast.create(
            tenant_id=base.tenant_id,
            organization_id=base.organization_id,
            project_id=project_id,
            name=name,
            currency_code=base.currency_code,
            as_of_date=as_of_date,
            generation_mode=ForecastGenerationMode.HYBRID,
            created_by=actor_id,
            revision=(latest.revision + 1) if latest else 1,
            notes=reason,
            created_at=occurred_at,
        )
        successor.submit(submitted_by=actor_id, submitted_at=occurred_at, notes=reason)
        successor.approve(approved_by=actor_id, approved_at=occurred_at, notes=reason)
        base_version = base.row_version
        base.supersede(superseded_by=actor_id, superseded_at=occurred_at)
        self._forecast_repo.update(base, expected_row_version=base_version)
        self._forecast_repo.flush()
        self._forecast_repo.add(successor)
        self._forecast_repo.flush()
        references: list[tuple[str, str]] = []
        decisions: list[ForecastSourceDecision] = []
        for source in self._forecast_repo.list_lines(base.id):
            adjustment = by_target.get(source.id)
            amount = source.amount + (adjustment.amount if adjustment else Decimal(0))
            if amount < 0:
                raise BusinessRuleError(
                    "Forecast change would make a successor line negative.",
                    code="FINANCIAL_CHANGE_FORECAST_NEGATIVE_RESULT",
                )
            reference_type = (
                "financial_change_impact" if adjustment else "project_forecast_line"
            )
            reference_id = adjustment.impact_id if adjustment else source.id
            source_type = (
                ForecastLineSourceType.FINANCIAL_CHANGE
                if adjustment
                else ForecastLineSourceType.BASE_FORECAST
            )
            line = ForecastLine.create(
                tenant_id=base.tenant_id,
                organization_id=base.organization_id,
                forecast_id=successor.id,
                project_id=project_id,
                cost_code_id=source.cost_code_id,
                task_id=source.task_id,
                description=adjustment.description if adjustment else source.description,
                amount=amount,
                currency_code=base.currency_code,
                source_kind=(
                    ForecastLineSourceKind.MANUAL
                    if adjustment
                    else ForecastLineSourceKind.AUTOMATIC
                ),
                source_type=source_type,
                source_reference_type=reference_type,
                source_reference_id=reference_id,
                source_snapshot_at=occurred_at if adjustment else base.updated_at,
                period_start=source.period_start,
                period_end=source.period_end,
                created_by=actor_id,
                created_at=occurred_at,
            )
            self._forecast_repo.add_line(line)
            decisions.append(
                self._financial_change_source_decision(
                    successor, line, source_type, reference_type, reference_id, occurred_at
                )
            )
            if adjustment:
                references.append((adjustment.impact_id, line.id))
        for adjustment in adjustments:
            if adjustment.target_line_id:
                continue
            line = ForecastLine.create(
                tenant_id=base.tenant_id,
                organization_id=base.organization_id,
                forecast_id=successor.id,
                project_id=project_id,
                cost_code_id=adjustment.cost_code_id,
                task_id=adjustment.task_id,
                description=adjustment.description,
                amount=adjustment.amount,
                currency_code=base.currency_code,
                source_kind=ForecastLineSourceKind.MANUAL,
                source_type=ForecastLineSourceType.FINANCIAL_CHANGE,
                source_reference_type="financial_change_impact",
                source_reference_id=adjustment.impact_id,
                source_snapshot_at=occurred_at,
                created_by=actor_id,
                created_at=occurred_at,
            )
            self._forecast_repo.add_line(line)
            decisions.append(
                self._financial_change_source_decision(
                    successor,
                    line,
                    ForecastLineSourceType.FINANCIAL_CHANGE,
                    "financial_change_impact",
                    adjustment.impact_id,
                    occurred_at,
                )
            )
            references.append((adjustment.impact_id, line.id))
        self._forecast_repo.add_decisions(decisions)
        self._forecast_repo.flush()
        self._record_forecast_audit("apply_financial_change", successor)
        return ApprovedFinancialSuccessorResult(
            version_id=successor.id, line_references=tuple(references)
        )


    @staticmethod
    def _financial_change_source_decision(
        forecast: ProjectForecast,
        line: ForecastLine,
        source_type: ForecastLineSourceType,
        reference_type: str,
        reference_id: str,
        occurred_at: datetime,
    ) -> ForecastSourceDecision:
        return ForecastSourceDecision.create(
            tenant_id=forecast.tenant_id,
            organization_id=forecast.organization_id,
            forecast_id=forecast.id,
            project_id=forecast.project_id,
            cost_code_id=line.cost_code_id,
            task_id=line.task_id,
            source_type=source_type,
            source_reference_type=reference_type,
            source_reference_id=reference_id,
            action=ForecastDecisionAction.INCLUDED,
            reason=(
                ForecastDecisionReason.FINANCIAL_CHANGE
                if source_type is ForecastLineSourceType.FINANCIAL_CHANGE
                else ForecastDecisionReason.BASE_FORECAST
            ),
            source_amount=line.amount,
            included_amount=line.amount,
            excluded_amount=Decimal(0),
            currency_code=forecast.currency_code,
            source_snapshot_at=line.source_snapshot_at or occurred_at,
            created_at=occurred_at,
        )


    def _apply_rejection_decision(
        self, *, forecast_id: str, rejected_by: str, expected_version: int, notes: str
    ) -> ProjectForecast:
        forecast = self._require_forecast(forecast_id)
        if forecast.row_version != expected_version:
            raise ConcurrencyError("Forecast changed since you opened it.", code="STALE_WRITE")
        now = self._clock.now()
        forecast.reject(rejected_by=rejected_by, rejected_at=now, notes=notes)
        self._forecast_repo.update(forecast, expected_row_version=expected_version)
        self._record_forecast_audit("reject", forecast)
        self._session.flush()
        self._emit_version_event(
            forecast, change_type=ForecastVersionChangeType.REJECTED, occurred_at=now
        )
        return forecast


    def _require_forecast(self, forecast_id: str) -> ProjectForecast:
        forecast = self._forecast_repo.get(forecast_id)
        if forecast is None:
            raise NotFoundError("Project forecast not found.", code="PROJECT_FORECAST_NOT_FOUND")
        return forecast


    def _require_project_permission(self, project_id: str, permission: str, operation: str) -> None:
        require_permission(self._user_session, permission, operation_label=operation)
        require_project_permission(
            self._user_session, project_id, permission, operation_label=operation
        )


    @staticmethod
    def _integrity_message(exc: IntegrityError) -> str:
        return str(getattr(exc, "orig", "") or exc).lower()


    @classmethod
    def _is_approval_conflict(cls, exc: IntegrityError) -> bool:
        message = cls._integrity_message(exc)
        return _APPROVED_CONSTRAINT in message or "project_finance_forecasts" in message


    def _record_forecast_audit(self, operation: str, forecast: ProjectForecast) -> None:
        full_operation = f"project_forecast.{operation}"
        snapshot = {
            "status": forecast.status.value,
            "revision": forecast.revision,
            "as_of_date": forecast.as_of_date.isoformat(),
            "generation_mode": forecast.generation_mode.value,
            "currency_code": forecast.currency_code,
        }
        record_audit_entry(
            self,
            operation=full_operation,
            entity_type="project_forecast",
            entity_id=forecast.id,
            entity_parent_id=forecast.project_id,
            module="project_management",
            category="FINANCIAL",
            after_data=snapshot,
            workspace_id=forecast.project_id,
            source="application",
            severity="high",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )
        record_activity(
            self,
            action=full_operation,
            entity_type="project_forecast",
            entity_id=forecast.id,
            parent_entity_id=forecast.project_id,
            module="project_management",
            workspace_id=forecast.project_id,
            details={"action": operation},
            commit=False,
        )



__all__ = ["ForecastApprovalCommands"]
