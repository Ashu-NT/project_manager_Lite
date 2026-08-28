from __future__ import annotations

from datetime import date

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.financials.models.finance_budget_facts import (
    FinancePageFacts,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_rate_facts import (
    RateCardFact,
    RateCardRequest,
    RateLineFact,
    RateLineRequest,
)
from src.core.modules.project_management.infrastructure.persistence.orm.rate_cards import (
    ProjectRateCardORM,
    RateCardLineORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.platform.infrastructure.persistence.orm.master_data.department.departments import (
    DepartmentORM,
)


_CARD_LINE_COUNT = (
    select(func.count(RateCardLineORM.id))
    .where(
        RateCardLineORM.tenant_id == ProjectRateCardORM.tenant_id,
        RateCardLineORM.organization_id == ProjectRateCardORM.organization_id,
        RateCardLineORM.rate_card_id == ProjectRateCardORM.id,
    )
    .correlate(ProjectRateCardORM)
    .scalar_subquery()
)
_CARD_SCOPE = case(
    (ProjectRateCardORM.project_id.is_(None), "organization"),
    else_="project",
)
_CARD_SORTS = {
    "title": ProjectRateCardORM.name,
    "statusLabel": ProjectRateCardORM.is_active,
    "subtitle": _CARD_SCOPE,
    "supportingText": _CARD_LINE_COUNT,
    "metaText": ProjectRateCardORM.version,
}
_LINE_SELECTOR = func.coalesce(
    ResourceORM.name,
    RateCardLineORM.role,
    RateCardLineORM.skill_code,
    DepartmentORM.name,
    RateCardLineORM.contract_reference,
    "",
)
_LINE_SORTS = {
    "title": _LINE_SELECTOR,
    "statusLabel": RateCardLineORM.rate_type,
    "subtitle": RateCardLineORM.rate_currency,
    "supportingText": RateCardLineORM.rate_amount,
    "metaText": RateCardLineORM.effective_from,
}
_RATE_TYPES = {"cost", "billing"}
_STATUSES = {"active", "inactive"}
_SCOPES = {"organization", "project"}
_EFFECTIVE_STATUSES = {"current", "future", "expired", "open_ended"}


class SqlAlchemyFinanceRateReader:
    """Bounded scalar Rate Card projections; never resolves or mutates rates."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def list_cards(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: RateCardRequest,
    ) -> FinancePageFacts[RateCardFact]:
        conditions = self._card_conditions(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
        )
        scope_filter = request.scope.strip().lower()
        if scope_filter in _SCOPES:
            conditions.append(
                ProjectRateCardORM.project_id.is_(None)
                if scope_filter == "organization"
                else ProjectRateCardORM.project_id == project_id
            )
        status = request.status.strip().lower()
        if status in _STATUSES:
            conditions.append(ProjectRateCardORM.is_active.is_(status == "active"))
        if request.search.strip():
            conditions.append(
                ProjectRateCardORM.name.ilike(f"%{request.search.strip()}%")
            )

        total = int(
            self._session.scalar(
                select(func.count(ProjectRateCardORM.id)).where(*conditions)
            )
            or 0
        )
        page, page_size, offset = _normalized_window(
            request.normalized_page, request.normalized_page_size, total
        )
        sort_key = request.normalized_sort_key
        direction = "asc" if request.sort_direction == "asc" else "desc"
        sort_expression = _CARD_SORTS[sort_key]
        ordered = sort_expression.asc() if direction == "asc" else sort_expression.desc()
        rows = self._session.execute(
            self._card_projection()
            .where(*conditions)
            .order_by(ordered, ProjectRateCardORM.id.asc())
            .offset(offset)
            .limit(page_size)
        ).all()
        return FinancePageFacts(
            items=tuple(self._card_fact(row) for row in rows),
            total=total,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=direction,
        )

    def get_card(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        rate_card_id: str,
    ) -> RateCardFact | None:
        row = self._session.execute(
            self._card_projection().where(
                *self._card_conditions(
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    project_id=project_id,
                ),
                ProjectRateCardORM.id == rate_card_id,
            )
        ).one_or_none()
        return self._card_fact(row) if row is not None else None

    def list_lines(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        rate_card_id: str,
        request: RateLineRequest,
    ) -> FinancePageFacts[RateLineFact]:
        as_of = request.as_of or date.today()
        conditions = self._line_conditions(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            rate_card_id=rate_card_id,
        )
        rate_type = request.rate_type.strip().lower()
        if rate_type in _RATE_TYPES:
            conditions.append(RateCardLineORM.rate_type == rate_type)
        status = request.status.strip().lower()
        if status in _STATUSES:
            conditions.append(RateCardLineORM.is_active.is_(status == "active"))
        effective_status = request.effective_status.strip().lower()
        if effective_status in _EFFECTIVE_STATUSES:
            conditions.extend(_effective_conditions(effective_status, as_of))
        if request.search.strip():
            pattern = f"%{request.search.strip()}%"
            conditions.append(
                or_(
                    ResourceORM.name.ilike(pattern),
                    ResourceORM.resource_code.ilike(pattern),
                    RateCardLineORM.role.ilike(pattern),
                    RateCardLineORM.skill_code.ilike(pattern),
                    DepartmentORM.name.ilike(pattern),
                    RateCardLineORM.contract_reference.ilike(pattern),
                    RateCardLineORM.rate_currency.ilike(pattern),
                    RateCardLineORM.unit.ilike(pattern),
                )
            )

        count_stmt = (
            select(func.count(RateCardLineORM.id))
            .select_from(RateCardLineORM)
            .join(ProjectRateCardORM, ProjectRateCardORM.id == RateCardLineORM.rate_card_id)
            .outerjoin(ResourceORM, _resource_join_scope())
            .outerjoin(DepartmentORM, _department_join_scope())
            .where(*conditions)
        )
        total = int(self._session.scalar(count_stmt) or 0)
        page, page_size, offset = _normalized_window(
            request.normalized_page, request.normalized_page_size, total
        )
        sort_key = request.normalized_sort_key
        direction = "asc" if request.sort_direction == "asc" else "desc"
        sort_expression = _LINE_SORTS[sort_key]
        ordered = sort_expression.asc() if direction == "asc" else sort_expression.desc()
        rows = self._session.execute(
            self._line_projection(as_of)
            .where(*conditions)
            .order_by(ordered, RateCardLineORM.id.asc())
            .offset(offset)
            .limit(page_size)
        ).all()
        return FinancePageFacts(
            items=tuple(self._line_fact(row) for row in rows),
            total=total,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=direction,
        )

    @staticmethod
    def _card_conditions(*, tenant_id: str, organization_id: str, project_id: str):
        return [
            ProjectRateCardORM.tenant_id == tenant_id,
            ProjectRateCardORM.organization_id == organization_id,
            or_(
                ProjectRateCardORM.project_id.is_(None),
                ProjectRateCardORM.project_id == project_id,
            ),
        ]

    @staticmethod
    def _line_conditions(
        *, tenant_id: str, organization_id: str, project_id: str, rate_card_id: str
    ):
        return [
            RateCardLineORM.tenant_id == tenant_id,
            RateCardLineORM.organization_id == organization_id,
            RateCardLineORM.rate_card_id == rate_card_id,
            ProjectRateCardORM.id == rate_card_id,
            ProjectRateCardORM.tenant_id == tenant_id,
            ProjectRateCardORM.organization_id == organization_id,
            or_(
                ProjectRateCardORM.project_id.is_(None),
                ProjectRateCardORM.project_id == project_id,
            ),
        ]

    @staticmethod
    def _card_projection():
        return select(
            ProjectRateCardORM.id,
            ProjectRateCardORM.name,
            ProjectRateCardORM.project_id,
            _CARD_SCOPE.label("scope"),
            ProjectRateCardORM.is_active,
            ProjectRateCardORM.card_kind,
            ProjectRateCardORM.version,
            _CARD_LINE_COUNT.label("line_count"),
            ProjectRateCardORM.created_at,
            ProjectRateCardORM.updated_at,
        )

    @staticmethod
    def _card_fact(row) -> RateCardFact:
        return RateCardFact(
            id=row.id,
            name=row.name,
            project_id=row.project_id,
            scope=row.scope,
            is_active=bool(row.is_active),
            is_legacy=row.card_kind == "legacy",
            version=int(row.version),
            line_count=int(row.line_count or 0),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _line_projection(as_of: date):
        return (
            select(
                RateCardLineORM,
                ResourceORM.resource_code,
                ResourceORM.name.label("resource_name"),
                ResourceORM.worker_type,
                DepartmentORM.name.label("department_name"),
                _effective_status_expression(as_of).label("effective_status"),
            )
            .select_from(RateCardLineORM)
            .join(ProjectRateCardORM, ProjectRateCardORM.id == RateCardLineORM.rate_card_id)
            .outerjoin(ResourceORM, _resource_join_scope())
            .outerjoin(DepartmentORM, _department_join_scope())
        )

    @staticmethod
    def _line_fact(row) -> RateLineFact:
        line = row[0]
        selector_kind, selector_label = _selector(
            line=line,
            resource_name=row.resource_name,
            department_name=row.department_name,
        )
        worker_type = getattr(row.worker_type, "value", row.worker_type) or ""
        return RateLineFact(
            id=line.id,
            rate_card_id=line.rate_card_id,
            rate_type=line.rate_type,
            origin=line.origin,
            selector_kind=selector_kind,
            selector_label=selector_label,
            resource_id=line.resource_id,
            resource_code=row.resource_code or "",
            resource_name=row.resource_name or "",
            worker_type=str(worker_type),
            role=line.role or "",
            skill_code=line.skill_code or "",
            department_id=line.department_id,
            department_name=row.department_name or "",
            customer_party_id=line.customer_party_id,
            contract_reference=line.contract_reference or "",
            effective_from=line.effective_from,
            effective_to=line.effective_to,
            effective_status=row.effective_status,
            is_active=bool(line.is_active),
            unit=line.unit,
            rate_amount=line.rate_amount,
            rate_currency=line.rate_currency,
            overtime_multiplier=line.overtime_multiplier,
            weekend_multiplier=line.weekend_multiplier,
            holiday_multiplier=line.holiday_multiplier,
            version=int(line.version),
            updated_at=line.updated_at,
        )


def _selector(*, line, resource_name: str | None, department_name: str | None):
    if line.resource_id:
        label = resource_name or line.resource_id
        if line.contract_reference:
            label = f"{label} / {line.contract_reference}"
        return "resource", label
    if line.role:
        return "role", line.role
    if line.skill_code:
        return "skill", line.skill_code
    return "department", department_name or line.department_id or ""


def _resource_join_scope():
    return and_(
        ResourceORM.id == RateCardLineORM.resource_id,
        ResourceORM.tenant_id == RateCardLineORM.tenant_id,
        ResourceORM.organization_id == RateCardLineORM.organization_id,
    )


def _department_join_scope():
    return and_(
        DepartmentORM.id == RateCardLineORM.department_id,
        DepartmentORM.tenant_id == RateCardLineORM.tenant_id,
        DepartmentORM.organization_id == RateCardLineORM.organization_id,
    )


def _effective_status_expression(as_of: date):
    return case(
        (RateCardLineORM.is_active.is_(False), "inactive"),
        (RateCardLineORM.effective_from > as_of, "future"),
        (RateCardLineORM.effective_to < as_of, "expired"),
        else_="current",
    )


def _effective_conditions(status: str, as_of: date):
    if status == "future":
        return [RateCardLineORM.effective_from > as_of]
    if status == "expired":
        return [RateCardLineORM.effective_to < as_of]
    if status == "open_ended":
        return [RateCardLineORM.effective_to.is_(None)]
    return [
        RateCardLineORM.is_active.is_(True),
        or_(RateCardLineORM.effective_from.is_(None), RateCardLineORM.effective_from <= as_of),
        or_(RateCardLineORM.effective_to.is_(None), RateCardLineORM.effective_to >= as_of),
    ]


def _normalized_window(page: int, page_size: int, total: int) -> tuple[int, int, int]:
    if total <= 0:
        return 1, page_size, 0
    last_page = max(1, (total + page_size - 1) // page_size)
    normalized_page = min(page, last_page)
    return normalized_page, page_size, (normalized_page - 1) * page_size


__all__ = ["SqlAlchemyFinanceRateReader"]
