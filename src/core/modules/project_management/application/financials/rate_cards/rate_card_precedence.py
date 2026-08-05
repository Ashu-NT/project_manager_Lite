"""ADR-PF-005 precedence policy — pure, no I/O.

Kept separate from ``RateCardResolver`` (orchestration: fetching the
resource, candidate lines, and skills) so the classification and
tie-breaking rules can be unit-tested directly against plain constructed
values, with no database or repository involved.
"""

from __future__ import annotations

from src.core.modules.project_management.domain.financials.rate_cards import (
    RateCardLine,
    RateLineOrigin,
)
from src.core.platform.common.exceptions import BusinessRuleError


def classify_line(
    line: RateCardLine,
    *,
    is_project_scoped: bool,
    resource_id: str,
    folded_resource_role: str | None,
    department_id: str | None,
    skill_codes: frozenset[str],
    customer_party_id: str | None,
    contract_reference: str | None,
) -> int | None:
    """Return this line's ADR-PF-005 precedence level (1-6) against the
    given resource/context, or ``None`` if it does not match at all.
    """
    if line.resource_id:
        if line.resource_id != resource_id:
            return None
        if not is_project_scoped:
            return 6 if line.origin == RateLineOrigin.LEGACY_SEEDED else 4
        if line.customer_party_id:
            if (
                line.customer_party_id == customer_party_id
                and line.contract_reference == contract_reference
            ):
                return 1
            return None
        return 2

    if line.role and line.role != folded_resource_role:
        return None
    if line.skill_code and line.skill_code not in skill_codes:
        return None
    if line.department_id and line.department_id != department_id:
        return None
    return 3 if is_project_scoped else 5


def select_within_level(level: int, matches: list[RateCardLine]) -> RateCardLine:
    """Pick the one line that wins within a precedence level, or raise if
    two or more are genuinely tied — never an arbitrary first match."""
    if level in (3, 5):
        max_count = max(line.specificity_dimension_count for line in matches)
        matches = [line for line in matches if line.specificity_dimension_count == max_count]
    if len(matches) > 1:
        raise BusinessRuleError(
            "Multiple rate-card lines match with equal specificity for this "
            "resource and effective date.",
            code="RATE_CARD_AMBIGUOUS_SELECTION",
        )
    return matches[0]


__all__ = ["classify_line", "select_within_level"]
