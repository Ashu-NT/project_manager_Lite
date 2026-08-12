"""Concrete, tenant-scoped batch reads for ADR-PF-005 rate resolution.

One dedicated adapter — not two existing write repositories partially
implementing a shared protocol. ``RateCardResolver`` depends on
``RateResolutionReader`` (``contracts/repositories/rate_resolution.py``),
never on this concrete class directly.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.finance.rate_cards.rate_resolution import (
    RateResolutionCandidate,
    ResourceRateContext,
)
from src.core.modules.project_management.domain.financials.rate_cards import RateType
from src.core.modules.project_management.infrastructure.persistence.mappers.rate_cards import (
    rate_card_line_from_orm,
)
from src.core.modules.project_management.infrastructure.persistence.orm.rate_cards import (
    ProjectRateCardORM,
    RateCardLineORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.resource import (
    ResourceORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.skills import (
    ResourceSkillORM,
)


class SqlAlchemyRateResolutionReader:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_resource_contexts(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        resource_ids: tuple[str, ...],
    ) -> tuple[ResourceRateContext, ...]:
        if not resource_ids:
            return ()
        stmt = (
            select(
                ResourceORM.id,
                ResourceORM.role,
                ResourceORM.department_id,
                ResourceSkillORM.skill_code,
            )
            .select_from(ResourceORM)
            .outerjoin(ResourceSkillORM, ResourceSkillORM.resource_id == ResourceORM.id)
            .where(
                ResourceORM.tenant_id == tenant_id,
                ResourceORM.organization_id == organization_id,
                ResourceORM.id.in_(resource_ids),
            )
        )
        rows = self._session.execute(stmt).all()

        # A resource with several skills produces several joined rows —
        # group into exactly one context per resource, not one per row.
        builders: dict[str, dict] = {}
        for resource_id, role, department_id, skill_code in rows:
            entry = builders.setdefault(
                resource_id,
                {
                    "resource_id": resource_id,
                    "role": role,
                    "department_id": department_id,
                    "skill_codes": set(),
                },
            )
            if skill_code:
                entry["skill_codes"].add(skill_code)

        return tuple(
            ResourceRateContext(
                resource_id=entry["resource_id"],
                role=entry["role"],
                department_id=entry["department_id"],
                skill_codes=frozenset(entry["skill_codes"]),
            )
            for entry in builders.values()
        )

    def list_candidates(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str | None,
        rate_type: RateType,
        unit: str,
        as_of: date,
    ) -> tuple[RateResolutionCandidate, ...]:
        card_scope = ProjectRateCardORM.project_id.is_(None)
        if project_id is not None:
            card_scope = or_(card_scope, ProjectRateCardORM.project_id == project_id)

        stmt = (
            select(RateCardLineORM, ProjectRateCardORM)
            .join(
                ProjectRateCardORM,
                ProjectRateCardORM.id == RateCardLineORM.rate_card_id,
            )
            .where(
                RateCardLineORM.tenant_id == tenant_id,
                RateCardLineORM.organization_id == organization_id,
                RateCardLineORM.rate_type == RateType(rate_type).value,
                RateCardLineORM.unit == unit,
                RateCardLineORM.is_active.is_(True),
                ProjectRateCardORM.is_active.is_(True),
                or_(
                    RateCardLineORM.effective_from.is_(None),
                    RateCardLineORM.effective_from <= as_of,
                ),
                or_(
                    RateCardLineORM.effective_to.is_(None),
                    RateCardLineORM.effective_to >= as_of,
                ),
                card_scope,
            )
        )
        rows = self._session.execute(stmt).all()
        return tuple(
            RateResolutionCandidate(
                line=rate_card_line_from_orm(line_row),
                card_project_id=card_row.project_id,
                card_version=card_row.version,
            )
            for line_row, card_row in rows
        )

    def list_candidates_for_range(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str | None,
        rate_type: RateType,
        unit: str,
        starts_on: date,
        ends_on: date,
    ) -> tuple[RateResolutionCandidate, ...]:
        card_scope = ProjectRateCardORM.project_id.is_(None)
        if project_id is not None:
            card_scope = or_(card_scope, ProjectRateCardORM.project_id == project_id)

        stmt = (
            select(RateCardLineORM, ProjectRateCardORM)
            .join(ProjectRateCardORM, ProjectRateCardORM.id == RateCardLineORM.rate_card_id)
            .where(
                RateCardLineORM.tenant_id == tenant_id,
                RateCardLineORM.organization_id == organization_id,
                RateCardLineORM.rate_type == RateType(rate_type).value,
                RateCardLineORM.unit == unit,
                RateCardLineORM.is_active.is_(True),
                ProjectRateCardORM.is_active.is_(True),
                or_(
                    RateCardLineORM.effective_from.is_(None),
                    RateCardLineORM.effective_from <= ends_on,
                ),
                or_(
                    RateCardLineORM.effective_to.is_(None),
                    RateCardLineORM.effective_to >= starts_on,
                ),
                card_scope,
            )
        )
        rows = self._session.execute(stmt).all()
        return tuple(
            RateResolutionCandidate(
                line=rate_card_line_from_orm(line_row),
                card_project_id=card_row.project_id,
                card_version=card_row.version,
            )
            for line_row, card_row in rows
        )


__all__ = ["SqlAlchemyRateResolutionReader"]
