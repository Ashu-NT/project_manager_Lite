from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.modules.inventory_procurement.domain import InventoryItemCategory
from core.modules.inventory_procurement.interfaces import InventoryItemCategoryRepository
from core.modules.inventory_procurement.support import (
    normalize_inventory_code,
    normalize_inventory_name,
    normalize_item_category_type,
    normalize_optional_text,
)
from core.platform.audit.helpers import record_audit
from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from core.platform.common.interfaces import OrganizationRepository
from core.platform.notifications.domain_events import domain_events
from core.platform.org.domain import Organization


class ItemCategoryService:
    def __init__(
        self,
        session: Session,
        category_repo: InventoryItemCategoryRepository,
        *,
        organization_repo: OrganizationRepository,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._category_repo = category_repo
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._audit_service = audit_service

    def list_categories(
        self,
        *,
        active_only: bool | None = None,
        category_type: str | None = None,
    ) -> list[InventoryItemCategory]:
        self._require_read("list inventory item categories")
        organization = self._active_organization()
        resolved_type = normalize_item_category_type(category_type) if category_type else None
        return self._category_repo.list_for_organization(
            organization.id,
            active_only=active_only,
            category_type=resolved_type,
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
        normalized_search = normalize_optional_text(search_text).lower()
        rows = self.list_categories(active_only=active_only, category_type=category_type)
        filtered: list[InventoryItemCategory] = []
        for category in rows:
            if equipment_only is True and not category.is_equipment:
                continue
            if equipment_only is False and category.is_equipment:
                continue
            if project_usage_only is True and not category.supports_project_usage:
                continue
            if project_usage_only is False and category.supports_project_usage:
                continue
            if maintenance_usage_only is True and not category.supports_maintenance_usage:
                continue
            if maintenance_usage_only is False and category.supports_maintenance_usage:
                continue
            if normalized_search:
                haystack = " ".join(
                    filter(
                        None,
                        [
                            category.category_code,
                            category.name,
                            category.description,
                            category.category_type,
                        ],
                    )
                ).lower()
                if normalized_search not in haystack:
                    continue
            filtered.append(category)
        return filtered

    def get_category(self, category_id: str) -> InventoryItemCategory:
        self._require_read("view inventory item category")
        organization = self._active_organization()
        category = self._category_repo.get(category_id)
        if category is None or category.organization_id != organization.id:
            raise NotFoundError(
                "Inventory item category not found in the active organization.",
                code="INVENTORY_CATEGORY_NOT_FOUND",
            )
        return category

    def find_category_by_code(
        self,
        category_code: str,
        *,
        active_only: bool | None = None,
    ) -> InventoryItemCategory | None:
        self._require_read("resolve inventory item category")
        organization = self._active_organization()
        normalized_code = normalize_inventory_code(category_code, label="Category code")
        category = self._category_repo.get_by_code(organization.id, normalized_code)
        if category is None:
            return None
        if active_only is not None and category.is_active != bool(active_only):
            return None
        return category

    def list_project_resource_categories(self, *, active_only: bool | None = True) -> list[InventoryItemCategory]:
        return self.search_categories(active_only=active_only, project_usage_only=True)

    def list_maintenance_categories(self, *, active_only: bool | None = True) -> list[InventoryItemCategory]:
        return self.search_categories(active_only=active_only, maintenance_usage_only=True)

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
        self._require_manage("create inventory item category")
        organization = self._active_organization()
        normalized_code = normalize_inventory_code(category_code, label="Category code")
        if self._category_repo.get_by_code(organization.id, normalized_code) is not None:
            raise ValidationError(
                "Category code already exists in the active organization.",
                code="INVENTORY_CATEGORY_CODE_EXISTS",
            )
        resolved_type = normalize_item_category_type(category_type)
        category = InventoryItemCategory.create(
            organization_id=organization.id,
            category_code=normalized_code,
            name=normalize_inventory_name(name, label="Category name"),
            description=normalize_optional_text(description),
            category_type=resolved_type,
            is_equipment=bool(is_equipment or resolved_type == "EQUIPMENT"),
            supports_project_usage=bool(supports_project_usage),
            supports_maintenance_usage=bool(supports_maintenance_usage),
            is_active=bool(is_active),
        )
        try:
            self._category_repo.add(category)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Category code already exists in the active organization.",
                code="INVENTORY_CATEGORY_CODE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="inventory_item_category.create",
            entity_type="inventory_item_category",
            entity_id=category.id,
            details={
                "organization_id": organization.id,
                "category_code": category.category_code,
                "category_type": category.category_type,
                "is_equipment": category.is_equipment,
                "supports_project_usage": category.supports_project_usage,
                "supports_maintenance_usage": category.supports_maintenance_usage,
            },
        )
        domain_events.inventory_item_categories_changed.emit(category.id)
        return category

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
        self._require_manage("update inventory item category")
        organization = self._active_organization()
        category = self._category_repo.get(category_id)
        if category is None or category.organization_id != organization.id:
            raise NotFoundError(
                "Inventory item category not found in the active organization.",
                code="INVENTORY_CATEGORY_NOT_FOUND",
            )
        if expected_version is not None and category.version != expected_version:
            raise ConcurrencyError(
                "Inventory item category changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        if category_code is not None:
            normalized_code = normalize_inventory_code(category_code, label="Category code")
            existing = self._category_repo.get_by_code(organization.id, normalized_code)
            if existing is not None and existing.id != category.id:
                raise ValidationError(
                    "Category code already exists in the active organization.",
                    code="INVENTORY_CATEGORY_CODE_EXISTS",
                )
            category.category_code = normalized_code
        if name is not None:
            category.name = normalize_inventory_name(name, label="Category name")
        if description is not None:
            category.description = normalize_optional_text(description)
        next_type = category.category_type
        if category_type is not None:
            next_type = normalize_item_category_type(category_type)
            category.category_type = next_type
        next_is_equipment = category.is_equipment if is_equipment is None else bool(is_equipment)
        if next_type == "EQUIPMENT":
            next_is_equipment = True
        category.is_equipment = next_is_equipment
        if supports_project_usage is not None:
            category.supports_project_usage = bool(supports_project_usage)
        if supports_maintenance_usage is not None:
            category.supports_maintenance_usage = bool(supports_maintenance_usage)
        if is_active is not None:
            category.is_active = bool(is_active)
        category.updated_at = datetime.now(timezone.utc)
        try:
            self._category_repo.update(category)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Category code already exists in the active organization.",
                code="INVENTORY_CATEGORY_CODE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="inventory_item_category.update",
            entity_type="inventory_item_category",
            entity_id=category.id,
            details={
                "organization_id": organization.id,
                "category_code": category.category_code,
                "category_type": category.category_type,
                "is_equipment": category.is_equipment,
                "supports_project_usage": category.supports_project_usage,
                "supports_maintenance_usage": category.supports_maintenance_usage,
                "is_active": category.is_active,
            },
        )
        domain_events.inventory_item_categories_changed.emit(category.id)
        return category

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "inventory.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "inventory.manage", operation_label=operation_label)


__all__ = ["ItemCategoryService"]
