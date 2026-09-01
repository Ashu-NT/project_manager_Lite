from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.modules.project_management.application.common.clock import Clock
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
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
from src.core.modules.project_management.domain.financials.configuration import CostCodePolicy
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastGenerationMode,
    ForecastLine,
    ForecastLineSourceKind,
    ForecastLineSourceType,
    ForecastStatus,
    ForecastSourceDecision,
    ProjectForecast,
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


_OPEN_CONSTRAINT = "uq_pf_forecasts_one_open_per_project"
_APPROVED_CONSTRAINT = "uq_pf_forecasts_one_approved_per_project"
_REVISION_CONSTRAINT = "uq_pf_forecast_project_revision"
_UNSET = object()


class ForecastVersionService(ProjectManagementModuleGuardMixin):
    """Governed lifecycle for reproducible forecast versions and ETC lines."""

    def __init__(
        self,
        *,
        session: Session,
        forecast_repo: ProjectForecastRepository,
        project_repo: ProjectRepository,
        financial_profile_repo: ProjectFinancialProfileRepository,
        cost_code_repo: ProjectCostCodeRepository,
        task_repo: TaskRepository,
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
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service

    def get_forecast(self, forecast_id: str) -> ProjectForecast:
        require_permission(self._user_session, "finance.read", operation_label="view project forecast")
        forecast = self._require_forecast(forecast_id)
        require_project_permission(
            self._user_session,
            forecast.project_id,
            "finance.read",
            operation_label="view project forecast",
        )
        return forecast

    def list_forecasts(self, project_id: str) -> list[ProjectForecast]:
        self._require_project_permission(project_id, "finance.read", "list project forecasts")
        return self._forecast_repo.list_for_project(project_id)

    def get_approved_forecast(self, project_id: str) -> ProjectForecast | None:
        self._require_project_permission(project_id, "finance.read", "view approved project forecast")
        return self._forecast_repo.get_approved_for_project(project_id)

    def list_lines(self, forecast_id: str) -> list[ForecastLine]:
        forecast = self.get_forecast(forecast_id)
        return self._forecast_repo.list_lines(forecast.id)

    def list_source_decisions(self, forecast_id: str) -> list[ForecastSourceDecision]:
        forecast = self.get_forecast(forecast_id)
        return self._forecast_repo.list_decisions(forecast.id)

    def create_forecast(
        self,
        project_id: str,
        *,
        name: str,
        as_of_date: date,
        generation_mode: ForecastGenerationMode,
        created_by: str,
        notes: str = "",
    ) -> ProjectForecast:
        self._require_project_permission(project_id, "forecast.manage", "create project forecast")
        if self._project_repo.get(project_id) is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        profile = self._financial_profile_repo.get_by_project(project_id)
        if profile is None:
            raise NotFoundError(
                "Project financial profile not found; configure finance before creating a forecast.",
                code="PROJECT_FINANCIAL_PROFILE_NOT_FOUND",
            )
        context = self._require_context("create project forecast")
        if self._forecast_repo.has_open_for_project(project_id):
            raise BusinessRuleError(
                "A draft or submitted forecast already exists for this project.",
                code="PROJECT_FORECAST_OPEN_VERSION_EXISTS",
            )
        latest = self._forecast_repo.get_latest_for_project(project_id)
        now = self._clock.now()
        forecast = ProjectForecast.create(
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            project_id=project_id,
            name=name,
            currency_code=profile.currency_code,
            as_of_date=as_of_date,
            generation_mode=generation_mode,
            created_by=created_by,
            revision=(latest.revision + 1) if latest else 1,
            notes=notes,
            created_at=now,
        )
        try:
            with self._session.begin_nested():
                self._forecast_repo.add(forecast)
                self._forecast_repo.flush()
        except IntegrityError as exc:
            self._translate_create_conflict(exc)
        self._record_forecast_audit("create", forecast)
        self._session.flush()
        return forecast

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
        return line

    def update_line(
        self,
        line_id: str,
        *,
        expected_line_version: int,
        expected_forecast_version: int,
        cost_code_id: str | None = None,
        task_id: str | None | object = _UNSET,
        description: str | None = None,
        amount: Decimal | None = None,
        period_start: date | None | object = _UNSET,
        period_end: date | None | object = _UNSET,
    ) -> ForecastLine:
        line = self._require_line(line_id)
        forecast = self._require_mutable_forecast(
            line.forecast_id, expected_forecast_version, "update project forecast line"
        )
        if line.row_version != expected_line_version:
            raise ConcurrencyError("Forecast line changed since you opened it.", code="STALE_WRITE")
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
        now = self._clock.now()
        line.updated_at = now
        self._forecast_repo.update_line(line, expected_row_version=expected_line_version)
        forecast.touch(updated_at=now)
        self._forecast_repo.update(
            forecast, expected_row_version=expected_forecast_version
        )
        self._record_line_audit("update", line, forecast)
        self._session.flush()
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
        forecast.touch(updated_at=self._clock.now())
        self._forecast_repo.update(
            forecast, expected_row_version=expected_forecast_version
        )
        self._record_line_audit("delete", line, forecast)
        self._session.flush()

    def submit_forecast(
        self,
        forecast_id: str,
        *,
        submitted_by: str,
        expected_version: int,
        notes: str = "",
    ) -> ProjectForecast:
        forecast = self._require_mutable_forecast(
            forecast_id, expected_version, "submit project forecast"
        )
        if (
            not self._forecast_repo.list_lines(forecast_id)
            and not self._forecast_repo.list_decisions(forecast_id)
        ):
            raise BusinessRuleError(
                "Cannot submit a forecast without ETC lines or generation evidence.",
                code="PROJECT_FORECAST_EMPTY",
            )
        forecast.submit(
            submitted_by=submitted_by,
            submitted_at=self._clock.now(),
            notes=notes,
        )
        self._forecast_repo.update(forecast, expected_row_version=expected_version)
        self._record_forecast_audit("submit", forecast)
        self._session.flush()
        return forecast

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
        now = self._clock.now()
        previous = self._forecast_repo.get_approved_for_project(forecast.project_id)
        try:
            with self._session.begin_nested():
                if previous is not None:
                    previous_version = previous.row_version
                    previous.supersede(superseded_by=approved_by, superseded_at=now)
                    self._forecast_repo.update(
                        previous, expected_row_version=previous_version
                    )
                    self._forecast_repo.flush()
                forecast.approve(approved_by=approved_by, approved_at=now, notes=notes)
                self._forecast_repo.update(
                    forecast, expected_row_version=expected_version
                )
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
        return forecast

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
        forecast.reject(
            rejected_by=rejected_by,
            rejected_at=self._clock.now(),
            notes=notes,
        )
        self._forecast_repo.update(forecast, expected_row_version=expected_version)
        self._record_forecast_audit("reject", forecast)
        self._session.flush()
        return forecast

    def delete_forecast(self, forecast_id: str, *, expected_version: int) -> None:
        forecast = self._require_mutable_forecast(
            forecast_id, expected_version, "delete project forecast"
        )
        self._forecast_repo.delete(
            forecast_id, expected_row_version=expected_version
        )
        self._record_forecast_audit("delete", forecast)
        self._session.flush()

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

    def _require_context(self, operation: str):
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                f"Active organization context is required to {operation}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation
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

    @staticmethod
    def _integrity_message(exc: IntegrityError) -> str:
        return str(getattr(exc, "orig", "") or exc).lower()

    @classmethod
    def _is_approval_conflict(cls, exc: IntegrityError) -> bool:
        message = cls._integrity_message(exc)
        return _APPROVED_CONSTRAINT in message or "project_finance_forecasts" in message

    def _translate_create_conflict(self, exc: IntegrityError) -> None:
        message = self._integrity_message(exc)
        if _REVISION_CONSTRAINT in message or "revision" in message:
            raise ConcurrencyError(
                "Another forecast revision was created concurrently. Refresh and try again.",
                code="PROJECT_FORECAST_REVISION_CONFLICT",
            ) from exc
        if _OPEN_CONSTRAINT in message or "project_finance_forecasts" in message:
            raise BusinessRuleError(
                "A draft or submitted forecast already exists for this project.",
                code="PROJECT_FORECAST_OPEN_VERSION_EXISTS",
            ) from exc
        raise

    def _record_forecast_audit(self, operation: str, forecast: ProjectForecast) -> None:
        record_audit_entry(
            self,
            operation=f"project_forecast.{operation}",
            entity_type="project_forecast",
            entity_id=forecast.id,
            entity_parent_id=forecast.project_id,
            module="project_management",
            old_value=None,
            new_value=json.dumps(
                {
                    "status": forecast.status.value,
                    "revision": forecast.revision,
                    "as_of_date": forecast.as_of_date.isoformat(),
                    "generation_mode": forecast.generation_mode.value,
                    "currency_code": forecast.currency_code,
                },
                sort_keys=True,
            ),
            workspace_id=forecast.project_id,
            source="application",
            severity="high",
            compliance_tag="financial",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )

    def _record_line_audit(
        self, operation: str, line: ForecastLine, forecast: ProjectForecast
    ) -> None:
        record_audit_entry(
            self,
            operation=f"project_forecast_line.{operation}",
            entity_type="project_forecast_line",
            entity_id=line.id,
            entity_parent_id=forecast.id,
            module="project_management",
            old_value=None,
            new_value=json.dumps(
                {
                    "amount": str(line.amount),
                    "currency_code": line.currency_code,
                    "cost_code_id": line.cost_code_id,
                    "task_id": line.task_id,
                    "source_kind": line.source_kind.value,
                    "source_type": line.source_type.value,
                    "source_reference_type": line.source_reference_type,
                    "source_reference_id": line.source_reference_id,
                },
                sort_keys=True,
            ),
            workspace_id=forecast.project_id,
            source="application",
            severity="high",
            compliance_tag="financial",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )

__all__ = ["ForecastVersionService"]
