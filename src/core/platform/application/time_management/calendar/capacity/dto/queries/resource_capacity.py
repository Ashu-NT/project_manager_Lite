"""Calendar resource capacity inputs and results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ResourceCapacityCommand:
    resource_id: str
    start_date: date | str
    end_date: date | str
    project_id: str | None = None
