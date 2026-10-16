from __future__ import annotations

from src.core.modules.project_management.application.financials.rate_cards.dto.responses.mutations import (
    FinancialRateMutationDto,
)
from src.core.modules.project_management.domain.financials.rate_cards import (
    ProjectRateCard,
    RateCardLine,
)


def map_rate_card(card: ProjectRateCard) -> FinancialRateMutationDto:
    return FinancialRateMutationDto(rate_card_id=card.id, version=card.version)


def map_rate_line(line: RateCardLine) -> FinancialRateMutationDto:
    return FinancialRateMutationDto(
        rate_card_id=line.rate_card_id, rate_line_id=line.id, version=line.version,
    )
