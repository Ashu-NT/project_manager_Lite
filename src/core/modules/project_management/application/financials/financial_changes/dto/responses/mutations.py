from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FinancialChangeMutationDto:
    change_id: str
    project_id: str
    status: str
    row_version: int
    impact_id: str = ""
    impact_row_version: int = 0
    approval_request_id: str = ""
