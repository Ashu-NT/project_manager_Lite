"""ADR-PF-005 rate-card resolution — orchestration only.

"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.core.modules.project_management.application.common.clock import Clock
from src.core.modules.project_management.application.financials.rate_cards.rate_card_precedence import (
    classify_line,
    select_within_level,
)
from src.core.modules.project_management.contracts.repositories.rate_resolution import (
    RateResolutionBatch,
    RateResolutionCandidate,
    RateResolutionReader,
    ResolvedLaborRate,
    ResourceRateContext,
    UnresolvedLaborRate,
)
from src.core.modules.project_management.domain.financials.rate_cards import (
    RateCardLine,
    RateModifier,
    RateSelectionSnapshot,
    RateType,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from src.core.platform.finance.money.money import Money
from src.core.platform.finance.money.quantity import MonetaryRate, normalize_unit

_PER_RESOURCE_FAILURE_CODES = frozenset(
    {"RATE_CARD_NO_APPLICABLE_RATE", "RATE_CARD_AMBIGUOUS_SELECTION"}
)


def _fold(value: str | None) -> str | None:
    return value.strip().lower() if value else None


class RateCardResolver:
    """Selects and snapshots a rate-card line per ADR-PF-005's precedence order.
    """

    def __init__(
        self,
        *,
        reader: RateResolutionReader,
        tenant_context_service: TenantContextService,
        clock: Clock,
    ) -> None:
        self._reader = reader
        self._tenant_context_service = tenant_context_service
        self._clock = clock

    def resolve(
        self,
        *,
        tenant_id: str,
        organization_id: str,
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

        batch = self._resolve_batch(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            resource_ids=(resource_id,),
            rate_type=rate_type,
            as_of=as_of,
            unit=unit,
            customer_party_id=customer_party_id,
            contract_reference=contract_reference,
            modifier=modifier,
        )
        if batch.unresolved:
            reason = batch.unresolved[0]
            if reason.reason_code == "RESOURCE_NOT_FOUND":
                raise NotFoundError(reason.detail)
            raise BusinessRuleError(reason.detail, code=reason.reason_code)
        snapshot = batch.snapshot_for(resource_id)
        assert snapshot is not None
        return snapshot

    def resolve_many(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str | None,
        resource_ids: tuple[str, ...],
        rate_type: RateType | str,
        as_of: date,
        unit: str,
    ) -> RateResolutionBatch:
        return self._resolve_batch(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            resource_ids=resource_ids,
            rate_type=rate_type,
            as_of=as_of,
            unit=unit,
        )

    def _resolve_batch(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str | None,
        resource_ids: tuple[str, ...],
        rate_type: RateType | str,
        as_of: date,
        unit: str,
        customer_party_id: str | None = None,
        contract_reference: str | None = None,
        modifier: RateModifier | None = None,
    ) -> RateResolutionBatch:
        self._verify_context(tenant_id=tenant_id, organization_id=organization_id)

        resolved_type = RateType(rate_type)
        resolved_unit = normalize_unit(unit)
        deduped_ids = tuple(dict.fromkeys(resource_ids))

        contexts_by_id = {
            context.resource_id: context
            for context in self._reader.list_resource_contexts(
                tenant_id=tenant_id,
                organization_id=organization_id,
                resource_ids=deduped_ids,
            )
        }
        candidates = self._reader.list_candidates(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            rate_type=resolved_type,
            unit=resolved_unit,
            as_of=as_of,
        )

        resolved: list[ResolvedLaborRate] = []
        unresolved: list[UnresolvedLaborRate] = []
        for resource_id in deduped_ids:
            context = contexts_by_id.get(resource_id)
            if context is None:
                unresolved.append(
                    UnresolvedLaborRate(
                        resource_id=resource_id,
                        project_id=project_id,
                        as_of=as_of,
                        reason_code="RESOURCE_NOT_FOUND",
                        detail=f"Resource '{resource_id}' not found.",
                    )
                )
                continue
            try:
                snapshot = self._select_for_resource(
                    context,
                    candidates,
                    as_of=as_of,
                    customer_party_id=customer_party_id,
                    contract_reference=contract_reference,
                    modifier=modifier,
                )
            except BusinessRuleError as exc:
                if exc.code not in _PER_RESOURCE_FAILURE_CODES:
                    raise
                unresolved.append(
                    UnresolvedLaborRate(
                        resource_id=resource_id,
                        project_id=project_id,
                        as_of=as_of,
                        reason_code=exc.code,
                        detail=str(exc),
                    )
                )
                continue
            resolved.append(ResolvedLaborRate(resource_id=resource_id, snapshot=snapshot))

        return RateResolutionBatch(resolved=tuple(resolved), unresolved=tuple(unresolved))

    def _verify_context(self, *, tenant_id: str, organization_id: str) -> None:
        context = self._tenant_context_service.require_organization_context(
            operation_label="resolve rate card"
        )
        if context.tenant_id != tenant_id or context.organization_id != organization_id:
            raise BusinessRuleError(
                "Rate resolution tenant/organization does not match the "
                "active context.",
                code="RATE_CARD_RESOLVE_CONTEXT_MISMATCH",
            )

    def _select_for_resource(
        self,
        context: ResourceRateContext,
        candidates: tuple[RateResolutionCandidate, ...],
        *,
        as_of: date,
        customer_party_id: str | None,
        contract_reference: str | None,
        modifier: RateModifier | None,
    ) -> RateSelectionSnapshot:
        folded_role = _fold(context.role)

        buckets: dict[int, list[RateCardLine]] = {}
        card_version_by_line_id: dict[str, int] = {}
        for candidate in candidates:
            card_version_by_line_id[candidate.line.id] = candidate.card_version
            level = classify_line(
                candidate.line,
                is_project_scoped=candidate.card_project_id is not None,
                resource_id=context.resource_id,
                folded_resource_role=folded_role,
                department_id=context.department_id,
                skill_codes=context.skill_codes,
                customer_party_id=customer_party_id,
                contract_reference=contract_reference,
            )
            if level is not None:
                buckets.setdefault(level, []).append(candidate.line)

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
            f"No applicable rate for resource '{context.resource_id}' as of "
            f"{as_of.isoformat()}.",
            code="RATE_CARD_NO_APPLICABLE_RATE",
        )

    def _snapshot(
        self,
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
            resolved_at=self._clock.now(),
        )


__all__ = ["RateCardResolver"]
