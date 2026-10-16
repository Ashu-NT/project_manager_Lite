from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FinancialRateMutationDto:
    rate_card_id: str
    rate_line_id: str = ""
    version: int = 1
