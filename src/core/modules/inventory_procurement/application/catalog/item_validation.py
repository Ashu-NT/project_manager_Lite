from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.application.common.support import (
    BUSINESS_PARTY_TYPES,
    normalize_optional_text,
)
from src.core.modules.inventory_procurement.domain.catalog.item import StockItem
from src.core.platform.common.exceptions import ValidationError


def _validate_party_reference(owner: Any, party_id: str | None) -> str | None:
    normalized = normalize_optional_text(party_id)
    if not normalized:
        return None
    party = owner._party_service.get_party(normalized)
    if not party.is_active:
        raise ValidationError("Preferred party must be active.", code="INVENTORY_PARTY_INACTIVE")
    if party.party_type not in BUSINESS_PARTY_TYPES:
        raise ValidationError(
            "Preferred party must be a supplier, vendor, contractor, or service provider.",
            code="INVENTORY_PARTY_SCOPE_INVALID",
        )
    return party.id


def _validate_reorder_quantities(item: StockItem) -> None:
    if item.max_qty and item.max_qty < item.min_qty:
        raise ValidationError(
            "Maximum quantity cannot be less than minimum quantity.",
            code="INVENTORY_REORDER_RANGE_INVALID",
        )
    if item.max_qty and item.reorder_point > item.max_qty:
        raise ValidationError(
            "Reorder point cannot exceed maximum quantity.",
            code="INVENTORY_REORDER_POINT_INVALID",
        )


def _validate_uom_configuration(item: StockItem) -> None:
    if (
        item.order_uom == item.issue_uom
        and abs(float(item.order_uom_ratio) - float(item.issue_uom_ratio)) > 1e-9
    ):
        raise ValidationError(
            "Order and issue UOM factors must match when they use the same UOM code.",
            code="INVENTORY_UOM_FACTOR_CONFLICT",
        )


__all__ = [
    "_validate_party_reference",
    "_validate_reorder_quantities",
    "_validate_uom_configuration",
]
