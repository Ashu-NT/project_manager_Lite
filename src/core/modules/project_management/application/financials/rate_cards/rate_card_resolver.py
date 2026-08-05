"""ADR-PF-005 rate-card resolution — orchestration only.

Fetches the resource, its skills, and every candidate line/card pair in
one query each, then delegates classification and tie-breaking to
``rate_card_precedence`` (pure, no I/O) and returns an immutable snapshot
of what was selected. Never falls back across cost/billing rate types and
raises rather than guessing when more than one line matches with equal
specificity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from src.core.modules.project_management.application.financials.rate_cards.rate_card_precedence import (
    RateModifier,
    classify_line,
    select_within_level,
)
from src.core.modules.project_management.contracts.repositories.rate_cards import (
    ProjectRateCardRepository,
)
from src.core.modules.project_management.contracts.repositories.resource import (
    ResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.skills import (
    ResourceSkillRepository,
)
from src.core.modules.project_management.domain.financials.rate_cards import (
    RateCardLine,
    RateLineOrigin,
    RateType,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from src.core.platform.finance.money.money import Money
from src.core.platform.finance.money.quantity import MonetaryRate, normalize_unit


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _fold(value: str | None) -> str | None:
    return value.strip().lower() if value else None


@dataclass(frozen=True, slots=True)
class RateSelectionSnapshot:
    monetary_rate: MonetaryRate
    rate_card_id: str
    rate_line_id: str
    rate_card_version: int
    origin: RateLineOrigin
    precedence_level: int
    effective_date: date
    modifier_applied: RateModifier | None = None
    modifier_multiplier: Decimal | None = None
    resolved_at: datetime = field(default_factory=_utc_now)

    @property
    def modifiers_applied(self) -> Mapping[str, Decimal]:
        """Read-only view — kept for callers that want a dict-shaped
        summary; the snapshot's real, genuinely-immutable state is the
        two scalar fields above (a mutable dict field would let a caller
        mutate a supposedly-frozen snapshot in place)."""
        if self.modifier_applied is None or self.modifier_multiplier is None:
            return MappingProxyType({})
        return MappingProxyType({self.modifier_applied.value: self.modifier_multiplier})


class RateCardResolver:
    """Selects and snapshots a rate-card line per ADR-PF-005's precedence order.

    Precedence (most to least specific): (1) project + resource + customer/
    contract, (2) project + resource, (3) project + role/skill/department,
    (4) organization + resource, (5) organization + role/skill/department,
    (6) legacy ``Resource``-seeded fallback, otherwise fail. Levels 4 and 6
    share the same selection-key shape (organization-wide, resource-specific)
    and are distinguished only by ``RateCardLine.origin``.
    """

    def __init__(
        self,
        *,
        rate_card_repo: ProjectRateCardRepository,
        resource_repo: ResourceRepository,
        resource_skill_repo: ResourceSkillRepository,
        tenant_context_service: TenantContextService,
    ) -> None:
        self._rate_card_repo = rate_card_repo
        self._resource_repo = resource_repo
        self._resource_skill_repo = resource_skill_repo
        self._tenant_context_service = tenant_context_service

    def resolve(
        self,
        *,
        project_id: str | None,
        resource_id: str,
        rate_type: RateType | str,
        as_of: date,
        unit: str,
        customer_party_id: str | None = None,
        contract_reference: str | None = None,
        modifier: RateModifier | None = None,
    ) -> RateSelectionSnapshot:
        if bool(customer_party_id) != bool(contract_reference):
            raise ValidationError(
                "Customer and contract reference must be supplied together "
                "when resolving a rate.",
                code="RATE_CARD_RESOLVE_CUSTOMER_CONTRACT_INCOMPLETE",
            )

        context = self._tenant_context_service.require_organization_context(
            operation_label="resolve rate card"
        )
        resource = self._resource_repo.get(resource_id)
        if resource is None:
            raise NotFoundError("Resource not found.")
        if (
            getattr(resource, "organization_id", None) is not None
            and resource.organization_id != context.organization_id
        ):
            # Defense in depth: resource_repo.get() already scopes by the
            # ambient tenant/org context, so this should be unreachable —
            # but a resolver deciding what a resource actually costs is
            # exactly the kind of financial-correctness path that should
            # not rely on a single layer to catch a cross-org mismatch.
            raise BusinessRuleError(
                "Resource does not belong to the active organization.",
                code="RATE_CARD_RESOLVE_ORGANIZATION_MISMATCH",
            )

        resolved_type = RateType(rate_type)
        resolved_unit = normalize_unit(unit)
        skill_codes = self._resource_skill_codes(resource_id)
        folded_role = _fold(resource.role)

        candidates = self._rate_card_repo.list_effective_lines(
            project_id=project_id,
            rate_type=resolved_type,
            unit=resolved_unit,
            as_of=as_of,
        )

        buckets: dict[int, list[RateCardLine]] = {}
        card_version_by_line_id: dict[str, int] = {}
        for line, card in candidates:
            card_version_by_line_id[line.id] = card.version
            level = classify_line(
                line,
                is_project_scoped=card.project_id is not None,
                resource=resource,
                folded_resource_role=folded_role,
                skill_codes=skill_codes,
                customer_party_id=customer_party_id,
                contract_reference=contract_reference,
            )
            if level is not None:
                buckets.setdefault(level, []).append(line)

        for level in (1, 2, 3, 4, 5, 6):
            matches = buckets.get(level, [])
            if not matches:
                continue
            selected = select_within_level(level, matches)
            return self._snapshot(
                selected,
                level,
                card_version=card_version_by_line_id[selected.id],
                as_of=as_of,
                modifier=modifier,
            )

        raise BusinessRuleError(
            f"No applicable {resolved_type.value} rate for resource '{resource_id}' "
            f"as of {as_of.isoformat()}.",
            code="RATE_CARD_NO_APPLICABLE_RATE",
        )

    def _resource_skill_codes(self, resource_id: str) -> frozenset[str]:
        # Required, not optional (round-review correction): silently treating
        # a missing skill repo as "this resource has no skills" would make
        # every skill-dimensioned rate line silently fail to match and fall
        # through to a lower, wrong precedence level — a costing error with
        # no signal that anything was misconfigured. Callers that genuinely
        # never need skill-based resolution pass an explicit
        # always-empty ResourceSkillRepository, not None.
        return frozenset(
            folded
            for skill in self._resource_skill_repo.list_by_resource(resource_id)
            if (folded := _fold(getattr(skill, "skill_code", None)))
        )

    @staticmethod
    def _snapshot(
        line: RateCardLine,
        level: int,
        *,
        card_version: int,
        as_of: date,
        modifier: RateModifier | None,
    ) -> RateSelectionSnapshot:
        amount = line.rate_amount
        multiplier: Decimal | None = None
        if modifier is not None:
            multiplier = {
                RateModifier.OVERTIME: line.overtime_multiplier,
                RateModifier.WEEKEND: line.weekend_multiplier,
                RateModifier.HOLIDAY: line.holiday_multiplier,
            }[modifier]
            if multiplier is None:
                raise BusinessRuleError(
                    f"Rate line '{line.id}' has no {modifier.value} multiplier "
                    "configured — cannot honor the requested modifier.",
                    code="RATE_CARD_MODIFIER_NOT_CONFIGURED",
                )
            amount = amount * multiplier
        monetary_rate = MonetaryRate(Money.of(amount, line.rate_currency), line.unit)
        return RateSelectionSnapshot(
            monetary_rate=monetary_rate,
            rate_card_id=line.rate_card_id,
            rate_line_id=line.id,
            rate_card_version=card_version,
            origin=line.origin,
            precedence_level=level,
            effective_date=as_of,
            modifier_applied=modifier,
            modifier_multiplier=multiplier,
        )


__all__ = ["RateCardResolver", "RateSelectionSnapshot"]
