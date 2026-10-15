from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
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
from src.core.modules.project_management.application.financials.forecasts.dto.commands.forecast_lifecycle import (
    FinancialVersionedForecastCommand,
)
from src.core.modules.project_management.application.financials.forecasts.forecast_events import (
    ForecastVersionChanged,
    ForecastVersionChangeType,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.forecasts.forecast import (
    ProjectForecastRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastGenerationMode,
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
    ValidationError,
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


class ForecastLifecycleCommands(ProjectManagementModuleGuardMixin):
    """Version lifecycle and header commands."""

    def _command_actor_id(self) -> str:
        actor_id = self.current_actor_user_id
        if not actor_id:
            raise ValidationError(
                "An authenticated actor is required for Forecast commands.",
                code="FORECAST_ACTOR_REQUIRED",
            )
        return str(actor_id)

    def __init__(
        self,
        *,
        session: Session,
        forecast_repo: ProjectForecastRepository,
        project_repo: ProjectRepository,
        financial_profile_repo: ProjectFinancialProfileRepository,
        clock: CalendarClock,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None = None,
        record_event: Callable[[object], None] | None = None,
    ) -> None:
        self._session = session
        self._forecast_repo = forecast_repo
        self._project_repo = project_repo
        self._financial_profile_repo = financial_profile_repo
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._record_event = record_event


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
        self._emit_version_event(forecast, change_type=ForecastVersionChangeType.CREATED, occurred_at=now)
        return forecast


    def submit_forecast(self, command: FinancialVersionedForecastCommand) -> ProjectForecast:
        forecast_id = command.forecast_id
        submitted_by = self._command_actor_id()
        expected_version = command.expected_version
        notes = command.notes
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
        now = self._clock.now()
        forecast.submit(
            submitted_by=submitted_by,
            submitted_at=now,
            notes=notes,
        )
        self._forecast_repo.update(forecast, expected_row_version=expected_version)
        self._record_forecast_audit("submit", forecast)
        self._session.flush()
        self._emit_version_event(forecast, change_type=ForecastVersionChangeType.SUBMITTED, occurred_at=now)
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
        self._emit_version_event(
            forecast, change_type=ForecastVersionChangeType.DELETED, occurred_at=self._clock.now()
        )


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
    def _integrity_message(exc: IntegrityError) -> str:
        return str(getattr(exc, "orig", "") or exc).lower()


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

        raise exc


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



__all__ = ["ForecastLifecycleCommands"]
