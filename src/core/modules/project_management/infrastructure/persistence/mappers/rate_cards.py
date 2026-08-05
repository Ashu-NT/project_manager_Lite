from __future__ import annotations

from src.core.modules.project_management.domain.financials.rate_cards import (
    ProjectRateCard,
    RateCardLine,
    RateLineOrigin,
    RateType,
)
from src.core.modules.project_management.infrastructure.persistence.orm.rate_cards import (
    ProjectRateCardORM,
    RateCardLineORM,
)


def rate_card_to_orm(rate_card: ProjectRateCard) -> ProjectRateCardORM:
    return ProjectRateCardORM(
        id=rate_card.id,
        tenant_id=rate_card.tenant_id,
        organization_id=rate_card.organization_id,
        project_id=rate_card.project_id,
        name=rate_card.name,
        version=rate_card.version,
        is_active=rate_card.is_active,
        created_at=rate_card.created_at,
        updated_at=rate_card.updated_at,
    )


def rate_card_from_orm(row: ProjectRateCardORM) -> ProjectRateCard:
    return ProjectRateCard(
        id=row.id,
        tenant_id=row.tenant_id,
        organization_id=row.organization_id,
        project_id=row.project_id,
        name=row.name,
        version=row.version,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def rate_card_line_to_orm(line: RateCardLine) -> RateCardLineORM:
    return RateCardLineORM(
        id=line.id,
        tenant_id=line.tenant_id,
        organization_id=line.organization_id,
        rate_card_id=line.rate_card_id,
        rate_type=line.rate_type.value,
        origin=line.origin.value,
        resource_id=line.resource_id,
        customer_party_id=line.customer_party_id,
        contract_reference=line.contract_reference,
        role=line.role,
        skill_code=line.skill_code,
        department_id=line.department_id,
        effective_from=line.effective_from,
        effective_to=line.effective_to,
        is_active=line.is_active,
        unit=line.unit,
        rate_amount=line.rate_amount,
        rate_currency=line.rate_currency,
        overtime_multiplier=line.overtime_multiplier,
        weekend_multiplier=line.weekend_multiplier,
        holiday_multiplier=line.holiday_multiplier,
        version=line.version,
        created_at=line.created_at,
        updated_at=line.updated_at,
    )


def rate_card_line_from_orm(row: RateCardLineORM) -> RateCardLine:
    return RateCardLine(
        id=row.id,
        tenant_id=row.tenant_id,
        organization_id=row.organization_id,
        rate_card_id=row.rate_card_id,
        rate_type=RateType(row.rate_type),
        origin=RateLineOrigin(row.origin),
        resource_id=row.resource_id,
        customer_party_id=row.customer_party_id,
        contract_reference=row.contract_reference,
        role=row.role,
        skill_code=row.skill_code,
        department_id=row.department_id,
        effective_from=row.effective_from,
        effective_to=row.effective_to,
        is_active=row.is_active,
        unit=row.unit,
        rate_amount=row.rate_amount,
        rate_currency=row.rate_currency,
        overtime_multiplier=row.overtime_multiplier,
        weekend_multiplier=row.weekend_multiplier,
        holiday_multiplier=row.holiday_multiplier,
        version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


__all__ = [
    "rate_card_from_orm",
    "rate_card_line_from_orm",
    "rate_card_line_to_orm",
    "rate_card_to_orm",
]
