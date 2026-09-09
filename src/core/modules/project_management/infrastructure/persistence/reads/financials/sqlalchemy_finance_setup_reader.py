from __future__ import annotations

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased

from src.core.modules.project_management.contracts.reads.financials.models.finance_budget_facts import FinancePageFacts
from src.core.modules.project_management.contracts.reads.financials.models.finance_setup_facts import (
    FinanceSetupCostCodeFact,
    FinanceSetupCostCodeQuery,
    FinanceSetupFacts,
    FinanceSetupRestrictionFact,
    FinanceSetupRestrictionQuery,
)
from src.core.modules.project_management.infrastructure.persistence.orm.financial_configuration import (
    ProjectCostCodeORM,
    ProjectCostCodeRestrictionORM,
    ProjectFinancialProfileORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import (
    ProjectORM,
)


class SqlAlchemyFinanceSetupReader:
    """Immutable project Finance configuration projection."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def get_setup(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
    ) -> FinanceSetupFacts | None:
        default_code = aliased(ProjectCostCodeORM)
        row = self._session.execute(
            select(
                ProjectFinancialProfileORM.project_id,
                ProjectFinancialProfileORM.currency_code,
                ProjectFinancialProfileORM.status,
                ProjectFinancialProfileORM.billing_method,
                ProjectFinancialProfileORM.budget_control_mode,
                ProjectFinancialProfileORM.cost_code_policy,
                ProjectFinancialProfileORM.financial_start_date,
                ProjectFinancialProfileORM.financial_end_date,
                ProjectFinancialProfileORM.is_funded,
                ProjectFinancialProfileORM.is_billable,
                ProjectFinancialProfileORM.default_cost_code_id,
                ProjectFinancialProfileORM.version,
                default_code.code.label("default_cost_code_value"),
                default_code.name.label("default_cost_code_name"),
            )
            .join(
                ProjectORM,
                and_(
                    ProjectORM.id == ProjectFinancialProfileORM.project_id,
                    ProjectORM.tenant_id == ProjectFinancialProfileORM.tenant_id,
                    ProjectORM.organization_id
                    == ProjectFinancialProfileORM.organization_id,
                ),
            )
            .outerjoin(
                default_code,
                and_(
                    default_code.id
                    == ProjectFinancialProfileORM.default_cost_code_id,
                    default_code.tenant_id == ProjectFinancialProfileORM.tenant_id,
                    default_code.organization_id
                    == ProjectFinancialProfileORM.organization_id,
                ),
            )
            .where(
                ProjectFinancialProfileORM.tenant_id == tenant_id,
                ProjectFinancialProfileORM.organization_id == organization_id,
                ProjectFinancialProfileORM.project_id == project_id,
                ProjectORM.tenant_id == tenant_id,
                ProjectORM.organization_id == organization_id,
                ProjectORM.id == project_id,
            )
        ).one_or_none()
        if row is None:
            return None
        default_cost_code = ""
        if row.default_cost_code_value:
            default_cost_code = (
                f"{row.default_cost_code_value} - {row.default_cost_code_name}"
            )
        return FinanceSetupFacts(
            project_id=str(row.project_id),
            currency_code=str(row.currency_code),
            status=str(row.status),
            billing_method=str(row.billing_method),
            budget_control_mode=str(row.budget_control_mode),
            cost_code_policy=str(row.cost_code_policy),
            financial_start_date=row.financial_start_date,
            financial_end_date=row.financial_end_date,
            is_funded=bool(row.is_funded),
            is_billable=bool(row.is_billable),
            default_cost_code_id=(
                str(row.default_cost_code_id) if row.default_cost_code_id else None
            ),
            default_cost_code=default_cost_code,
            version=int(row.version),
        )

    def list_cost_codes(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: FinanceSetupCostCodeQuery,
    ) -> FinancePageFacts[FinanceSetupCostCodeFact]:
        parent = aliased(ProjectCostCodeORM)
        restriction = aliased(ProjectCostCodeRestrictionORM)
        profile = aliased(ProjectFinancialProfileORM)
        assigned = case((restriction.id.is_not(None), True), else_=False)
        defaulted = case((profile.default_cost_code_id == ProjectCostCodeORM.id, True), else_=False)
        from_clause = (
            ProjectCostCodeORM.__table__
            .outerjoin(
                parent,
                and_(
                    parent.id == ProjectCostCodeORM.parent_id,
                    parent.tenant_id == ProjectCostCodeORM.tenant_id,
                    parent.organization_id == ProjectCostCodeORM.organization_id,
                ),
            )
            .outerjoin(
                restriction,
                and_(
                    restriction.cost_code_id == ProjectCostCodeORM.id,
                    restriction.project_id == project_id,
                    restriction.tenant_id == ProjectCostCodeORM.tenant_id,
                    restriction.organization_id == ProjectCostCodeORM.organization_id,
                ),
            )
            .outerjoin(
                profile,
                and_(
                    profile.project_id == project_id,
                    profile.tenant_id == ProjectCostCodeORM.tenant_id,
                    profile.organization_id == ProjectCostCodeORM.organization_id,
                ),
            )
        )
        filters = [
            ProjectCostCodeORM.tenant_id == tenant_id,
            ProjectCostCodeORM.organization_id == organization_id,
        ]
        search = str(request.search or "").strip().lower()
        if search:
            pattern = f"%{search}%"
            filters.append(
                or_(
                    func.lower(ProjectCostCodeORM.code).like(pattern),
                    func.lower(ProjectCostCodeORM.name).like(pattern),
                    func.lower(ProjectCostCodeORM.description).like(pattern),
                )
            )
        status = str(request.status or "").strip().lower()
        if status == "active":
            filters.append(ProjectCostCodeORM.is_active.is_(True))
        elif status == "inactive":
            filters.append(ProjectCostCodeORM.is_active.is_(False))
        assignment_state = str(request.assignment_state or "").strip().lower()
        if assignment_state == "assigned":
            filters.append(restriction.id.is_not(None))
        elif assignment_state == "unassigned":
            filters.append(restriction.id.is_(None))

        sort_map = {
            "code": ProjectCostCodeORM.code,
            "name": ProjectCostCodeORM.name,
            "statusLabel": ProjectCostCodeORM.is_active,
            "subtitle": ProjectCostCodeORM.effective_from,
            "supportingText": parent.code,
            "metaText": ProjectCostCodeORM.updated_at,
        }
        sort_key = request.sort_key if request.sort_key in sort_map else "code"
        direction = "desc" if request.sort_direction == "desc" else "asc"
        primary = sort_map[sort_key]
        order = primary.desc().nullslast() if direction == "desc" else primary.asc().nullsfirst()
        total = int(
            self._session.execute(
                select(func.count(ProjectCostCodeORM.id))
                .select_from(from_clause)
                .where(*filters)
            ).scalar_one()
        )
        page = request.normalized_page
        page_size = request.normalized_page_size
        max_page = max(1, (total + page_size - 1) // page_size)
        page = min(page, max_page)
        rows = self._session.execute(
            select(
                ProjectCostCodeORM,
                parent.code.label("parent_code"),
                assigned.label("is_assigned"),
                defaulted.label("is_default"),
            )
            .select_from(from_clause)
            .where(*filters)
            .order_by(order, ProjectCostCodeORM.code.asc(), ProjectCostCodeORM.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return FinancePageFacts(
            items=tuple(
                FinanceSetupCostCodeFact(
                    id=str(row.ProjectCostCodeORM.id),
                    code=str(row.ProjectCostCodeORM.code),
                    name=str(row.ProjectCostCodeORM.name),
                    description=str(row.ProjectCostCodeORM.description or ""),
                    parent_id=(str(row.ProjectCostCodeORM.parent_id) if row.ProjectCostCodeORM.parent_id else None),
                    parent_code=str(row.parent_code or ""),
                    external_system=row.ProjectCostCodeORM.external_system,
                    external_reference=row.ProjectCostCodeORM.external_reference,
                    effective_from=row.ProjectCostCodeORM.effective_from,
                    effective_to=row.ProjectCostCodeORM.effective_to,
                    is_active=bool(row.ProjectCostCodeORM.is_active),
                    is_assigned=bool(row.is_assigned),
                    is_default=bool(row.is_default),
                    version=int(row.ProjectCostCodeORM.version),
                    updated_at=row.ProjectCostCodeORM.updated_at,
                )
                for row in rows
            ),
            total=total,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=direction,
        )

    def list_restrictions(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: FinanceSetupRestrictionQuery,
    ) -> FinancePageFacts[FinanceSetupRestrictionFact]:
        profile = aliased(ProjectFinancialProfileORM)
        from_clause = (
            ProjectCostCodeRestrictionORM.__table__
            .join(
                ProjectCostCodeORM,
                and_(
                    ProjectCostCodeORM.id == ProjectCostCodeRestrictionORM.cost_code_id,
                    ProjectCostCodeORM.tenant_id == ProjectCostCodeRestrictionORM.tenant_id,
                    ProjectCostCodeORM.organization_id == ProjectCostCodeRestrictionORM.organization_id,
                ),
            )
            .outerjoin(
                profile,
                and_(
                    profile.project_id == project_id,
                    profile.tenant_id == ProjectCostCodeRestrictionORM.tenant_id,
                    profile.organization_id == ProjectCostCodeRestrictionORM.organization_id,
                ),
            )
        )
        filters = [
            ProjectCostCodeRestrictionORM.tenant_id == tenant_id,
            ProjectCostCodeRestrictionORM.organization_id == organization_id,
            ProjectCostCodeRestrictionORM.project_id == project_id,
        ]
        search = str(request.search or "").strip().lower()
        if search:
            pattern = f"%{search}%"
            filters.append(
                or_(
                    func.lower(ProjectCostCodeORM.code).like(pattern),
                    func.lower(ProjectCostCodeORM.name).like(pattern),
                )
            )
        sort_map = {
            "code": ProjectCostCodeORM.code,
            "name": ProjectCostCodeORM.name,
            "statusLabel": ProjectCostCodeORM.is_active,
            "metaText": ProjectCostCodeRestrictionORM.created_at,
        }
        sort_key = request.sort_key if request.sort_key in sort_map else "code"
        direction = "desc" if request.sort_direction == "desc" else "asc"
        primary = sort_map[sort_key]
        order = primary.desc() if direction == "desc" else primary.asc()
        total = int(
            self._session.execute(
                select(func.count(ProjectCostCodeRestrictionORM.id))
                .select_from(from_clause)
                .where(*filters)
            ).scalar_one()
        )
        page = request.normalized_page
        page_size = request.normalized_page_size
        max_page = max(1, (total + page_size - 1) // page_size)
        page = min(page, max_page)
        rows = self._session.execute(
            select(
                ProjectCostCodeRestrictionORM,
                ProjectCostCodeORM.code,
                ProjectCostCodeORM.name,
                ProjectCostCodeORM.is_active,
                case((profile.default_cost_code_id == ProjectCostCodeORM.id, True), else_=False).label("is_default"),
            )
            .select_from(from_clause)
            .where(*filters)
            .order_by(order, ProjectCostCodeORM.code.asc(), ProjectCostCodeRestrictionORM.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return FinancePageFacts(
            items=tuple(
                FinanceSetupRestrictionFact(
                    id=str(row.ProjectCostCodeRestrictionORM.id),
                    cost_code_id=str(row.ProjectCostCodeRestrictionORM.cost_code_id),
                    code=str(row.code),
                    name=str(row.name),
                    is_active=bool(row.is_active),
                    is_default=bool(row.is_default),
                    created_at=row.ProjectCostCodeRestrictionORM.created_at,
                )
                for row in rows
            ),
            total=total,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=direction,
        )


__all__ = ["SqlAlchemyFinanceSetupReader"]
