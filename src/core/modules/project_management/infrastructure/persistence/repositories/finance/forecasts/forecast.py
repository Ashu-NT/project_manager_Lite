from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.finance.forecasts.forecast import (
    ProjectForecastRepository,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastLine,
    ForecastSourceDecision,
    ProjectForecast,
)
from src.core.modules.project_management.infrastructure.persistence.mappers.forecast import (
    forecast_from_orm,
    forecast_decision_from_orm,
    forecast_decision_to_orm,
    forecast_line_from_orm,
    forecast_line_to_orm,
    forecast_to_orm,
)
from src.core.modules.project_management.infrastructure.persistence.orm.forecast import (
    ForecastLineORM,
    ForecastSourceDecisionORM,
    ProjectForecastORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.platform.application.tenant.tenancy.tenant_context import (
    ActiveScopeIds,
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.infra.persistence.db.optimistic import (
    delete_with_version_check,
    update_with_version_check,
)


class SqlAlchemyProjectForecastRepository(ProjectForecastRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _context(self, *, operation_label: str) -> ActiveScopeIds:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Forecast repository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation_label
        )

    @staticmethod
    def _require_entity_scope(entity, context: ActiveScopeIds) -> None:
        if (
            entity.tenant_id != context.tenant_id
            or entity.organization_id != context.organization_id
        ):
            raise BusinessRuleError(
                "Forecast scope does not match the active organization.",
                code="PROJECT_FORECAST_SCOPE_MISMATCH",
            )

    def _require_project(self, project_id: str, context: ActiveScopeIds) -> None:
        project = self.session.execute(
            select(ProjectORM.id).where(
                ProjectORM.id == project_id,
                ProjectORM.tenant_id == context.tenant_id,
                ProjectORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        if project is None:
            raise NotFoundError("Project not found.")

    def add(self, forecast: ProjectForecast) -> None:
        context = self._context(operation_label="create project forecast")
        self._require_entity_scope(forecast, context)
        self._require_project(forecast.project_id, context)
        self.session.add(forecast_to_orm(forecast))

    def get(self, forecast_id: str) -> ProjectForecast | None:
        context = self._context(operation_label="access project forecast")
        row = self.session.execute(
            select(ProjectForecastORM).where(
                ProjectForecastORM.id == forecast_id,
                ProjectForecastORM.tenant_id == context.tenant_id,
                ProjectForecastORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        return forecast_from_orm(row) if row else None

    def list_for_project(self, project_id: str) -> list[ProjectForecast]:
        context = self._context(operation_label="list project forecasts")
        rows = self.session.execute(
            select(ProjectForecastORM)
            .where(
                ProjectForecastORM.tenant_id == context.tenant_id,
                ProjectForecastORM.organization_id == context.organization_id,
                ProjectForecastORM.project_id == project_id,
            )
            .order_by(ProjectForecastORM.revision.desc())
        ).scalars().all()
        return [forecast_from_orm(row) for row in rows]

    def get_latest_for_project(self, project_id: str) -> ProjectForecast | None:
        context = self._context(operation_label="access latest project forecast")
        row = self.session.execute(
            select(ProjectForecastORM)
            .where(
                ProjectForecastORM.tenant_id == context.tenant_id,
                ProjectForecastORM.organization_id == context.organization_id,
                ProjectForecastORM.project_id == project_id,
            )
            .order_by(ProjectForecastORM.revision.desc())
            .limit(1)
        ).scalar_one_or_none()
        return forecast_from_orm(row) if row else None

    def get_approved_for_project(self, project_id: str) -> ProjectForecast | None:
        context = self._context(operation_label="access approved project forecast")
        row = self.session.execute(
            select(ProjectForecastORM).where(
                ProjectForecastORM.tenant_id == context.tenant_id,
                ProjectForecastORM.organization_id == context.organization_id,
                ProjectForecastORM.project_id == project_id,
                ProjectForecastORM.status == "approved",
            )
        ).scalar_one_or_none()
        return forecast_from_orm(row) if row else None

    def has_open_for_project(self, project_id: str) -> bool:
        context = self._context(operation_label="check open project forecast")
        return self.session.execute(
            select(ProjectForecastORM.id).where(
                ProjectForecastORM.tenant_id == context.tenant_id,
                ProjectForecastORM.organization_id == context.organization_id,
                ProjectForecastORM.project_id == project_id,
                ProjectForecastORM.status.in_(["draft", "submitted"]),
            )
        ).scalar_one_or_none() is not None

    def update(self, forecast: ProjectForecast, *, expected_row_version: int) -> None:
        context = self._context(operation_label="update project forecast")
        self._require_entity_scope(forecast, context)
        forecast.row_version = update_with_version_check(
            self.session,
            ProjectForecastORM,
            forecast.id,
            expected_row_version,
            {
                "name": forecast.name,
                "status": forecast.status.value,
                "submitted_by": forecast.submitted_by,
                "submitted_at": forecast.submitted_at,
                "approved_by": forecast.approved_by,
                "approved_at": forecast.approved_at,
                "rejected_by": forecast.rejected_by,
                "rejected_at": forecast.rejected_at,
                "superseded_by": forecast.superseded_by,
                "superseded_at": forecast.superseded_at,
                "notes": forecast.notes,
                "submission_notes": forecast.submission_notes,
                "approval_notes": forecast.approval_notes,
                "rejection_notes": forecast.rejection_notes,
                "updated_at": forecast.updated_at,
            },
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
            },
            not_found_message="Project forecast not found.",
            stale_message="Project forecast was updated by another user.",
        )

    def delete(self, forecast_id: str, *, expected_row_version: int) -> None:
        context = self._context(operation_label="delete project forecast")
        delete_with_version_check(
            self.session,
            ProjectForecastORM,
            forecast_id,
            expected_row_version,
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
            },
            not_found_message="Project forecast not found.",
            stale_message="Project forecast was updated by another user.",
        )

    def add_line(self, line: ForecastLine) -> None:
        context = self._context(operation_label="create project forecast line")
        self._require_entity_scope(line, context)
        self._require_forecast(line.forecast_id, context)
        self.session.add(forecast_line_to_orm(line))

    def get_line(self, line_id: str) -> ForecastLine | None:
        context = self._context(operation_label="access project forecast line")
        row = self.session.execute(
            select(ForecastLineORM).where(
                ForecastLineORM.id == line_id,
                ForecastLineORM.tenant_id == context.tenant_id,
                ForecastLineORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        return forecast_line_from_orm(row) if row else None

    def update_line(self, line: ForecastLine, *, expected_row_version: int) -> None:
        context = self._context(operation_label="update project forecast line")
        self._require_entity_scope(line, context)
        line.row_version = update_with_version_check(
            self.session,
            ForecastLineORM,
            line.id,
            expected_row_version,
            {
                "cost_code_id": line.cost_code_id,
                "task_id": line.task_id,
                "description": line.description,
                "amount": line.amount,
                "currency_code": line.currency_code,
                "source_kind": line.source_kind.value,
                "source_type": line.source_type.value,
                "source_reference_type": line.source_reference_type,
                "source_reference_id": line.source_reference_id,
                "source_snapshot_at": line.source_snapshot_at,
                "period_start": line.period_start,
                "period_end": line.period_end,
                "updated_at": line.updated_at,
            },
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
                "forecast_id": line.forecast_id,
            },
            not_found_message="Project forecast line not found.",
            stale_message="Project forecast line was updated by another user.",
        )

    def delete_line(self, line_id: str, *, expected_row_version: int) -> None:
        context = self._context(operation_label="delete project forecast line")
        delete_with_version_check(
            self.session,
            ForecastLineORM,
            line_id,
            expected_row_version,
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
            },
            not_found_message="Project forecast line not found.",
            stale_message="Project forecast line was updated by another user.",
        )

    def list_lines(self, forecast_id: str) -> list[ForecastLine]:
        context = self._context(operation_label="list project forecast lines")
        self._require_forecast(forecast_id, context)
        rows = self.session.execute(
            select(ForecastLineORM)
            .where(
                ForecastLineORM.tenant_id == context.tenant_id,
                ForecastLineORM.organization_id == context.organization_id,
                ForecastLineORM.forecast_id == forecast_id,
            )
            .order_by(
                ForecastLineORM.period_start.asc(),
                ForecastLineORM.cost_code_id.asc(),
                ForecastLineORM.id.asc(),
            )
        ).scalars().all()
        return [forecast_line_from_orm(row) for row in rows]

    def add_decisions(self, decisions: list[ForecastSourceDecision]) -> None:
        if not decisions:
            return
        context = self._context(operation_label="create forecast source decisions")
        forecast_ids = {decision.forecast_id for decision in decisions}
        if len(forecast_ids) != 1:
            raise BusinessRuleError(
                "Forecast source decisions must belong to one forecast.",
                code="PROJECT_FORECAST_DECISION_PARENT_MISMATCH",
            )
        self._require_forecast(next(iter(forecast_ids)), context)
        for decision in decisions:
            self._require_entity_scope(decision, context)
        self.session.add_all(forecast_decision_to_orm(item) for item in decisions)

    def list_decisions(self, forecast_id: str) -> list[ForecastSourceDecision]:
        context = self._context(operation_label="list forecast source decisions")
        self._require_forecast(forecast_id, context)
        rows = self.session.execute(
            select(ForecastSourceDecisionORM)
            .where(
                ForecastSourceDecisionORM.tenant_id == context.tenant_id,
                ForecastSourceDecisionORM.organization_id == context.organization_id,
                ForecastSourceDecisionORM.forecast_id == forecast_id,
            )
            .order_by(
                ForecastSourceDecisionORM.cost_code_id.asc(),
                ForecastSourceDecisionORM.task_id.asc(),
                ForecastSourceDecisionORM.source_reference_type.asc(),
                ForecastSourceDecisionORM.source_reference_id.asc(),
            )
        ).scalars().all()
        return [forecast_decision_from_orm(row) for row in rows]

    def flush(self) -> None:
        self.session.flush()

    def _require_forecast(
        self, forecast_id: str, context: ActiveScopeIds
    ) -> ProjectForecastORM:
        row = self.session.execute(
            select(ProjectForecastORM).where(
                ProjectForecastORM.id == forecast_id,
                ProjectForecastORM.tenant_id == context.tenant_id,
                ProjectForecastORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFoundError("Project forecast not found.")
        return row


__all__ = ["SqlAlchemyProjectForecastRepository"]
