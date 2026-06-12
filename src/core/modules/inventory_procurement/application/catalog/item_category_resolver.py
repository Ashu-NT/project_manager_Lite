from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.application.catalog.catalog_context import (
    _active_organization,
)
from src.core.modules.inventory_procurement.application.common.support import (
    normalize_optional_text,
)
from src.core.modules.inventory_procurement.domain.catalog.item import (
    InventoryItemCategory,
)
from src.core.platform.common.exceptions import ValidationError


def _resolve_category_reference(
    owner: Any,
    category_code: str | None,
    *,
    allow_existing_code: str | None = None,
) -> tuple[str, InventoryItemCategory | None]:
    normalized = normalize_optional_text(category_code).upper()
    if not normalized:
        return "", None
    existing_code = normalize_optional_text(allow_existing_code).upper()
    if existing_code and normalized == existing_code:
        return normalized, _find_category_by_code_internal(owner, normalized)
    category = _find_category_by_code_internal(owner, normalized, active_only=True)
    if category is None:
        raise ValidationError(
            "Category code must reference an active inventory item category.",
            code="INVENTORY_CATEGORY_NOT_FOUND",
        )
    return category.category_code, category


def _find_category_by_code_internal(
    owner: Any,
    category_code: str,
    *,
    active_only: bool | None = None,
) -> InventoryItemCategory | None:
    if owner._category_repo is None:
        return None
    organization = _active_organization(owner)
    category = owner._category_repo.get_by_code(organization.id, category_code)
    if category is None:
        return None
    if active_only is not None and category.is_active != bool(active_only):
        return None
    return category


__all__ = ["_find_category_by_code_internal", "_resolve_category_reference"]
