from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.application.common.support import (
    BUSINESS_PARTY_TYPES,
    normalize_optional_text,
)
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


__all__ = ["_validate_party_reference"]
