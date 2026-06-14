from __future__ import annotations

from sqlalchemy.orm import Session

from . import category_commands, category_queries
from src.core.modules.inventory_procurement.contracts.repositories.catalog import (
    InventoryItemCategoryRepository,
)
from src.core.modules.inventory_procurement.domain.catalog.item import (
    InventoryItemCategory,
)
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.tenancy.tenant_context import (
    TenantContextService,
    require_tenant_context_service,
)


class ItemCategoryService:
    def __init__(
        self,
        session: Session,
        category_repo: InventoryItemCategoryRepository,
        *,
        organization_repo: OrganizationRepository,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        audit_service=None,
        activity_service=None,
    ) -> None:
        self._session = session
        self._category_repo = category_repo
        self._organization_repo = organization_repo
        self._tenant_context_service = require_tenant_context_service(
            tenant_context_service,
            consumer_label="ItemCategoryService",
        )
        self._user_session = user_session
        self._audit_service = audit_service
        self._activity_service = activity_service
        self._catalog_operation_label = "inventory item categories"

    def list_categories(
        self,
        *,
        active_only: bool | None = None,
        category_type: str | None = None,
    ) -> list[InventoryItemCategory]:
        return category_queries.list_categories(
            self,
            active_only=active_only,
            category_type=category_type,
        )

    def search_categories(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
        category_type: str | None = None,
        equipment_only: bool | None = None,
        project_usage_only: bool | None = None,
        maintenance_usage_only: bool | None = None,
    ) -> list[InventoryItemCategory]:
        return category_queries.search_categories(
            self,
            search_text=search_text,
            active_only=active_only,
            category_type=category_type,
            equipment_only=equipment_only,
            project_usage_only=project_usage_only,
            maintenance_usage_only=maintenance_usage_only,
        )

    def get_category(self, category_id: str) -> InventoryItemCategory:
        return category_queries.get_category(self, category_id)

    def find_category_by_code(
        self,
        category_code: str,
        *,
        active_only: bool | None = None,
    ) -> InventoryItemCategory | None:
        return category_queries.find_category_by_code(
            self,
            category_code,
            active_only=active_only,
        )

    def list_project_resource_categories(
        self,
        *,
        active_only: bool | None = True,
    ) -> list[InventoryItemCategory]:
        return category_queries.list_project_resource_categories(
            self,
            active_only=active_only,
        )

    def list_maintenance_categories(
        self,
        *,
        active_only: bool | None = True,
    ) -> list[InventoryItemCategory]:
        return category_queries.list_maintenance_categories(
            self,
            active_only=active_only,
        )

    def create_category(
        self,
        *,
        category_code: str,
        name: str,
        description: str = "",
        category_type: str = "MATERIAL",
        is_equipment: bool = False,
        supports_project_usage: bool = False,
        supports_maintenance_usage: bool = False,
        is_active: bool = True,
    ) -> InventoryItemCategory:
        return category_commands.create_category(
            self,
            category_code=category_code,
            name=name,
            description=description,
            category_type=category_type,
            is_equipment=is_equipment,
            supports_project_usage=supports_project_usage,
            supports_maintenance_usage=supports_maintenance_usage,
            is_active=is_active,
        )

    def update_category(
        self,
        category_id: str,
        *,
        category_code: str | None = None,
        name: str | None = None,
        description: str | None = None,
        category_type: str | None = None,
        is_equipment: bool | None = None,
        supports_project_usage: bool | None = None,
        supports_maintenance_usage: bool | None = None,
        is_active: bool | None = None,
        expected_version: int | None = None,
    ) -> InventoryItemCategory:
        return category_commands.update_category(
            self,
            category_id,
            category_code=category_code,
            name=name,
            description=description,
            category_type=category_type,
            is_equipment=is_equipment,
            supports_project_usage=supports_project_usage,
            supports_maintenance_usage=supports_maintenance_usage,
            is_active=is_active,
            expected_version=expected_version,
        )


__all__ = ["ItemCategoryService"]
