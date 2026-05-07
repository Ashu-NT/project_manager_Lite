from __future__ import annotations

from src.core.modules.inventory_procurement.api.desktop.catalog.models import (
    InventoryCategoryCreateCommand,
    InventoryCategoryDesktopDto,
    InventoryCategoryUpdateCommand,
)
from src.core.modules.inventory_procurement.api.desktop.catalog.serializers import (
    serialize_category,
)


class InventoryCatalogDesktopCategoryMixin:
    def list_categories(
        self,
        *,
        active_only: bool | None = None,
        category_type: str | None = None,
        search_text: str = "",
        equipment_only: bool | None = None,
        project_usage_only: bool | None = None,
        maintenance_usage_only: bool | None = None,
    ) -> tuple[InventoryCategoryDesktopDto, ...]:
        if self._category_service is None:
            return ()
        if (
            search_text
            or equipment_only is not None
            or project_usage_only is not None
            or maintenance_usage_only is not None
        ):
            categories = self._category_service.search_categories(
                search_text=search_text,
                active_only=active_only,
                category_type=category_type,
                equipment_only=equipment_only,
                project_usage_only=project_usage_only,
                maintenance_usage_only=maintenance_usage_only,
            )
        else:
            categories = self._category_service.list_categories(
                active_only=active_only,
                category_type=category_type,
            )
        ordered = sorted(
            categories,
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "category_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_category(row) for row in ordered)

    def create_category(
        self,
        command: InventoryCategoryCreateCommand,
    ) -> InventoryCategoryDesktopDto:
        service = self._require_category_service()
        category = service.create_category(
            category_code=command.category_code,
            name=command.name,
            description=command.description,
            category_type=command.category_type,
            is_equipment=command.is_equipment,
            supports_project_usage=command.supports_project_usage,
            supports_maintenance_usage=command.supports_maintenance_usage,
            is_active=command.is_active,
        )
        return serialize_category(category)

    def update_category(
        self,
        command: InventoryCategoryUpdateCommand,
    ) -> InventoryCategoryDesktopDto:
        service = self._require_category_service()
        category = service.update_category(
            command.category_id,
            category_code=command.category_code,
            name=command.name,
            description=command.description,
            category_type=command.category_type,
            is_equipment=command.is_equipment,
            supports_project_usage=command.supports_project_usage,
            supports_maintenance_usage=command.supports_maintenance_usage,
            is_active=command.is_active,
            expected_version=command.expected_version,
        )
        return serialize_category(category)

    def toggle_category_active(
        self,
        category_id: str,
        *,
        expected_version: int | None = None,
    ) -> InventoryCategoryDesktopDto:
        service = self._require_category_service()
        category = service.get_category(category_id)
        updated = service.update_category(
            category_id,
            is_active=not bool(getattr(category, "is_active", True)),
            expected_version=expected_version,
        )
        return serialize_category(updated)


__all__ = ["InventoryCatalogDesktopCategoryMixin"]
