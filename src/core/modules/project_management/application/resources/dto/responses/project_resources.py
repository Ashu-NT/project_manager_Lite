from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ProjectResourceResponse:
    id: str
    project_id: str
    resource_id: str
    hourly_rate: Decimal | None = None
    currency_code: str | None = None
    planned_hours: Decimal = Decimal(0)
    is_active: bool = True
    version: int = 1


