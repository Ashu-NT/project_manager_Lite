"""Cost item domain-to-DTO serializer."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.cost_items import FinancialCostItemDto
from src.core.modules.project_management.api.desktop.financials.formatters.money_formatter import format_money
from src.core.modules.project_management.api.desktop.financials.formatters.date_formatter import format_date
from src.core.modules.project_management.api.desktop.financials.formatters.enum_formatter import format_enum_label
from src.core.modules.project_management.api.desktop.financials.utils.cost_type_utils import coerce_cost_type
from src.core.modules.project_management.api.desktop.financials.utils.commitment_utils import commitment_status_value


def serialize_cost_item(item, *, task_lookup: dict[str, str]) -> FinancialCostItemDto:
    resolved_currency = (getattr(item, "currency_code", None) or "").strip().upper() or None
    cost_type = coerce_cost_type(getattr(item, "cost_type", None))
    task_id = str(getattr(item, "task_id", "") or "").strip() or None
    planned = float(getattr(item, "planned_amount", 0.0) or 0.0)
    committed = float(getattr(item, "committed_amount", 0.0) or 0.0)
    actual = float(getattr(item, "actual_amount", 0.0) or 0.0)
    raw_forecast = getattr(item, "forecast_amount", None)
    effective_forecast = float(raw_forecast) if raw_forecast is not None else planned
    status = commitment_status_value(item)
    return FinancialCostItemDto(
        id=item.id,
        project_id=item.project_id,
        task_id=task_id,
        task_name=task_lookup.get(task_id or "", "Not linked to a task"),
        code=str(getattr(item, "code", "") or ""),
        description=(item.description or "").strip(),
        planned_amount=planned,
        planned_amount_label=format_money(planned, resolved_currency),
        committed_amount=committed,
        committed_amount_label=format_money(committed, resolved_currency),
        actual_amount=actual,
        actual_amount_label=format_money(actual, resolved_currency),
        forecast_amount=effective_forecast,
        forecast_amount_label=format_money(effective_forecast, resolved_currency),
        commitment_status=status,
        commitment_status_label=format_enum_label(status),
        vendor_reference=str(getattr(item, "vendor_reference", None) or "").strip() or None,
        cost_type=cost_type.value,
        cost_type_label=format_enum_label(cost_type.value),
        incurred_date=getattr(item, "incurred_date", None),
        incurred_date_label=format_date(getattr(item, "incurred_date", None)),
        currency_code=resolved_currency,
        version=int(getattr(item, "version", 1) or 1),
    )


__all__ = ["serialize_cost_item"]
