from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Final

from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.forecasts.forecast_events import (
    ForecastLineChanged,
    ForecastLineChangeType,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectCostCodeRepository,
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.forecasts.forecast import (
    ProjectForecastRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    TaskRepository,
)
from src.core.modules.project_management.domain.financials.configuration import (
    CostCodePolicy,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastGenerationMode,
    ForecastLine,
    ForecastLineSourceKind,
    ForecastLineSourceType,
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


class ForecastLineCommands(ProjectManagementModuleGuardMixin):
    """Mutable financial line commands."""

    def __init__(
        self,
        *,
        session: Session,
        forecast_repo: ProjectForecastRepository,
        financial_profile_repo: ProjectFinancialProfileRepository,
        cost_code_repo: ProjectCostCodeRepository,
        task_repo: TaskRepository,
        clock: CalendarClock,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None = None,
        record_event: Callable[[object], None] | None = None,
    ) -> None:
        self._session = session
        self._forecast_repo = forecast_repo
        self._financial_profile_repo = financial_profile_repo
        self._cost_code_repo = cost_code_repo
        self._task_repo = task_repo
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._record_event = record_event


    def _emit_line_event(
        self,
        line: ForecastLine,
        forecast: ProjectForecast,
        *,
        change_type: ForecastLineChangeType,
        occurred_at: datetime,
    ) -> None:
        if self._record_event is None:
            return
        self._record_event(
            ForecastLineChanged(
                tenant_id=forecast.tenant_id,
                organization_id=forecast.organization_id,
                project_id=forecast.project_id,
                forecast_id=forecast.id,
                line_id=line.id,
                change_type=change_type,
                occurred_at=occurred_at,
            )
        )


    def add_line(
        self,
        forecast_id: str,
        *,
        cost_code_id: str,
        description: str,
        amount: Decimal,
        source_kind: ForecastLineSourceKind,
        source_type: ForecastLineSourceType,
        created_by: str,
        expected_forecast_version: int,
        task_id: str | None = None,
        source_reference_type: str | None = None,
        source_reference_id: str | None = None,
        source_snapshot_at: datetime | None = None,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> ForecastLine:
        forecast = self._require_mutable_forecast(
            forecast_id, expected_forecast_version, "add project forecast line"
        )
        self._require_mode_supports(forecast, source_kind)
        self._require_eligible_cost_code(forecast.project_id, cost_code_id)
        if task_id:
            self._require_task_in_project(task_id, forecast.project_id)
        now = self._clock.now()
        line = ForecastLine.create(
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
            created_by=created_by,
            created_at=now,
        )
        self._forecast_repo.add_line(line)
        forecast.touch(updated_at=now)
        self._forecast_repo.update(
            forecast, expected_row_version=expected_forecast_version
        )
        self._record_line_audit("add", line, forecast)
        self._session.flush()
        self._emit_line_event(line, forecast, change_type=ForecastLineChangeType.ADDED, occurred_at=now)
        return line


    def update_line(
        self,
        line_id: str,
        *,
        expected_line_version: int,
        expected_forecast_version: int,
        cost_code_id: str | None = None,
        task_id: str | None | _Unset = _UNSET,
        description: str | None = None,
        amount: Decimal | None = None,
        period_start: date | None | _Unset = _UNSET,
        period_end: date | None | _Unset = _UNSET,
    ) -> ForecastLine:
        line = self._require_line(line_id)
        forecast = self._require_mutable_forecast(
            line.forecast_id, expected_forecast_version, "update project forecast line"
        )
        if line.row_version != expected_line_version:
            raise ConcurrencyError("Forecast line changed since you opened it.", code="STALE_WRITE")
        original = (
            line.cost_code_id, line.task_id, line.description, line.amount,
            line.period_start, line.period_end,
        )
        if cost_code_id is not None and cost_code_id != line.cost_code_id:
            self._require_eligible_cost_code(forecast.project_id, cost_code_id)
            line.cost_code_id = cost_code_id
        if task_id is not _UNSET:
            if task_id is not None:
                self._require_task_in_project(task_id, forecast.project_id)
            line.task_id = task_id
        if description is not None:
            line.description = description
        if amount is not None:
            if amount < 0:
                raise BusinessRuleError(
                    "Forecast line amount cannot be negative.",
                    code="PROJECT_FORECAST_LINE_AMOUNT_INVALID",
                )
            line.amount = Decimal(str(amount))
        if period_start is not _UNSET:
            line.period_start = period_start
        if period_end is not _UNSET:
            line.period_end = period_end
        self._validate_period(line.period_start, line.period_end)
        changed = (
            line.cost_code_id, line.task_id, line.description, line.amount,
            line.period_start, line.period_end,
        ) != original
        if not changed:
            # True no-op: no write, audit, event, or version bump.
            return line
        now = self._clock.now()
        line.updated_at = now
        self._forecast_repo.update_line(line, expected_row_version=expected_line_version)
        forecast.touch(updated_at=now)
        self._forecast_repo.update(
            forecast, expected_row_version=expected_forecast_version
        )
        self._record_line_audit("update", line, forecast)
        self._session.flush()
        self._emit_line_event(line, forecast, change_type=ForecastLineChangeType.UPDATED, occurred_at=now)
        return line


    def delete_line(
        self,
        line_id: str,
        *,
        expected_line_version: int,
        expected_forecast_version: int,
    ) -> None:
        line = self._require_line(line_id)
        forecast = self._require_mutable_forecast(
            line.forecast_id, expected_forecast_version, "delete project forecast line"
        )
        self._forecast_repo.delete_line(
            line_id, expected_row_version=expected_line_version
        )
        now = self._clock.now()
        forecast.touch(updated_at=now)
        self._forecast_repo.update(
            forecast, expected_row_version=expected_forecast_version
        )
        self._record_line_audit("delete", line, forecast)
        self._session.flush()
        self._emit_line_event(line, forecast, change_type=ForecastLineChangeType.REMOVED, occurred_at=now)


    def _require_mutable_forecast(
        self, forecast_id: str, expected_version: int, operation: str
    ) -> ProjectForecast:
        forecast = self._require_forecast(forecast_id)
        self._require_project_permission(forecast.project_id, "forecast.manage", operation)
        forecast.ensure_mutable()
        if forecast.row_version != expected_version:
            raise ConcurrencyError("Forecast changed since you opened it.", code="STALE_WRITE")
        return forecast


    def _require_forecast(self, forecast_id: str) -> ProjectForecast:
        forecast = self._forecast_repo.get(forecast_id)
        if forecast is None:
            raise NotFoundError("Project forecast not found.", code="PROJECT_FORECAST_NOT_FOUND")
        return forecast


    def _require_line(self, line_id: str) -> ForecastLine:
        line = self._forecast_repo.get_line(line_id)
        if line is None:
            raise NotFoundError(
                "Project forecast line not found.",
                code="PROJECT_FORECAST_LINE_NOT_FOUND",
            )
        return line


    def _require_project_permission(self, project_id: str, permission: str, operation: str) -> None:
        require_permission(self._user_session, permission, operation_label=operation)
        require_project_permission(
            self._user_session, project_id, permission, operation_label=operation
        )


    @staticmethod
    def _require_mode_supports(
        forecast: ProjectForecast, source_kind: ForecastLineSourceKind
    ) -> None:
        if forecast.generation_mode == ForecastGenerationMode.HYBRID:
            return
        if forecast.generation_mode.value != source_kind.value:
            raise BusinessRuleError(
                "Forecast line source kind does not match the forecast generation mode.",
                code="PROJECT_FORECAST_GENERATION_MODE_MISMATCH",
            )


    def _require_eligible_cost_code(self, project_id: str, cost_code_id: str) -> None:
        cost_code = self._cost_code_repo.get(cost_code_id)
        if cost_code is None:
            raise NotFoundError(
                "Cost code not found.",
                code="PROJECT_FORECAST_LINE_COST_CODE_NOT_FOUND",
            )
        if not cost_code.is_effective_on(self._clock.today()):
            raise BusinessRuleError(
                "Cost code is not active or effective for this date.",
                code="PROJECT_FORECAST_LINE_COST_CODE_INACTIVE",
            )
        profile = self._financial_profile_repo.get_by_project(project_id)
        if profile and profile.cost_code_policy == CostCodePolicy.RESTRICTED:
            allowed = {
                item.cost_code_id
                for item in self._cost_code_repo.list_restrictions(project_id)
            }
            if cost_code_id not in allowed:
                raise BusinessRuleError(
                    "This cost code is not permitted for this project.",
                    code="PROJECT_FORECAST_LINE_COST_CODE_NOT_PERMITTED",
                )


    def _require_task_in_project(self, task_id: str, project_id: str) -> None:
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        if task.project_id != project_id:
            raise BusinessRuleError(
                "Task does not belong to this project.",
                code="PROJECT_FORECAST_LINE_TASK_PROJECT_MISMATCH",
            )


    @staticmethod
    def _validate_period(period_start: date | None, period_end: date | None) -> None:
        if (period_start is None) != (period_end is None):
            raise BusinessRuleError(
                "Forecast line period start and end must be provided together.",
                code="PROJECT_FORECAST_LINE_PERIOD_INCOMPLETE",
            )
        if period_start and period_end and period_end < period_start:
            raise BusinessRuleError(
                "Forecast line period end cannot precede period start.",
                code="PROJECT_FORECAST_LINE_PERIOD_INVALID",
            )


    def _record_line_audit(
        self, operation: str, line: ForecastLine, forecast: ProjectForecast
    ) -> None:
        full_operation = f"project_forecast_line.{operation}"
        snapshot = {
            "amount": str(line.amount),
            "currency_code": line.currency_code,
            "cost_code_id": line.cost_code_id,
            "task_id": line.task_id,
            "source_kind": line.source_kind.value,
            "source_type": line.source_type.value,
            "source_reference_type": line.source_reference_type,
            "source_reference_id": line.source_reference_id,
        }
        record_audit_entry(
            self,
            operation=full_operation,
            entity_type="project_forecast_line",
            entity_id=line.id,
            entity_parent_id=forecast.id,
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
            entity_type="project_forecast_line",
            entity_id=line.id,
            parent_entity_id=forecast.id,
            module="project_management",
            workspace_id=forecast.project_id,
            details={"action": operation},
            commit=False,
        )



__all__ = ["ForecastLineCommands"]
