from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryCategoryCreateCommand,
    InventoryCategoryUpdateCommand,
)

from .validation import (
    optional_bool,
    optional_int,
    optional_text,
    require_text,
)

def suggest_category_code(desktop_api, payload: dict[str, Any]) -> str:
    from src.core.platform.common.code_generation import CodeGenerator

    existing = {
        str(getattr(row, "category_code", "") or "").upper()
        for row in desktop_api.list_categories(active_only=None)
    }
    name = str(payload.get("name") or "").strip()
    return CodeGenerator().generate(
        "category",
        exists=lambda code: code.upper() in existing,
        name=name or None,
        use_year=not bool(name),
    )

def create_category(desktop_api, payload: dict[str, Any]) -> None:
    command = InventoryCategoryCreateCommand(
        category_code=require_text(payload, "categoryCode", "Category code is required."),
        name=require_text(payload, "name", "Category name is required."),
        description=optional_text(payload, "description") or "",
        category_type=require_text(
            payload,
            "categoryType",
            "Choose a category type before saving.",
        ),
        is_equipment=optional_bool(payload, "isEquipment", default=False),
        supports_project_usage=optional_bool(
            payload, "supportsProjectUsage", default=False
        ),
        supports_maintenance_usage=optional_bool(
            payload, "supportsMaintenanceUsage", default=False
        ),
        is_active=optional_bool(payload, "isActive", default=True),
    )
    desktop_api.create_category(command)

def update_category(desktop_api, payload: dict[str, Any]) -> None:
    command = InventoryCategoryUpdateCommand(
        category_id=require_text(
            payload, "categoryId", "Category ID is required for updates."
        ),
        category_code=require_text(payload, "categoryCode", "Category code is required."),
        name=require_text(payload, "name", "Category name is required."),
        description=optional_text(payload, "description") or "",
        category_type=require_text(
            payload,
            "categoryType",
            "Choose a category type before saving.",
        ),
        is_equipment=optional_bool(payload, "isEquipment", default=False),
        supports_project_usage=optional_bool(
            payload, "supportsProjectUsage", default=False
        ),
        supports_maintenance_usage=optional_bool(
            payload, "supportsMaintenanceUsage", default=False
        ),
        is_active=optional_bool(payload, "isActive", default=True),
        expected_version=optional_int(payload, "expectedVersion"),
    )
    desktop_api.update_category(command)

def toggle_category_active(
    desktop_api,
    category_id: str,
    expected_version: int | None = None,
) -> None:
    normalized_id = (category_id or "").strip()
    if not normalized_id:
        raise ValueError("Category ID is required to change active state.")
    desktop_api.toggle_category_active(normalized_id, expected_version=expected_version)
