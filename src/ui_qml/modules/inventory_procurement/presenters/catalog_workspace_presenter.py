from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryCategoryCreateCommand,
    InventoryCategoryUpdateCommand,
    InventoryItemCreateCommand,
    InventoryItemUpdateCommand,
    InventoryProcurementCatalogDesktopApi,
    build_inventory_procurement_catalog_desktop_api,
)
from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryCatalogMetricViewModel,
    InventoryCatalogOverviewViewModel,
    InventoryCatalogWorkspaceViewModel,
    InventoryDetailFieldViewModel,
    InventoryDetailViewModel,
    InventoryDocumentOptionViewModel,
    InventoryRecordViewModel,
    InventorySelectorOptionViewModel,
)


class InventoryCatalogWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: InventoryProcurementCatalogDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_inventory_procurement_catalog_desktop_api()

    def build_workspace_state(
        self,
        *,
        search_text: str = "",
        active_filter: str = "all",
        usage_filter: str = "all",
        category_type_filter: str = "all",
        category_filter: str = "all",
        selected_category_id: str | None = None,
        selected_item_id: str | None = None,
    ) -> InventoryCatalogWorkspaceViewModel:
        all_categories = self._desktop_api.list_categories(active_only=None)
        all_items = self._desktop_api.list_items(active_only=None)
        active_options = (
            InventorySelectorOptionViewModel(value="all", label="All records"),
            InventorySelectorOptionViewModel(value="active", label="Active only"),
            InventorySelectorOptionViewModel(value="inactive", label="Inactive only"),
        )
        usage_options = (
            InventorySelectorOptionViewModel(value="all", label="All usage"),
            InventorySelectorOptionViewModel(value="equipment", label="Equipment"),
            InventorySelectorOptionViewModel(value="projects", label="Projects"),
            InventorySelectorOptionViewModel(value="maintenance", label="Maintenance"),
        )
        category_type_options = (
            InventorySelectorOptionViewModel(value="all", label="All category types"),
            *(
                InventorySelectorOptionViewModel(
                    value=option.value,
                    label=option.label,
                )
                for option in self._desktop_api.list_category_types()
            ),
        )
        category_options = (
            InventorySelectorOptionViewModel(value="all", label="All categories"),
            *(
                InventorySelectorOptionViewModel(
                    value=category.category_code,
                    label=f"{category.category_code} - {category.name}",
                )
                for category in all_categories
            ),
        )
        item_status_options = tuple(
            InventorySelectorOptionViewModel(value=option.value, label=option.label)
            for option in self._desktop_api.list_item_statuses()
        )
        business_party_options = (
            InventorySelectorOptionViewModel(
                value="",
                label="No preferred party",
            ),
            *(
                InventorySelectorOptionViewModel(value=option.value, label=option.label)
                for option in self._desktop_api.list_business_parties(active_only=None)
            ),
        )
        available_documents = tuple(
            InventoryDocumentOptionViewModel(
                value=option.value,
                label=option.label,
                document_type=option.document_type,
                storage_kind=option.storage_kind,
                effective_date_label=option.effective_date_label,
                is_active=option.is_active,
            )
            for option in self._desktop_api.list_available_documents(active_only=True)
        )
        normalized_search = (search_text or "").strip()
        normalized_active_filter = self._normalize_active_filter(active_filter)
        normalized_usage_filter = self._normalize_usage_filter(usage_filter)
        normalized_category_type_filter = self._normalize_option_filter(
            category_type_filter,
            category_type_options,
        )
        normalized_category_filter = self._normalize_option_filter(
            category_filter,
            category_options,
        )
        categories_by_code = {
            category.category_code: category for category in all_categories
        }
        filtered_categories = tuple(
            category
            for category in all_categories
            if self._matches_active(category.is_active, normalized_active_filter)
            and self._matches_category_type(category, normalized_category_type_filter)
            and self._matches_usage(category, normalized_usage_filter)
            and self._matches_category_search(category, normalized_search)
        )
        filtered_items = tuple(
            item
            for item in all_items
            if self._matches_active(item.is_active, normalized_active_filter)
            and self._matches_item_category(item, normalized_category_filter)
            and self._matches_item_usage(
                item,
                normalized_usage_filter,
                categories_by_code,
            )
            and self._matches_item_search(item, normalized_search)
        )
        resolved_selected_category_id = self._resolve_selected_id(
            selected_category_id,
            filtered_categories,
        )
        resolved_selected_item_id = self._resolve_selected_id(
            selected_item_id,
            filtered_items,
        )
        selected_category = next(
            (
                category
                for category in filtered_categories
                if category.id == resolved_selected_category_id
            ),
            None,
        )
        selected_item = next(
            (item for item in filtered_items if item.id == resolved_selected_item_id),
            None,
        )
        return InventoryCatalogWorkspaceViewModel(
            overview=self._build_overview(
                all_categories=all_categories,
                all_items=all_items,
                filtered_categories=filtered_categories,
                filtered_items=filtered_items,
            ),
            active_options=active_options,
            usage_options=usage_options,
            category_type_options=category_type_options,
            category_options=category_options,
            item_status_options=item_status_options,
            business_party_options=business_party_options,
            available_documents=available_documents,
            selected_active_filter=normalized_active_filter,
            selected_usage_filter=normalized_usage_filter,
            selected_category_type_filter=normalized_category_type_filter,
            selected_category_filter=normalized_category_filter,
            search_text=normalized_search,
            categories=tuple(
                self._to_category_record_view_model(category)
                for category in filtered_categories
            ),
            selected_category_id=resolved_selected_category_id,
            selected_category_detail=self._build_category_detail(selected_category),
            items=tuple(self._to_item_record_view_model(item) for item in filtered_items),
            selected_item_id=resolved_selected_item_id,
            selected_item_detail=self._build_item_detail(selected_item),
            empty_state=self._build_workspace_empty_state(
                all_categories=all_categories,
                all_items=all_items,
                filtered_categories=filtered_categories,
                filtered_items=filtered_items,
                search_text=normalized_search,
                active_filter=normalized_active_filter,
                usage_filter=normalized_usage_filter,
                category_type_filter=normalized_category_type_filter,
                category_filter=normalized_category_filter,
            ),
        )

    def create_category(self, payload: dict[str, Any]) -> None:
        command = InventoryCategoryCreateCommand(
            category_code=self._require_text(
                payload,
                "categoryCode",
                "Category code is required.",
            ),
            name=self._require_text(payload, "name", "Category name is required."),
            description=self._optional_text(payload, "description") or "",
            category_type=self._require_text(
                payload,
                "categoryType",
                "Choose a category type before saving.",
            ),
            is_equipment=self._optional_bool(payload, "isEquipment", default=False),
            supports_project_usage=self._optional_bool(
                payload,
                "supportsProjectUsage",
                default=False,
            ),
            supports_maintenance_usage=self._optional_bool(
                payload,
                "supportsMaintenanceUsage",
                default=False,
            ),
            is_active=self._optional_bool(payload, "isActive", default=True),
        )
        self._desktop_api.create_category(command)

    def update_category(self, payload: dict[str, Any]) -> None:
        command = InventoryCategoryUpdateCommand(
            category_id=self._require_text(
                payload,
                "categoryId",
                "Category ID is required for updates.",
            ),
            category_code=self._require_text(
                payload,
                "categoryCode",
                "Category code is required.",
            ),
            name=self._require_text(payload, "name", "Category name is required."),
            description=self._optional_text(payload, "description") or "",
            category_type=self._require_text(
                payload,
                "categoryType",
                "Choose a category type before saving.",
            ),
            is_equipment=self._optional_bool(payload, "isEquipment", default=False),
            supports_project_usage=self._optional_bool(
                payload,
                "supportsProjectUsage",
                default=False,
            ),
            supports_maintenance_usage=self._optional_bool(
                payload,
                "supportsMaintenanceUsage",
                default=False,
            ),
            is_active=self._optional_bool(payload, "isActive", default=True),
            expected_version=self._optional_int(payload, "expectedVersion"),
        )
        self._desktop_api.update_category(command)

    def toggle_category_active(
        self,
        category_id: str,
        expected_version: int | None = None,
    ) -> None:
        normalized_id = (category_id or "").strip()
        if not normalized_id:
            raise ValueError("Category ID is required to change active state.")
        self._desktop_api.toggle_category_active(
            normalized_id,
            expected_version=expected_version,
        )

    def create_item(self, payload: dict[str, Any]) -> None:
        command = InventoryItemCreateCommand(
            item_code=self._require_text(payload, "itemCode", "Item code is required."),
            name=self._require_text(payload, "name", "Item name is required."),
            description=self._optional_text(payload, "description") or "",
            item_type=self._optional_text(payload, "itemType") or "",
            status=self._require_text(
                payload,
                "status",
                "Choose an item status before saving.",
            ),
            stock_uom=self._require_text(
                payload,
                "stockUom",
                "Stock UOM is required.",
            ),
            order_uom=self._optional_text(payload, "orderUom"),
            issue_uom=self._optional_text(payload, "issueUom"),
            order_uom_ratio=self._optional_float(payload, "orderUomRatio"),
            issue_uom_ratio=self._optional_float(payload, "issueUomRatio"),
            category_code=self._optional_text(payload, "categoryCode") or "",
            commodity_code=self._optional_text(payload, "commodityCode") or "",
            is_stocked=self._optional_bool(payload, "isStocked", default=True),
            is_purchase_allowed=self._optional_bool(
                payload,
                "isPurchaseAllowed",
                default=True,
            ),
            default_reorder_policy=self._optional_text(
                payload,
                "defaultReorderPolicy",
            )
            or "",
            min_qty=self._optional_float(payload, "minQty", default=0.0) or 0.0,
            max_qty=self._optional_float(payload, "maxQty", default=0.0) or 0.0,
            reorder_point=self._optional_float(payload, "reorderPoint", default=0.0)
            or 0.0,
            reorder_qty=self._optional_float(payload, "reorderQty", default=0.0)
            or 0.0,
            lead_time_days=self._optional_int(payload, "leadTimeDays"),
            is_lot_tracked=self._optional_bool(payload, "isLotTracked", default=False),
            is_serial_tracked=self._optional_bool(
                payload,
                "isSerialTracked",
                default=False,
            ),
            shelf_life_days=self._optional_int(payload, "shelfLifeDays"),
            preferred_party_id=self._optional_text(payload, "preferredPartyId"),
            notes=self._optional_text(payload, "notes") or "",
        )
        self._desktop_api.create_item(command)

    def update_item(self, payload: dict[str, Any]) -> None:
        command = InventoryItemUpdateCommand(
            item_id=self._require_text(
                payload,
                "itemId",
                "Item ID is required for updates.",
            ),
            item_code=self._require_text(payload, "itemCode", "Item code is required."),
            name=self._require_text(payload, "name", "Item name is required."),
            description=self._optional_text(payload, "description") or "",
            item_type=self._optional_text(payload, "itemType") or "",
            status=self._require_text(
                payload,
                "status",
                "Choose an item status before saving.",
            ),
            stock_uom=self._require_text(
                payload,
                "stockUom",
                "Stock UOM is required.",
            ),
            order_uom=self._optional_text(payload, "orderUom"),
            issue_uom=self._optional_text(payload, "issueUom"),
            order_uom_ratio=self._optional_float(payload, "orderUomRatio"),
            issue_uom_ratio=self._optional_float(payload, "issueUomRatio"),
            category_code=self._optional_text(payload, "categoryCode") or "",
            commodity_code=self._optional_text(payload, "commodityCode") or "",
            is_stocked=self._optional_bool(payload, "isStocked", default=True),
            is_purchase_allowed=self._optional_bool(
                payload,
                "isPurchaseAllowed",
                default=True,
            ),
            default_reorder_policy=self._optional_text(
                payload,
                "defaultReorderPolicy",
            )
            or "",
            min_qty=self._optional_float(payload, "minQty", default=0.0) or 0.0,
            max_qty=self._optional_float(payload, "maxQty", default=0.0) or 0.0,
            reorder_point=self._optional_float(payload, "reorderPoint", default=0.0)
            or 0.0,
            reorder_qty=self._optional_float(payload, "reorderQty", default=0.0)
            or 0.0,
            lead_time_days=self._optional_int(payload, "leadTimeDays"),
            is_lot_tracked=self._optional_bool(payload, "isLotTracked", default=False),
            is_serial_tracked=self._optional_bool(
                payload,
                "isSerialTracked",
                default=False,
            ),
            shelf_life_days=self._optional_int(payload, "shelfLifeDays"),
            preferred_party_id=self._optional_text(payload, "preferredPartyId"),
            notes=self._optional_text(payload, "notes") or "",
            expected_version=self._optional_int(payload, "expectedVersion"),
        )
        self._desktop_api.update_item(command)

    def apply_bulk_status(self, payload: dict[str, Any]) -> None:
        selected_ids = [
            str(item_id or "").strip()
            for item_id in payload.get("itemIds", [])
            if str(item_id or "").strip()
        ]
        if not selected_ids:
            raise ValueError("Select one or more catalog items to update.")
        next_status = self._require_text(
            payload,
            "status",
            "Choose a status before applying the bulk update.",
        )
        for item_id in selected_ids:
            self._desktop_api.change_item_status(item_id, status=next_status)

    def toggle_item_active(
        self,
        item_id: str,
        expected_version: int | None = None,
    ) -> None:
        normalized_id = (item_id or "").strip()
        if not normalized_id:
            raise ValueError("Item ID is required to change active state.")
        self._desktop_api.toggle_item_active(
            normalized_id,
            expected_version=expected_version,
        )

    def link_document(
        self,
        item_id: str,
        document_id: str,
    ) -> None:
        normalized_item_id = (item_id or "").strip()
        normalized_document_id = (document_id or "").strip()
        if not normalized_item_id:
            raise ValueError("Select an item before linking a document.")
        if not normalized_document_id:
            raise ValueError("Choose a document before saving.")
        self._desktop_api.link_document(
            normalized_item_id,
            document_id=normalized_document_id,
        )

    def unlink_document(
        self,
        item_id: str,
        document_id: str,
    ) -> None:
        normalized_item_id = (item_id or "").strip()
        normalized_document_id = (document_id or "").strip()
        if not normalized_item_id:
            raise ValueError("Select an item before unlinking a document.")
        if not normalized_document_id:
            raise ValueError("Choose a linked document before removing it.")
        self._desktop_api.unlink_document(
            normalized_item_id,
            document_id=normalized_document_id,
        )

    @staticmethod
    def _build_overview(
        *,
        all_categories,
        all_items,
        filtered_categories,
        filtered_items,
    ) -> InventoryCatalogOverviewViewModel:
        equipment_count = sum(1 for category in all_categories if category.is_equipment)
        project_usage_count = sum(
            1 for category in all_categories if category.supports_project_usage
        )
        maintenance_usage_count = sum(
            1 for category in all_categories if category.supports_maintenance_usage
        )
        active_item_count = sum(1 for item in all_items if item.is_active)
        stocked_item_count = sum(1 for item in all_items if item.is_stocked)
        purchasable_item_count = sum(
            1 for item in all_items if item.is_purchase_allowed
        )
        return InventoryCatalogOverviewViewModel(
            title="Catalog",
            subtitle="Category governance, reusable inventory items, supplier context, and linked document workflows.",
            metrics=(
                InventoryCatalogMetricViewModel(
                    label="Categories",
                    value=str(len(all_categories)),
                    supporting_text=f"Showing {len(filtered_categories)} category records with the current filters.",
                ),
                InventoryCatalogMetricViewModel(
                    label="Equipment",
                    value=str(equipment_count),
                    supporting_text="Categories flagged for reusable equipment and fleet-style assets.",
                ),
                InventoryCatalogMetricViewModel(
                    label="Project usage",
                    value=str(project_usage_count),
                    supporting_text="Categories available to project-side planning and execution.",
                ),
                InventoryCatalogMetricViewModel(
                    label="Maintenance usage",
                    value=str(maintenance_usage_count),
                    supporting_text="Categories available to maintenance spare and work-order flows.",
                ),
                InventoryCatalogMetricViewModel(
                    label="Active items",
                    value=str(active_item_count),
                    supporting_text=f"{stocked_item_count} stocked, {purchasable_item_count} purchasable.",
                ),
                InventoryCatalogMetricViewModel(
                    label="Filtered items",
                    value=str(len(filtered_items)),
                    supporting_text="Item rows that match the current catalog filters.",
                ),
            ),
        )

    def _build_category_detail(self, category) -> InventoryDetailViewModel:
        if category is None:
            return InventoryDetailViewModel(
                title="No category selected",
                empty_state="Select a category from the catalog to review usage flags or update its governance settings.",
            )
        state = self._build_category_state(category)
        usage_bits = []
        if category.is_equipment:
            usage_bits.append("Equipment")
        if category.supports_project_usage:
            usage_bits.append("Projects")
        if category.supports_maintenance_usage:
            usage_bits.append("Maintenance")
        return InventoryDetailViewModel(
            id=category.id,
            title=f"{category.category_code} - {category.name}",
            status_label=category.active_label,
            subtitle=", ".join(usage_bits) or "Inventory only",
            description=category.description or "No category description has been added yet.",
            fields=(
                InventoryDetailFieldViewModel(
                    label="Category type",
                    value=category.category_type_label,
                ),
                InventoryDetailFieldViewModel(
                    label="Usage",
                    value=", ".join(usage_bits) or "Inventory only",
                ),
                InventoryDetailFieldViewModel(
                    label="Active",
                    value=category.active_label,
                ),
                InventoryDetailFieldViewModel(
                    label="Version",
                    value=str(category.version),
                ),
            ),
            state=state,
        )

    def _build_item_detail(self, item) -> InventoryDetailViewModel:
        if item is None:
            return InventoryDetailViewModel(
                title="No item selected",
                empty_state="Select an item from the catalog to review operational fields, supplier context, and linked documents.",
            )
        linked_documents = tuple(
            InventoryDocumentOptionViewModel(
                value=document.value,
                label=document.label,
                document_type=document.document_type,
                storage_kind=document.storage_kind,
                effective_date_label=document.effective_date_label,
                is_active=document.is_active,
            )
            for document in self._desktop_api.list_linked_documents(
                item.id,
                active_only=None,
            )
        )
        state = self._build_item_state(item)
        return InventoryDetailViewModel(
            id=item.id,
            title=f"{item.item_code} - {item.name}",
            status_label=item.active_label,
            subtitle=item.preferred_party_label if item.preferred_party_id else "No preferred supplier",
            description=item.description or "No item description has been added yet.",
            fields=(
                InventoryDetailFieldViewModel(
                    label="Status",
                    value=item.status_label,
                ),
                InventoryDetailFieldViewModel(
                    label="Category",
                    value=item.category_label or "Uncategorized",
                ),
                InventoryDetailFieldViewModel(
                    label="UOM",
                    value=item.stock_uom or "-",
                    supporting_text=(
                        f"Order {item.order_uom or item.stock_uom or '-'} "
                        f"({item.order_uom_ratio_label}) | "
                        f"Issue {item.issue_uom or item.stock_uom or '-'} "
                        f"({item.issue_uom_ratio_label})"
                    ),
                ),
                InventoryDetailFieldViewModel(
                    label="Replenishment",
                    value=(
                        f"Min {item.min_qty_label} | Max {item.max_qty_label} | "
                        f"ROP {item.reorder_point_label} | ROQ {item.reorder_qty_label}"
                    ),
                    supporting_text=(
                        f"Lead time: {item.lead_time_days if item.lead_time_days is not None else '-'} days"
                    ),
                ),
                InventoryDetailFieldViewModel(
                    label="Tracking",
                    value=", ".join(
                        bit
                        for bit in (
                            "Stocked" if item.is_stocked else "",
                            "Purchasable" if item.is_purchase_allowed else "",
                            "Lot tracked" if item.is_lot_tracked else "",
                            "Serial tracked" if item.is_serial_tracked else "",
                        )
                        if bit
                    )
                    or "No special tracking flags",
                    supporting_text=(
                        f"Shelf life: {item.shelf_life_days if item.shelf_life_days is not None else '-'} days"
                    ),
                ),
                InventoryDetailFieldViewModel(
                    label="Preferred party",
                    value=item.preferred_party_label or "No preferred party",
                ),
                InventoryDetailFieldViewModel(
                    label="Version",
                    value=str(item.version),
                ),
            ),
            linked_documents=linked_documents,
            state=state,
        )

    @staticmethod
    def _to_category_record_view_model(category) -> InventoryRecordViewModel:
        state = InventoryCatalogWorkspacePresenter._build_category_state(category)
        usage_bits = []
        if category.is_equipment:
            usage_bits.append("Equipment")
        if category.supports_project_usage:
            usage_bits.append("Projects")
        if category.supports_maintenance_usage:
            usage_bits.append("Maintenance")
        return InventoryRecordViewModel(
            id=category.id,
            title=f"{category.category_code} - {category.name}",
            status_label=category.active_label,
            subtitle=category.category_type_label,
            supporting_text=", ".join(usage_bits) or "Inventory only",
            meta_text=category.description or "",
            can_primary_action=True,
            can_secondary_action=True,
            state=state,
        )

    @staticmethod
    def _to_item_record_view_model(item) -> InventoryRecordViewModel:
        state = InventoryCatalogWorkspacePresenter._build_item_state(item)
        return InventoryRecordViewModel(
            id=item.id,
            title=f"{item.item_code} - {item.name}",
            status_label=item.active_label,
            subtitle=item.category_label or "Uncategorized",
            supporting_text=(
                f"{item.status_label} | Stock UOM {item.stock_uom or '-'} | "
                f"ROP {item.reorder_point_label} | ROQ {item.reorder_qty_label}"
            ),
            meta_text=(
                item.preferred_party_label
                if item.preferred_party_id
                else "No preferred supplier linked"
            ),
            can_primary_action=True,
            can_secondary_action=True,
            state=state,
        )

    @staticmethod
    def _build_category_state(category) -> dict[str, object]:
        return {
            "categoryId": category.id,
            "categoryCode": category.category_code,
            "name": category.name,
            "description": category.description,
            "categoryType": category.category_type,
            "categoryTypeLabel": category.category_type_label,
            "isEquipment": category.is_equipment,
            "supportsProjectUsage": category.supports_project_usage,
            "supportsMaintenanceUsage": category.supports_maintenance_usage,
            "isActive": category.is_active,
            "activeLabel": category.active_label,
            "version": category.version,
        }

    @staticmethod
    def _build_item_state(item) -> dict[str, object]:
        return {
            "itemId": item.id,
            "itemCode": item.item_code,
            "name": item.name,
            "description": item.description,
            "itemType": item.item_type,
            "status": item.status,
            "statusLabel": item.status_label,
            "stockUom": item.stock_uom,
            "orderUom": item.order_uom or "",
            "issueUom": item.issue_uom or "",
            "orderUomRatio": f"{float(item.order_uom_ratio or 0.0):.3f}",
            "issueUomRatio": f"{float(item.issue_uom_ratio or 0.0):.3f}",
            "categoryCode": item.category_code,
            "categoryLabel": item.category_label,
            "commodityCode": item.commodity_code,
            "isStocked": item.is_stocked,
            "isPurchaseAllowed": item.is_purchase_allowed,
            "isActive": item.is_active,
            "activeLabel": item.active_label,
            "defaultReorderPolicy": item.default_reorder_policy,
            "minQty": f"{float(item.min_qty or 0.0):.3f}",
            "maxQty": f"{float(item.max_qty or 0.0):.3f}",
            "reorderPoint": f"{float(item.reorder_point or 0.0):.3f}",
            "reorderQty": f"{float(item.reorder_qty or 0.0):.3f}",
            "leadTimeDays": "" if item.lead_time_days is None else str(item.lead_time_days),
            "shelfLifeDays": "" if item.shelf_life_days is None else str(item.shelf_life_days),
            "isLotTracked": item.is_lot_tracked,
            "isSerialTracked": item.is_serial_tracked,
            "preferredPartyId": item.preferred_party_id or "",
            "preferredPartyLabel": item.preferred_party_label or "",
            "notes": item.notes,
            "version": item.version,
        }

    @staticmethod
    def _matches_active(is_active: bool, active_filter: str) -> bool:
        if active_filter == "all":
            return True
        if active_filter == "active":
            return bool(is_active)
        if active_filter == "inactive":
            return not bool(is_active)
        return True

    @staticmethod
    def _matches_category_type(category, category_type_filter: str) -> bool:
        if category_type_filter == "all":
            return True
        return category.category_type == category_type_filter

    @staticmethod
    def _matches_usage(category, usage_filter: str) -> bool:
        if usage_filter == "all":
            return True
        if usage_filter == "equipment":
            return bool(category.is_equipment)
        if usage_filter == "projects":
            return bool(category.supports_project_usage)
        if usage_filter == "maintenance":
            return bool(category.supports_maintenance_usage)
        return True

    @staticmethod
    def _matches_category_search(category, search_text: str) -> bool:
        if not search_text:
            return True
        normalized = search_text.casefold()
        haystacks = (
            category.category_code or "",
            category.name or "",
            category.description or "",
            category.category_type_label or "",
        )
        return any(normalized in value.casefold() for value in haystacks)

    @staticmethod
    def _matches_item_category(item, category_filter: str) -> bool:
        if category_filter == "all":
            return True
        return item.category_code == category_filter

    @staticmethod
    def _matches_item_usage(item, usage_filter: str, categories_by_code) -> bool:
        if usage_filter == "all":
            return True
        category = categories_by_code.get(item.category_code)
        if category is None:
            return False
        return InventoryCatalogWorkspacePresenter._matches_usage(category, usage_filter)

    @staticmethod
    def _matches_item_search(item, search_text: str) -> bool:
        if not search_text:
            return True
        normalized = search_text.casefold()
        haystacks = (
            item.item_code or "",
            item.name or "",
            item.description or "",
            item.category_label or "",
            item.preferred_party_label or "",
            item.status_label or "",
            item.commodity_code or "",
        )
        return any(normalized in value.casefold() for value in haystacks)

    @staticmethod
    def _resolve_selected_id(selected_id: str | None, rows) -> str:
        normalized_id = (selected_id or "").strip()
        if normalized_id and any(row.id == normalized_id for row in rows):
            return normalized_id
        if rows:
            return rows[0].id
        return ""

    @staticmethod
    def _normalize_active_filter(active_filter: str) -> str:
        normalized_value = (active_filter or "all").strip().lower()
        if normalized_value in {"all", "active", "inactive"}:
            return normalized_value
        return "all"

    @staticmethod
    def _normalize_usage_filter(usage_filter: str) -> str:
        normalized_value = (usage_filter or "all").strip().lower()
        if normalized_value in {"all", "equipment", "projects", "maintenance"}:
            return normalized_value
        return "all"

    @staticmethod
    def _normalize_option_filter(filter_value: str, options) -> str:
        normalized_value = (filter_value or "all").strip().upper()
        available_values = {option.value.upper(): option.value for option in options}
        return available_values.get(normalized_value, "all")

    @staticmethod
    def _build_workspace_empty_state(
        *,
        all_categories,
        all_items,
        filtered_categories,
        filtered_items,
        search_text: str,
        active_filter: str,
        usage_filter: str,
        category_type_filter: str,
        category_filter: str,
    ) -> str:
        if filtered_categories or filtered_items:
            return ""
        if not all_categories and not all_items:
            return "No inventory catalog records are available yet. Create categories and items to start the shared inventory master."
        if (
            search_text
            or active_filter != "all"
            or usage_filter != "all"
            or category_type_filter != "all"
            or category_filter != "all"
        ):
            return "No inventory catalog records match the current filters."
        return "No inventory catalog records are available yet."

    @staticmethod
    def _require_text(payload: dict[str, Any], key: str, message: str) -> str:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            raise ValueError(message)
        return value

    @staticmethod
    def _optional_text(payload: dict[str, Any], key: str) -> str | None:
        value = str(payload.get(key, "") or "").strip()
        return value or None

    @staticmethod
    def _optional_bool(payload: dict[str, Any], key: str, *, default: bool) -> bool:
        value = payload.get(key)
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _optional_int(payload: dict[str, Any], key: str) -> int | None:
        value = payload.get(key)
        if value in (None, ""):
            return None
        return int(value)

    @staticmethod
    def _optional_float(
        payload: dict[str, Any],
        key: str,
        message: str | None = None,
        *,
        default: float | None = None,
    ) -> float | None:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            return default
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(message or f"{key} must be a valid number.") from exc


__all__ = ["InventoryCatalogWorkspacePresenter"]
