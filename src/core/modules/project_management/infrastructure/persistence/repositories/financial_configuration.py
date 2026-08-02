from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.financial_configuration import (
    ProjectCostCodeRepository,
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.domain.financials.configuration import (
    ProjectCostCode,
    ProjectCostCodeRestriction,
    ProjectFinancialProfile,
)
from src.core.modules.project_management.infrastructure.persistence.mappers.financial_configuration import (
    cost_code_from_orm,
    cost_code_to_orm,
    financial_profile_from_orm,
    financial_profile_to_orm,
    restriction_from_orm,
    restriction_to_orm,
)
from src.core.modules.project_management.infrastructure.persistence.orm.financial_configuration import (
    ProjectCostCodeORM,
    ProjectCostCodeRestrictionORM,
    ProjectFinancialProfileORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.tenancy.tenant_context import TenantContext, TenantContextService
from src.infra.persistence.db.optimistic import update_with_version_check


class _FinancialConfigurationScope:
    session: Session
    _tenant_context_service: TenantContextService | None

    def _context(self, *, operation_label: str) -> TenantContext:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Financial configuration repository requires TenantContextService.",
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
                "Financial configuration scope does not match the active organization.",
                code="FINANCIAL_CONFIGURATION_SCOPE_MISMATCH",
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


class SqlAlchemyProjectFinancialProfileRepository(
    _FinancialConfigurationScope,
    ProjectFinancialProfileRepository,
):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def add(self, profile: ProjectFinancialProfile) -> None:
        context = self._context(operation_label="create project financial profile")
        self._require_entity_scope(profile, context)
        self._require_project(profile.project_id, context)
        if profile.default_cost_code_id:
            self._require_cost_code(profile.default_cost_code_id, context)
        self.session.add(financial_profile_to_orm(profile))

    def get_by_project(self, project_id: str) -> ProjectFinancialProfile | None:
        context = self._context(operation_label="access project financial profile")
        row = self.session.execute(
            select(ProjectFinancialProfileORM).where(
                ProjectFinancialProfileORM.project_id == project_id,
                ProjectFinancialProfileORM.tenant_id == context.tenant_id,
                ProjectFinancialProfileORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        return financial_profile_from_orm(row) if row else None

    def update(self, profile: ProjectFinancialProfile) -> None:
        context = self._context(operation_label="update project financial profile")
        self._require_entity_scope(profile, context)
        self._require_project(profile.project_id, context)
        if profile.default_cost_code_id:
            self._require_cost_code(profile.default_cost_code_id, context)
        profile.version = update_with_version_check(
            self.session,
            ProjectFinancialProfileORM,
            profile.id,
            profile.version,
            {
                "currency_code": profile.currency_code,
                "status": profile.status.value,
                "billing_method": profile.billing_method.value,
                "budget_control_mode": profile.budget_control_mode.value,
                "cost_code_policy": profile.cost_code_policy.value,
                "financial_start_date": profile.financial_start_date,
                "financial_end_date": profile.financial_end_date,
                "is_funded": profile.is_funded,
                "is_billable": profile.is_billable,
                "default_cost_code_id": profile.default_cost_code_id,
                "updated_at": profile.updated_at,
            },
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
                "project_id": profile.project_id,
            },
            not_found_message="Project financial profile not found.",
            stale_message="Project financial profile was updated by another user.",
        )

    def _require_cost_code(self, cost_code_id: str, context: TenantContext) -> None:
        row = self.session.execute(
            select(ProjectCostCodeORM.id).where(
                ProjectCostCodeORM.id == cost_code_id,
                ProjectCostCodeORM.tenant_id == context.tenant_id,
                ProjectCostCodeORM.organization_id == context.organization_id,
                ProjectCostCodeORM.is_active.is_(True),
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFoundError("Active project cost code not found.")


class SqlAlchemyProjectCostCodeRepository(
    _FinancialConfigurationScope,
    ProjectCostCodeRepository,
):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _base_stmt(self, *, operation_label: str):
        context = self._context(operation_label=operation_label)
        return select(ProjectCostCodeORM).where(
            ProjectCostCodeORM.tenant_id == context.tenant_id,
            ProjectCostCodeORM.organization_id == context.organization_id,
        )

    def add(self, cost_code: ProjectCostCode) -> None:
        context = self._context(operation_label="create project cost code")
        self._require_entity_scope(cost_code, context)
        if cost_code.parent_id:
            self._require_cost_code(cost_code.parent_id, context)
        self.session.add(cost_code_to_orm(cost_code))

    def get(self, cost_code_id: str) -> ProjectCostCode | None:
        row = self.session.execute(
            self._base_stmt(operation_label="access project cost code").where(
                ProjectCostCodeORM.id == cost_code_id
            )
        ).scalar_one_or_none()
        return cost_code_from_orm(row) if row else None

    def get_by_code(self, code: str) -> ProjectCostCode | None:
        row = self.session.execute(
            self._base_stmt(operation_label="access project cost code").where(
                ProjectCostCodeORM.code == str(code or "").strip().upper()
            )
        ).scalar_one_or_none()
        return cost_code_from_orm(row) if row else None

    def list(self, *, include_inactive: bool = False) -> list[ProjectCostCode]:
        stmt = self._base_stmt(operation_label="list project cost codes")
        if not include_inactive:
            stmt = stmt.where(ProjectCostCodeORM.is_active.is_(True))
        rows = self.session.execute(
            stmt.order_by(ProjectCostCodeORM.code.asc())
        ).scalars().all()
        return [cost_code_from_orm(row) for row in rows]

    def update(self, cost_code: ProjectCostCode) -> None:
        context = self._context(operation_label="update project cost code")
        self._require_entity_scope(cost_code, context)
        if cost_code.parent_id:
            self._require_cost_code(cost_code.parent_id, context)
        cost_code.version = update_with_version_check(
            self.session,
            ProjectCostCodeORM,
            cost_code.id,
            cost_code.version,
            {
                "code": cost_code.code,
                "name": cost_code.name,
                "description": cost_code.description,
                "parent_id": cost_code.parent_id,
                "external_system": cost_code.external_system,
                "external_reference": cost_code.external_reference,
                "effective_from": cost_code.effective_from,
                "effective_to": cost_code.effective_to,
                "is_active": cost_code.is_active,
                "updated_at": cost_code.updated_at,
            },
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
            },
            not_found_message="Project cost code not found.",
            stale_message="Project cost code was updated by another user.",
        )

    def add_restriction(self, restriction: ProjectCostCodeRestriction) -> None:
        context = self._context(operation_label="restrict project cost codes")
        self._require_entity_scope(restriction, context)
        self._require_project(restriction.project_id, context)
        self._require_cost_code(restriction.cost_code_id, context, active_only=True)
        self.session.add(restriction_to_orm(restriction))

    def remove_restriction(self, *, project_id: str, cost_code_id: str) -> None:
        context = self._context(operation_label="remove project cost-code restriction")
        self._require_project(project_id, context)
        self.session.execute(
            delete(ProjectCostCodeRestrictionORM).where(
                ProjectCostCodeRestrictionORM.project_id == project_id,
                ProjectCostCodeRestrictionORM.cost_code_id == cost_code_id,
                ProjectCostCodeRestrictionORM.tenant_id == context.tenant_id,
                ProjectCostCodeRestrictionORM.organization_id == context.organization_id,
            )
        )

    def list_restrictions(self, project_id: str) -> list[ProjectCostCodeRestriction]:
        context = self._context(operation_label="list project cost-code restrictions")
        self._require_project(project_id, context)
        rows = self.session.execute(
            select(ProjectCostCodeRestrictionORM).where(
                ProjectCostCodeRestrictionORM.project_id == project_id,
                ProjectCostCodeRestrictionORM.tenant_id == context.tenant_id,
                ProjectCostCodeRestrictionORM.organization_id == context.organization_id,
            )
        ).scalars().all()
        return [restriction_from_orm(row) for row in rows]

    def is_default_for_any_profile(self, cost_code_id: str) -> bool:
        context = self._context(operation_label="check project cost-code usage")
        row = self.session.execute(
            select(ProjectFinancialProfileORM.id).where(
                ProjectFinancialProfileORM.default_cost_code_id == cost_code_id,
                ProjectFinancialProfileORM.tenant_id == context.tenant_id,
                ProjectFinancialProfileORM.organization_id == context.organization_id,
            )
        ).first()
        return row is not None

    def _require_cost_code(
        self,
        cost_code_id: str,
        context: TenantContext,
        *,
        active_only: bool = False,
    ) -> ProjectCostCodeORM:
        stmt = select(ProjectCostCodeORM).where(
            ProjectCostCodeORM.id == cost_code_id,
            ProjectCostCodeORM.tenant_id == context.tenant_id,
            ProjectCostCodeORM.organization_id == context.organization_id,
        )
        if active_only:
            stmt = stmt.where(ProjectCostCodeORM.is_active.is_(True))
        row = self.session.execute(stmt).scalar_one_or_none()
        if row is None:
            raise NotFoundError("Project cost code not found.")
        return row


__all__ = [
    "SqlAlchemyProjectCostCodeRepository",
    "SqlAlchemyProjectFinancialProfileRepository",
]
