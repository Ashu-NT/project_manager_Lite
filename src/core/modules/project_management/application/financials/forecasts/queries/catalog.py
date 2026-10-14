from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.contracts.repositories.finance.forecasts.forecast import (
    ProjectForecastRepository,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastLine,
    ForecastSourceDecision,
    ProjectForecast,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError


class ForecastVersionQueries(ProjectManagementModuleGuardMixin):
    """Authorized aggregate reads, independent of lifecycle command dependencies."""

    def __init__(
        self,
        *,
        forecast_repo: ProjectForecastRepository,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._forecast_repo = forecast_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

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


__all__ = ["ForecastVersionQueries"]
