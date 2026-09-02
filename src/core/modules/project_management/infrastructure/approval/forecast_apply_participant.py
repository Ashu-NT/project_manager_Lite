from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.financials.forecasts.version_service import (
    ForecastVersionService,
)
from src.core.modules.project_management.application.financials.forecasts.forecast_events import (
    ForecastVersionChanged,
    ForecastVersionChangeType,
)
from src.core.modules.project_management.infrastructure.approval._financial_decision_actor import (
    require_financial_decision_actor,
)
from src.core.platform.contract.models.approval.contracts import (
    ApprovalHandlerResult,
)
from src.core.platform.domain.approval import ApprovalRequest


@dataclass(frozen=True)
class ForecastApprovalDeps:
    forecast_service: ForecastVersionService


class ForecastApprovalParticipant:
    def apply(
        self, request: ApprovalRequest, deps: ForecastApprovalDeps
    ) -> ApprovalHandlerResult:
        actor = require_financial_decision_actor(deps.forecast_service._user_session)
        forecast = deps.forecast_service._apply_approval_decision(
            forecast_id=request.payload["forecast_id"],
            approved_by=actor,
            expected_version=request.payload["expected_version"],
            notes=request.payload.get("notes", ""),
        )
        return ApprovalHandlerResult(
            domain_events=(
                ForecastVersionChanged(
                    tenant_id=forecast.tenant_id,
                    organization_id=forecast.organization_id,
                    project_id=forecast.project_id,
                    forecast_id=forecast.id,
                    change_type=ForecastVersionChangeType.APPROVED,
                    occurred_at=forecast.approved_at or forecast.updated_at,
                ),
            )
        )

    def reject(
        self, request: ApprovalRequest, deps: ForecastApprovalDeps
    ) -> ApprovalHandlerResult:
        actor = require_financial_decision_actor(deps.forecast_service._user_session)
        forecast = deps.forecast_service._apply_rejection_decision(
            forecast_id=request.payload["forecast_id"],
            rejected_by=actor,
            expected_version=request.payload["expected_version"],
            notes=request.payload.get("notes", ""),
        )
        return ApprovalHandlerResult(
            domain_events=(
                ForecastVersionChanged(
                    tenant_id=forecast.tenant_id,
                    organization_id=forecast.organization_id,
                    project_id=forecast.project_id,
                    forecast_id=forecast.id,
                    change_type=ForecastVersionChangeType.REJECTED,
                    occurred_at=forecast.rejected_at or forecast.updated_at,
                ),
            )
        )


__all__ = ["ForecastApprovalDeps", "ForecastApprovalParticipant"]
