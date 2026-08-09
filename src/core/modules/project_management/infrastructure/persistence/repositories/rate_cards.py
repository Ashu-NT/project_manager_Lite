from __future__ import annotations

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.rate_cards import (
    ProjectRateCardRepository,
)
from src.core.modules.project_management.domain.financials.rate_cards import (
    ProjectRateCard,
    RateCardLine,
    RateType,
)
from src.core.modules.project_management.infrastructure.persistence.mappers.rate_cards import (
    rate_card_from_orm,
    rate_card_line_from_orm,
    rate_card_line_to_orm,
    rate_card_to_orm,
)
from src.core.modules.project_management.infrastructure.persistence.orm.rate_cards import (
    ProjectRateCardORM,
    RateCardLineORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.platform.application.tenant.tenancy.tenant_context import ActiveScopeIds, TenantContextService
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.infra.persistence.db.optimistic import update_with_version_check


class _RateCardScope:
    session: Session
    _tenant_context_service: TenantContextService | None

    def _context(self, *, operation_label: str) -> ActiveScopeIds:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Rate card repository requires TenantContextService.",
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
                "Rate card scope does not match the active organization.",
                code="RATE_CARD_SCOPE_MISMATCH",
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


class SqlAlchemyProjectRateCardRepository(_RateCardScope, ProjectRateCardRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def add(self, rate_card: ProjectRateCard) -> None:
        context = self._context(operation_label="create rate card")
        self._require_entity_scope(rate_card, context)
        if rate_card.project_id:
            self._require_project(rate_card.project_id, context)
        self.session.add(rate_card_to_orm(rate_card))

    def get(self, rate_card_id: str) -> ProjectRateCard | None:
        context = self._context(operation_label="access rate card")
        row = self.session.execute(
            select(ProjectRateCardORM).where(
                ProjectRateCardORM.id == rate_card_id,
                ProjectRateCardORM.tenant_id == context.tenant_id,
                ProjectRateCardORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        return rate_card_from_orm(row) if row else None

    def list(
        self,
        *,
        project_id: str | None = None,
        include_inactive: bool = False,
    ) -> list[ProjectRateCard]:
        context = self._context(operation_label="list rate cards")
        stmt = select(ProjectRateCardORM).where(
            ProjectRateCardORM.tenant_id == context.tenant_id,
            ProjectRateCardORM.organization_id == context.organization_id,
        )
        if project_id is not None:
            stmt = stmt.where(ProjectRateCardORM.project_id == project_id)
        if not include_inactive:
            stmt = stmt.where(ProjectRateCardORM.is_active.is_(True))
        rows = self.session.execute(stmt.order_by(ProjectRateCardORM.name.asc())).scalars().all()
        return [rate_card_from_orm(row) for row in rows]

    def update(self, rate_card: ProjectRateCard) -> None:
        context = self._context(operation_label="update rate card")
        self._require_entity_scope(rate_card, context)
        if rate_card.project_id:
            self._require_project(rate_card.project_id, context)
        rate_card.version = update_with_version_check(
            self.session,
            ProjectRateCardORM,
            rate_card.id,
            rate_card.version,
            {
                "name": rate_card.name,
                "is_active": rate_card.is_active,
                "updated_at": rate_card.updated_at,
            },
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
            },
            not_found_message="Rate card not found.",
            stale_message="Rate card was updated by another user.",
        )

    def add_line(self, line: RateCardLine) -> None:
        context = self._context(operation_label="create rate card line")
        self._require_entity_scope(line, context)
        self._require_rate_card(line.rate_card_id, context)
        self.session.add(rate_card_line_to_orm(line))

    def get_line(self, line_id: str) -> RateCardLine | None:
        context = self._context(operation_label="access rate card line")
        row = self.session.execute(
            select(RateCardLineORM).where(
                RateCardLineORM.id == line_id,
                RateCardLineORM.tenant_id == context.tenant_id,
                RateCardLineORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        return rate_card_line_from_orm(row) if row else None

    def update_line(self, line: RateCardLine) -> None:
        context = self._context(operation_label="update rate card line")
        self._require_entity_scope(line, context)
        self._require_rate_card(line.rate_card_id, context)
        line.version = update_with_version_check(
            self.session,
            RateCardLineORM,
            line.id,
            line.version,
            {
                "rate_type": line.rate_type.value,
                "origin": line.origin.value,
                "resource_id": line.resource_id,
                "customer_party_id": line.customer_party_id,
                "contract_reference": line.contract_reference,
                "role": line.role,
                "skill_code": line.skill_code,
                "department_id": line.department_id,
                "effective_from": line.effective_from,
                "effective_to": line.effective_to,
                "is_active": line.is_active,
                "unit": line.unit,
                "rate_amount": line.rate_amount,
                "rate_currency": line.rate_currency,
                "overtime_multiplier": line.overtime_multiplier,
                "weekend_multiplier": line.weekend_multiplier,
                "holiday_multiplier": line.holiday_multiplier,
                "updated_at": line.updated_at,
            },
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
                "rate_card_id": line.rate_card_id,
            },
            not_found_message="Rate card line not found.",
            stale_message="Rate card line was updated by another user.",
        )

    def list_lines(
        self,
        rate_card_id: str,
        *,
        include_inactive: bool = False,
    ) -> list[RateCardLine]:
        context = self._context(operation_label="list rate card lines")
        stmt = select(RateCardLineORM).where(
            RateCardLineORM.rate_card_id == rate_card_id,
            RateCardLineORM.tenant_id == context.tenant_id,
            RateCardLineORM.organization_id == context.organization_id,
        )
        if not include_inactive:
            stmt = stmt.where(RateCardLineORM.is_active.is_(True))
        rows = self.session.execute(stmt).scalars().all()
        return [rate_card_line_from_orm(row) for row in rows]

    def list_visible_for_project(
        self,
        project_id: str,
        *,
        include_inactive: bool = False,
    ) -> list[ProjectRateCard]:
        context = self._context(operation_label="list project-visible rate cards")
        stmt = select(ProjectRateCardORM).where(
            ProjectRateCardORM.tenant_id == context.tenant_id,
            ProjectRateCardORM.organization_id == context.organization_id,
            or_(
                ProjectRateCardORM.project_id.is_(None),
                ProjectRateCardORM.project_id == project_id,
            ),
        )
        if not include_inactive:
            stmt = stmt.where(ProjectRateCardORM.is_active.is_(True))
        rows = self.session.execute(
            stmt.order_by(ProjectRateCardORM.project_id.desc(), ProjectRateCardORM.name.asc())
        ).scalars().all()
        return [rate_card_from_orm(row) for row in rows]

    def list_lines_for_cards(
        self,
        rate_card_ids: tuple[str, ...],
        *,
        include_inactive: bool = False,
    ) -> list[RateCardLine]:
        if not rate_card_ids:
            return []
        context = self._context(operation_label="list project-visible rate card lines")
        stmt = select(RateCardLineORM).where(
            RateCardLineORM.tenant_id == context.tenant_id,
            RateCardLineORM.organization_id == context.organization_id,
            RateCardLineORM.rate_card_id.in_(rate_card_ids),
        )
        if not include_inactive:
            stmt = stmt.where(RateCardLineORM.is_active.is_(True))
        rows = self.session.execute(
            stmt.order_by(RateCardLineORM.rate_card_id.asc(), RateCardLineORM.created_at.asc())
        ).scalars().all()
        return [rate_card_line_from_orm(row) for row in rows]

    def list_effective_lines(
        self,
        *,
        project_id: str | None,
        rate_type: RateType,
        unit: str,
        as_of: date,
    ) -> list[tuple[RateCardLine, ProjectRateCard]]:
        context = self._context(operation_label="resolve rate card lines")
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
                RateCardLineORM.tenant_id == context.tenant_id,
                RateCardLineORM.organization_id == context.organization_id,
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
        rows = self.session.execute(stmt).all()
        return [
            (rate_card_line_from_orm(line_row), rate_card_from_orm(card_row))
            for line_row, card_row in rows
        ]

    def list_lines_in_scope(self, *, project_id: str | None) -> list[RateCardLine]:
        context = self._context(operation_label="check rate card line overlap")
        stmt = (
            select(RateCardLineORM)
            .join(
                ProjectRateCardORM,
                ProjectRateCardORM.id == RateCardLineORM.rate_card_id,
            )
            .where(
                RateCardLineORM.tenant_id == context.tenant_id,
                RateCardLineORM.organization_id == context.organization_id,
                RateCardLineORM.is_active.is_(True),
                ProjectRateCardORM.is_active.is_(True),
            )
        )
        if project_id is None:
            stmt = stmt.where(ProjectRateCardORM.project_id.is_(None))
        else:
            stmt = stmt.where(ProjectRateCardORM.project_id == project_id)
        rows = self.session.execute(stmt).scalars().all()
        return [rate_card_line_from_orm(row) for row in rows]

    def get_or_create_legacy_card(
        self, *, tenant_id: str, organization_id: str, currency_code: str
    ) -> ProjectRateCard:
        # currency_code isn't stored on the card itself (only rate lines
        # carry a currency) — accepted here to match the call site's
        # natural shape; the caller uses it separately when it seeds the
        # actual legacy RateCardLine alongside this card.
        del currency_code
        existing = self._select_legacy_card(tenant_id, organization_id)
        if existing is not None:
            return rate_card_from_orm(existing)

        card = ProjectRateCard.create(
            tenant_id=tenant_id,
            organization_id=organization_id,
            name="Legacy Resource Rates",
            card_kind="legacy",
        )
        try:
            with self.session.begin_nested():
                self.session.add(rate_card_to_orm(card))
                self.session.flush()
        except IntegrityError:
            # Lost the race to a concurrent creator — the partial unique
            # index (tenant_id, organization_id) WHERE card_kind='legacy'
            # is what actually guarantees only one exists; re-fetch it
            # rather than treating this as a real failure.
            existing = self._select_legacy_card(tenant_id, organization_id)
            if existing is None:
                raise
            return rate_card_from_orm(existing)
        return card

    def _select_legacy_card(
        self, tenant_id: str, organization_id: str
    ) -> ProjectRateCardORM | None:
        return self.session.execute(
            select(ProjectRateCardORM).where(
                ProjectRateCardORM.tenant_id == tenant_id,
                ProjectRateCardORM.organization_id == organization_id,
                ProjectRateCardORM.card_kind == "legacy",
            )
        ).scalar_one_or_none()

    def _require_rate_card(self, rate_card_id: str, context: ActiveScopeIds) -> ProjectRateCardORM:
        row = self.session.execute(
            select(ProjectRateCardORM).where(
                ProjectRateCardORM.id == rate_card_id,
                ProjectRateCardORM.tenant_id == context.tenant_id,
                ProjectRateCardORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFoundError("Rate card not found.")
        return row


__all__ = ["SqlAlchemyProjectRateCardRepository"]
