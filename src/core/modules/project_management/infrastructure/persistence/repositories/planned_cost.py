from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.planned_cost import (
    ProjectPlannedCostVersionRepository,
)
from src.core.modules.project_management.domain.financials.planned_cost import (
    ProjectPlannedCostLine,
    ProjectPlannedCostVersion,
)
from src.core.modules.project_management.infrastructure.persistence.mappers.planned_cost import (
    planned_cost_line_from_orm,
    planned_cost_line_to_orm,
    planned_cost_version_from_orm,
    planned_cost_version_to_orm,
)
from src.core.modules.project_management.infrastructure.persistence.orm.planned_cost import (
    ProjectPlannedCostLineORM,
    ProjectPlannedCostVersionORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContext, TenantContextService
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.infra.persistence.db.optimistic import update_with_version_check


class _PlannedCostScope:
    session: Session
    _tenant_context_service: TenantContextService | None

    def _context(self, *, operation_label: str) -> TenantContext:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Planned-cost repository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_organization_context(
            operation_label=operation_label
        )

    @staticmethod
    def _require_entity_scope(entity, context: TenantContext) -> None:
        if (
            entity.tenant_id != context.tenant_id
            or entity.organization_id != context.organization_id
        ):
            raise BusinessRuleError(
                "Planned-cost scope does not match the active organization.",
                code="PLANNED_COST_SCOPE_MISMATCH",
            )

    def _require_project(self, project_id: str, context: TenantContext) -> None:
        project = self.session.execute(
            select(ProjectORM.id).where(
                ProjectORM.id == project_id,
                ProjectORM.tenant_id == context.tenant_id,
                ProjectORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        if project is None:
            raise NotFoundError("Project not found.")


class SqlAlchemyProjectPlannedCostVersionRepository(
    _PlannedCostScope, ProjectPlannedCostVersionRepository
):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def add(self, version: ProjectPlannedCostVersion) -> None:
        context = self._context(operation_label="create planned-cost version")
        self._require_entity_scope(version, context)
        self._require_project(version.project_id, context)
        self.session.add(planned_cost_version_to_orm(version))

    def get(self, version_id: str) -> ProjectPlannedCostVersion | None:
        context = self._context(operation_label="access planned-cost version")
        row = self.session.execute(
            select(ProjectPlannedCostVersionORM).where(
                ProjectPlannedCostVersionORM.id == version_id,
                ProjectPlannedCostVersionORM.tenant_id == context.tenant_id,
                ProjectPlannedCostVersionORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        return planned_cost_version_from_orm(row) if row else None

    def list_for_project(self, project_id: str) -> list[ProjectPlannedCostVersion]:
        context = self._context(operation_label="list planned-cost versions")
        rows = (
            self.session.execute(
                select(ProjectPlannedCostVersionORM)
                .where(
                    ProjectPlannedCostVersionORM.tenant_id == context.tenant_id,
                    ProjectPlannedCostVersionORM.organization_id == context.organization_id,
                    ProjectPlannedCostVersionORM.project_id == project_id,
                )
                .order_by(ProjectPlannedCostVersionORM.revision.desc())
            )
            .scalars()
            .all()
        )
        return [planned_cost_version_from_orm(row) for row in rows]

    def get_current_for_project(self, project_id: str) -> ProjectPlannedCostVersion | None:
        context = self._context(operation_label="access current planned-cost version")
        row = self.session.execute(
            select(ProjectPlannedCostVersionORM).where(
                ProjectPlannedCostVersionORM.tenant_id == context.tenant_id,
                ProjectPlannedCostVersionORM.organization_id == context.organization_id,
                ProjectPlannedCostVersionORM.project_id == project_id,
                ProjectPlannedCostVersionORM.status == "current",
            )
        ).scalar_one_or_none()
        return planned_cost_version_from_orm(row) if row else None

    def update(
        self, version: ProjectPlannedCostVersion, *, expected_row_version: int
    ) -> None:
        context = self._context(operation_label="update planned-cost version")
        self._require_entity_scope(version, context)
        version.row_version = update_with_version_check(
            self.session,
            ProjectPlannedCostVersionORM,
            version.id,
            expected_row_version,
            {
                "status": version.status.value,
                "superseded_by": version.superseded_by,
                "superseded_at": version.superseded_at,
                "rates_complete": version.rates_complete,
                "allocations_complete": version.allocations_complete,
                "cost_codes_complete": version.cost_codes_complete,
                "unresolved_rate_count": version.unresolved_rate_count,
                "partially_allocated_resource_count": version.partially_allocated_resource_count,
                "unclassified_line_count": version.unclassified_line_count,
                "updated_at": version.updated_at,
            },
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
            },
            not_found_message="Planned-cost version not found.",
            stale_message="Planned-cost version was updated by another user.",
        )

    def add_lines(self, lines: list[ProjectPlannedCostLine]) -> None:
        if not lines:
            return
        context = self._context(operation_label="create planned-cost lines")
        for line in lines:
            self._require_entity_scope(line, context)
        self.session.add_all(planned_cost_line_to_orm(line) for line in lines)

    def list_lines(self, version_id: str) -> list[ProjectPlannedCostLine]:
        context = self._context(operation_label="list planned-cost lines")
        rows = (
            self.session.execute(
                select(ProjectPlannedCostLineORM).where(
                    ProjectPlannedCostLineORM.version_id == version_id,
                    ProjectPlannedCostLineORM.tenant_id == context.tenant_id,
                    ProjectPlannedCostLineORM.organization_id == context.organization_id,
                )
            )
            .scalars()
            .all()
        )
        return [planned_cost_line_from_orm(row) for row in rows]

    def flush(self) -> None:
        self.session.flush()


__all__ = ["SqlAlchemyProjectPlannedCostVersionRepository"]
