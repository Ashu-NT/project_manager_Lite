from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.shared.models.data_table_model import DynamicTableModel

from src.ui_qml.modules.inventory_procurement.controllers.common import (
    InventoryProcurementWorkspaceControllerBase,
    run_mutation,
    serialize_audit_entries_for_activity,
    serialize_catalog_detail_view_model,
    serialize_catalog_overview_view_model,
    serialize_document_option_view_models,
    serialize_record_view_models,
    serialize_selector_options,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.inventory_procurement.presenters import (
    InventoryCatalogWorkspacePresenter,
    InventoryProcurementWorkspacePresenter,
)

QML_IMPORT_NAME = "InventoryProcurement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Inventory workspace controllers are provided by the shell runtime.")
class InventoryProcurementCatalogWorkspaceController(
    InventoryProcurementWorkspaceControllerBase
):
    overviewChanged = Signal()
    activeOptionsChanged = Signal()
    usageOptionsChanged = Signal()
    categoryTypeOptionsChanged = Signal()
    categoryOptionsChanged = Signal()
    itemStatusOptionsChanged = Signal()
    businessPartyOptionsChanged = Signal()
    availableDocumentsChanged = Signal()
    selectedActiveFilterChanged = Signal()
    selectedUsageFilterChanged = Signal()
    selectedCategoryTypeFilterChanged = Signal()
    selectedCategoryFilterChanged = Signal()
    searchTextChanged = Signal()
    categoriesChanged = Signal()
    selectedCategoryChanged = Signal()
    selectedCategoryIdChanged = Signal()
    itemsChanged = Signal()
    selectedItemChanged = Signal()
    selectedItemIdChanged = Signal()
    # pagination + bulk + view
    itemPageChanged = Signal()
    itemPageSizeChanged = Signal()
    selectedItemIdsChanged = Signal()
    categoryPageChanged = Signal()
    categoryPageSizeChanged = Signal()
    selectedCategoryIdsChanged = Signal()
    activeViewChanged = Signal()
    bulkStatusOptionsChanged = Signal()
    detailActivityItemsChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: InventoryProcurementWorkspacePresenter | None = None,
        catalog_workspace_presenter: InventoryCatalogWorkspacePresenter | None = None,
        platform_audit: object | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or InventoryProcurementWorkspacePresenter(
            "inventory_procurement.catalog"
        )
        self._catalog_workspace_presenter = (
            catalog_workspace_presenter or InventoryCatalogWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._active_options: list[dict[str, str]] = []
        self._usage_options: list[dict[str, str]] = []
        self._category_type_options: list[dict[str, str]] = []
        self._category_options: list[dict[str, str]] = []
        self._item_status_options: list[dict[str, str]] = []
        self._business_party_options: list[dict[str, str]] = []
        self._available_documents: list[dict[str, object]] = []
        self._selected_active_filter = "all"
        self._selected_usage_filter = "all"
        self._selected_category_type_filter = "all"
        self._selected_category_filter = "all"
        self._search_text = ""
        self._categories_table_model = DynamicTableModel(self)
        self._items_table_model = DynamicTableModel(self)
        self._categories: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._selected_category: dict[str, object] = {
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "",
            "fields": [],
            "linkedDocuments": [],
            "state": {},
        }
        self._selected_category_id = ""
        self._items: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._selected_item: dict[str, object] = {
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "",
            "fields": [],
            "linkedDocuments": [],
            "state": {},
        }
        self._selected_item_id = ""
        # pagination + bulk + view state
        self._item_page = 1
        self._item_page_size = 25
        self._selected_item_ids: list[str] = []
        self._category_page = 1
        self._category_page_size = 25
        self._selected_category_ids: list[str] = []
        self._active_view = "items"
        self._bulk_status_options: list[dict[str, str]] = []
        self._platform_audit = platform_audit
        self._detail_activity_items: list[dict[str, object]] = []
        self._bind_domain_events()
        self.refresh()

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=activeOptionsChanged)
    def activeOptions(self) -> list[dict[str, str]]:
        return self._active_options

    @Property("QVariantList", notify=usageOptionsChanged)
    def usageOptions(self) -> list[dict[str, str]]:
        return self._usage_options

    @Property("QVariantList", notify=categoryTypeOptionsChanged)
    def categoryTypeOptions(self) -> list[dict[str, str]]:
        return self._category_type_options

    @Property("QVariantList", notify=categoryOptionsChanged)
    def categoryOptions(self) -> list[dict[str, str]]:
        return self._category_options

    @Property("QVariantList", notify=itemStatusOptionsChanged)
    def itemStatusOptions(self) -> list[dict[str, str]]:
        return self._item_status_options

    @Property("QVariantList", notify=businessPartyOptionsChanged)
    def businessPartyOptions(self) -> list[dict[str, str]]:
        return self._business_party_options

    @Property("QVariantList", notify=availableDocumentsChanged)
    def availableDocuments(self) -> list[dict[str, object]]:
        return self._available_documents

    @Property(str, notify=selectedActiveFilterChanged)
    def selectedActiveFilter(self) -> str:
        return self._selected_active_filter

    @Property(str, notify=selectedUsageFilterChanged)
    def selectedUsageFilter(self) -> str:
        return self._selected_usage_filter

    @Property(str, notify=selectedCategoryTypeFilterChanged)
    def selectedCategoryTypeFilter(self) -> str:
        return self._selected_category_type_filter

    @Property(str, notify=selectedCategoryFilterChanged)
    def selectedCategoryFilter(self) -> str:
        return self._selected_category_filter

    @Property(str, notify=searchTextChanged)
    def searchText(self) -> str:
        return self._search_text

    @Property("QVariantMap", notify=categoriesChanged)
    def categories(self) -> dict[str, object]:
        return self._categories

    @Property(QObject, constant=True)
    def categoriesTableModel(self) -> DynamicTableModel:
        return self._categories_table_model

    @Property("QVariantMap", notify=selectedCategoryChanged)
    def selectedCategory(self) -> dict[str, object]:
        return self._selected_category

    @Property(str, notify=selectedCategoryIdChanged)
    def selectedCategoryId(self) -> str:
        return self._selected_category_id

    @Property("QVariantMap", notify=itemsChanged)
    def items(self) -> dict[str, object]:
        return self._items

    @Property(QObject, constant=True)
    def itemsTableModel(self) -> DynamicTableModel:
        return self._items_table_model

    @Property("QVariantMap", notify=selectedItemChanged)
    def selectedItem(self) -> dict[str, object]:
        return self._selected_item

    @Property(str, notify=selectedItemIdChanged)
    def selectedItemId(self) -> str:
        return self._selected_item_id

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        try:
            self._set_error_message("")
            self._set_feedback_message("")
            self._set_workspace(
                serialize_workspace_view_model(
                    self._workspace_presenter.build_view_model()
                )
            )
            workspace_state = self._catalog_workspace_presenter.build_workspace_state(
                search_text=self._search_text,
                active_filter=self._selected_active_filter,
                usage_filter=self._selected_usage_filter,
                category_type_filter=self._selected_category_type_filter,
                category_filter=self._selected_category_filter,
                selected_category_id=self._selected_category_id or None,
                selected_item_id=self._selected_item_id or None,
            )
            self._set_overview(
                serialize_catalog_overview_view_model(workspace_state.overview)
            )
            self._set_active_options(
                serialize_selector_options(workspace_state.active_options)
            )
            self._set_usage_options(
                serialize_selector_options(workspace_state.usage_options)
            )
            self._set_category_type_options(
                serialize_selector_options(workspace_state.category_type_options)
            )
            self._set_category_options(
                serialize_selector_options(workspace_state.category_options)
            )
            self._set_item_status_options(
                serialize_selector_options(workspace_state.item_status_options)
            )
            self._set_business_party_options(
                serialize_selector_options(workspace_state.business_party_options)
            )
            self._set_available_documents(
                serialize_document_option_view_models(
                    workspace_state.available_documents
                )
            )
            self._set_selected_active_filter(workspace_state.selected_active_filter)
            self._set_selected_usage_filter(workspace_state.selected_usage_filter)
            self._set_selected_category_type_filter(
                workspace_state.selected_category_type_filter
            )
            self._set_selected_category_filter(
                workspace_state.selected_category_filter
            )
            self._set_search_text(workspace_state.search_text)
            self._set_categories(
                {
                    "title": "Category Catalog",
                    "subtitle": "Govern category types, usage flags, and equipment grouping.",
                    "emptyState": workspace_state.empty_state,
                    "items": serialize_record_view_models(workspace_state.categories),
                }
            )
            self._set_selected_category_id(workspace_state.selected_category_id)
            self._set_selected_category(
                serialize_catalog_detail_view_model(
                    workspace_state.selected_category_detail
                )
            )
            self._set_items(
                {
                    "title": "Item Catalog",
                    "subtitle": "Manage reusable stock items, supplier context, and linked documents.",
                    "emptyState": workspace_state.empty_state,
                    "items": serialize_record_view_models(workspace_state.items),
                }
            )
            self._set_selected_item_id(workspace_state.selected_item_id)
            self._set_selected_item(
                serialize_catalog_detail_view_model(
                    workspace_state.selected_item_detail
                )
            )
            self._set_empty_state(workspace_state.empty_state)
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        normalized_value = (search_text or "").strip()
        if normalized_value == self._search_text:
            return
        self._set_search_text(normalized_value)
        self.refresh()

    @Slot(str)
    def setActiveFilter(self, active_filter: str) -> None:
        normalized_value = (active_filter or "").strip().lower() or "all"
        if normalized_value == self._selected_active_filter:
            return
        self._set_selected_active_filter(normalized_value)
        self.refresh()

    @Slot(str)
    def setUsageFilter(self, usage_filter: str) -> None:
        normalized_value = (usage_filter or "").strip().lower() or "all"
        if normalized_value == self._selected_usage_filter:
            return
        self._set_selected_usage_filter(normalized_value)
        self.refresh()

    @Slot(str)
    def setCategoryTypeFilter(self, category_type: str) -> None:
        normalized_value = (category_type or "").strip() or "all"
        if normalized_value == self._selected_category_type_filter:
            return
        self._set_selected_category_type_filter(normalized_value)
        self.refresh()

    @Slot(str)
    def setCategoryFilter(self, category_code: str) -> None:
        normalized_value = (category_code or "").strip() or "all"
        if normalized_value == self._selected_category_filter:
            return
        self._set_selected_category_filter(normalized_value)
        self.refresh()

    @Slot(str)
    def selectCategory(self, category_id: str) -> None:
        normalized_value = (category_id or "").strip()
        if normalized_value == self._selected_category_id:
            return
        self._set_selected_category_id(normalized_value)
        self.refresh()

    @Slot(str)
    def selectItem(self, item_id: str) -> None:
        normalized_value = (item_id or "").strip()
        if normalized_value == self._selected_item_id:
            return
        self._set_selected_item_id(normalized_value)
        self.refresh()

    @Slot("QVariantMap", result="QVariantMap")
    def createCategory(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._catalog_workspace_presenter.create_category(
                dict(payload)
            ),
            success_message="Category created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateCategory(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._catalog_workspace_presenter.update_category(
                dict(payload)
            ),
            success_message="Category updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, int, result="QVariantMap")
    def toggleCategoryActive(
        self,
        category_id: str,
        expected_version: int = 0,
    ) -> dict[str, object]:
        resolved_version = expected_version or None
        return run_mutation(
            operation=lambda: self._catalog_workspace_presenter.toggle_category_active(
                category_id,
                resolved_version,
            ),
            success_message="Category availability updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createItem(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._catalog_workspace_presenter.create_item(
                dict(payload)
            ),
            success_message="Item created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateItem(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._catalog_workspace_presenter.update_item(
                dict(payload)
            ),
            success_message="Item updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def applyBulkStatus(self, payload: dict[str, object]) -> dict[str, object]:
        merged = dict(payload)
        merged.setdefault("itemIds", list(self._selected_item_ids))
        return run_mutation(
            operation=lambda: self._catalog_workspace_presenter.apply_bulk_status(
                merged
            ),
            success_message="Bulk item status applied.",
            on_success=lambda: (self.clearItemBulkSelection(), self.refresh()),
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, int, result="QVariantMap")
    def toggleItemActive(
        self,
        item_id: str,
        expected_version: int = 0,
    ) -> dict[str, object]:
        resolved_version = expected_version or None
        return run_mutation(
            operation=lambda: self._catalog_workspace_presenter.toggle_item_active(
                item_id,
                resolved_version,
            ),
            success_message="Item availability updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, str, result="QVariantMap")
    def linkDocument(self, item_id: str, document_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._catalog_workspace_presenter.link_document(
                item_id,
                document_id,
            ),
            success_message="Document linked.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, str, result="QVariantMap")
    def unlinkDocument(self, item_id: str, document_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._catalog_workspace_presenter.unlink_document(
                item_id,
                document_id,
            ),
            success_message="Document unlinked.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    # ── pagination + bulk + view ─────────────────────────────────────

    @Property(int, notify=itemPageChanged)
    def itemPage(self) -> int:
        return self._item_page

    @Property(int, notify=itemPageSizeChanged)
    def itemPageSize(self) -> int:
        return self._item_page_size

    @Property(int, notify=itemsChanged)
    def itemTotalCount(self) -> int:
        return len(self._items.get("items", []))

    @Property("QVariantList", notify=selectedItemIdsChanged)
    def selectedItemIds(self) -> list[str]:
        return self._selected_item_ids

    @Property(int, notify=selectedItemIdsChanged)
    def selectedItemCount(self) -> int:
        return len(self._selected_item_ids)

    @Property(int, notify=categoryPageChanged)
    def categoryPage(self) -> int:
        return self._category_page

    @Property(int, notify=categoryPageSizeChanged)
    def categoryPageSize(self) -> int:
        return self._category_page_size

    @Property(int, notify=categoriesChanged)
    def categoryTotalCount(self) -> int:
        return len(self._categories.get("items", []))

    @Property("QVariantList", notify=selectedCategoryIdsChanged)
    def selectedCategoryIds(self) -> list[str]:
        return self._selected_category_ids

    @Property(int, notify=selectedCategoryIdsChanged)
    def selectedCategoryCount(self) -> int:
        return len(self._selected_category_ids)

    @Property(str, notify=activeViewChanged)
    def activeView(self) -> str:
        return self._active_view

    @Property("QVariantList", notify=bulkStatusOptionsChanged)
    def bulkStatusOptions(self) -> list[dict[str, str]]:
        return self._bulk_status_options

    @Slot(str)
    def activateItem(self, item_id: str) -> None:
        self.selectItem(item_id)

    @Slot(str)
    def activateCategory(self, category_id: str) -> None:
        self.selectCategory(category_id)

    @Slot(str)
    def setActiveView(self, view: str) -> None:
        normalized = view if view in ("items", "categories") else "items"
        if normalized == self._active_view:
            return
        self._active_view = normalized
        self.activeViewChanged.emit()

    @Slot(int)
    def setItemPage(self, page: int) -> None:
        self._item_page = max(1, int(page))
        self.itemPageChanged.emit()

    @Slot(int)
    def setItemPageSize(self, size: int) -> None:
        self._item_page_size = max(10, min(200, int(size)))
        self._item_page = 1
        self.itemPageSizeChanged.emit()
        self.itemPageChanged.emit()

    @Slot(int)
    def setCategoryPage(self, page: int) -> None:
        self._category_page = max(1, int(page))
        self.categoryPageChanged.emit()

    @Slot(int)
    def setCategoryPageSize(self, size: int) -> None:
        self._category_page_size = max(10, min(200, int(size)))
        self._category_page = 1
        self.categoryPageSizeChanged.emit()
        self.categoryPageChanged.emit()

    @Slot(str, bool)
    def setItemBulkSelection(self, row_id: str, selected: bool) -> None:
        ids = list(self._selected_item_ids)
        if selected and row_id not in ids:
            ids.append(row_id)
        elif not selected and row_id in ids:
            ids.remove(row_id)
        self._set_selected_item_ids(ids)

    @Slot()
    def clearItemBulkSelection(self) -> None:
        self._set_selected_item_ids([])

    @Slot()
    def selectVisibleItems(self) -> None:
        all_ids = [
            str(r.get("id", ""))
            for r in self._items.get("items", [])
            if r.get("id")
        ]
        self._set_selected_item_ids(all_ids)

    @Slot(str, bool)
    def setCategoryBulkSelection(self, row_id: str, selected: bool) -> None:
        ids = list(self._selected_category_ids)
        if selected and row_id not in ids:
            ids.append(row_id)
        elif not selected and row_id in ids:
            ids.remove(row_id)
        self._set_selected_category_ids(ids)

    @Slot()
    def clearCategoryBulkSelection(self) -> None:
        self._set_selected_category_ids([])

    @Slot()
    def selectVisibleCategories(self) -> None:
        all_ids = [
            str(r.get("id", ""))
            for r in self._categories.get("items", [])
            if r.get("id")
        ]
        self._set_selected_category_ids(all_ids)

    @Slot()
    def clearFilters(self) -> None:
        self._set_selected_active_filter("all")
        self._set_selected_usage_filter("all")
        self._set_selected_category_type_filter("all")
        self._set_selected_category_filter("all")
        self._set_search_text("")
        self.refresh()

    def _set_selected_item_ids(self, ids: list[str]) -> None:
        if ids == self._selected_item_ids:
            return
        self._selected_item_ids = ids
        self.selectedItemIdsChanged.emit()

    def _set_selected_category_ids(self, ids: list[str]) -> None:
        if ids == self._selected_category_ids:
            return
        self._selected_category_ids = ids
        self.selectedCategoryIdsChanged.emit()

    @Property("QVariantList", notify=detailActivityItemsChanged)
    def detailActivityItems(self) -> list[dict[str, object]]:
        return self._detail_activity_items

    @Slot(str, str)
    def loadDetailActivity(self, entity_id: str, entity_type: str) -> None:
        if self._platform_audit is None or not entity_id:
            self._set_detail_activity_items([])
            return
        try:
            result = self._platform_audit.list_recent(entity_type=entity_type, limit=200)
            items = (
                serialize_audit_entries_for_activity(result.data, entity_id)
                if result.ok and result.data is not None
                else []
            )
        except Exception:  # pragma: no cover - defensive fallback
            items = []
        self._set_detail_activity_items(items)

    def _set_detail_activity_items(self, items: list[dict[str, object]]) -> None:
        if items == self._detail_activity_items:
            return
        self._detail_activity_items = items
        self.detailActivityItemsChanged.emit()

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(scope_code="inventory_procurement")
        self._subscribe_domain_change("document", scope_code="platform")
        self._subscribe_domain_change("party", scope_code="platform")

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_active_options(self, active_options: list[dict[str, str]]) -> None:
        if active_options == self._active_options:
            return
        self._active_options = active_options
        self.activeOptionsChanged.emit()

    def _set_usage_options(self, usage_options: list[dict[str, str]]) -> None:
        if usage_options == self._usage_options:
            return
        self._usage_options = usage_options
        self.usageOptionsChanged.emit()

    def _set_category_type_options(
        self,
        category_type_options: list[dict[str, str]],
    ) -> None:
        if category_type_options == self._category_type_options:
            return
        self._category_type_options = category_type_options
        self.categoryTypeOptionsChanged.emit()

    def _set_category_options(self, category_options: list[dict[str, str]]) -> None:
        if category_options == self._category_options:
            return
        self._category_options = category_options
        self.categoryOptionsChanged.emit()

    def _set_item_status_options(
        self,
        item_status_options: list[dict[str, str]],
    ) -> None:
        if item_status_options == self._item_status_options:
            return
        self._item_status_options = item_status_options
        self.itemStatusOptionsChanged.emit()

    def _set_business_party_options(
        self,
        business_party_options: list[dict[str, str]],
    ) -> None:
        if business_party_options == self._business_party_options:
            return
        self._business_party_options = business_party_options
        self.businessPartyOptionsChanged.emit()

    def _set_available_documents(
        self,
        available_documents: list[dict[str, object]],
    ) -> None:
        if available_documents == self._available_documents:
            return
        self._available_documents = available_documents
        self.availableDocumentsChanged.emit()

    def _set_selected_active_filter(self, selected_active_filter: str) -> None:
        if selected_active_filter == self._selected_active_filter:
            return
        self._selected_active_filter = selected_active_filter
        self.selectedActiveFilterChanged.emit()

    def _set_selected_usage_filter(self, selected_usage_filter: str) -> None:
        if selected_usage_filter == self._selected_usage_filter:
            return
        self._selected_usage_filter = selected_usage_filter
        self.selectedUsageFilterChanged.emit()

    def _set_selected_category_type_filter(
        self,
        selected_category_type_filter: str,
    ) -> None:
        if selected_category_type_filter == self._selected_category_type_filter:
            return
        self._selected_category_type_filter = selected_category_type_filter
        self.selectedCategoryTypeFilterChanged.emit()

    def _set_selected_category_filter(self, selected_category_filter: str) -> None:
        if selected_category_filter == self._selected_category_filter:
            return
        self._selected_category_filter = selected_category_filter
        self.selectedCategoryFilterChanged.emit()

    def _set_search_text(self, search_text: str) -> None:
        if search_text == self._search_text:
            return
        self._search_text = search_text
        self.searchTextChanged.emit()

    def _set_categories(self, categories: dict[str, object]) -> None:
        if categories == self._categories:
            return
        self._categories = categories
        self._categories_table_model.set_rows(categories.get("items", []))
        self.categoriesChanged.emit()

    def _set_selected_category(self, selected_category: dict[str, object]) -> None:
        if selected_category == self._selected_category:
            return
        self._selected_category = selected_category
        self.selectedCategoryChanged.emit()

    def _set_selected_category_id(self, selected_category_id: str) -> None:
        if selected_category_id == self._selected_category_id:
            return
        self._selected_category_id = selected_category_id
        self.selectedCategoryIdChanged.emit()

    def _set_items(self, items: dict[str, object]) -> None:
        if items == self._items:
            return
        self._items = items
        self._items_table_model.set_rows(items.get("items", []))
        self.itemsChanged.emit()

    def _set_selected_item(self, selected_item: dict[str, object]) -> None:
        if selected_item == self._selected_item:
            return
        self._selected_item = selected_item
        self.selectedItemChanged.emit()

    def _set_selected_item_id(self, selected_item_id: str) -> None:
        if selected_item_id == self._selected_item_id:
            return
        self._selected_item_id = selected_item_id
        self.selectedItemIdChanged.emit()


__all__ = ["InventoryProcurementCatalogWorkspaceController"]
