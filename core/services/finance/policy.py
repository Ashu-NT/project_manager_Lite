from __future__ import annotations

from datetime import date
from typing import Any

from core.interfaces import CostRepository
from core.models import CostType
from core.services.finance.helpers import is_effectively_equal


def manual_labor_raw_totals(
    *,
    cost_repo: CostRepository,
    project_id: str,
    as_of: date,
) -> dict[str, float]:
    raw = {"planned": 0.0, "committed": 0.0, "actual": 0.0}
    for item in cost_repo.list_by_project(project_id):
        if (getattr(item, "cost_type", None) or CostType.OTHER) != CostType.LABOR:
            continue
        raw["planned"] += float(getattr(item, "planned_amount", 0.0) or 0.0)
        raw["committed"] += float(getattr(item, "committed_amount", 0.0) or 0.0)
        actual = float(getattr(item, "actual_amount", 0.0) or 0.0)
        incurred = getattr(item, "incurred_date", None)
        if incurred is None or incurred <= as_of:
            raw["actual"] += actual
    return raw


def resolve_manual_labor_inclusion(
    *,
    source_rows: list[Any],
    manual_raw: dict[str, float],
) -> dict[str, bool]:
    row = next((r for r in source_rows if getattr(r, "source_key", "") == "LABOR_ADJUSTMENT"), None)
    if row is None:
        return {"planned": False, "committed": False, "actual": False}

    included: dict[str, bool] = {}
    for stage in ("planned", "committed", "actual"):
        raw_amount = float(manual_raw.get(stage, 0.0) or 0.0)
        effective_amount = float(getattr(row, stage, 0.0) or 0.0)
        included[stage] = raw_amount <= 0.0 or is_effectively_equal(raw_amount, effective_amount)
    return included


__all__ = ["manual_labor_raw_totals", "resolve_manual_labor_inclusion"]
