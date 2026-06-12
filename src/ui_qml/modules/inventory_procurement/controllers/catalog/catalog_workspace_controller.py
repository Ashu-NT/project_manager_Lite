from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.inventory_procurement.controllers.common import (
    InventoryProcurementWorkspaceControllerBase,
)
from src.ui_qml.modules.inventory_procurement.presenters import (
    InventoryCatalogWorkspacePresenter,
    InventoryProcurementWorkspacePresenter,
)
from src.ui_qml.shared.models.data_table_model import DynamicTableModel

from .catalog_activity_handler import load_detail_activity
from .catalog_bulk_handler import (
    apply_bulk_status,
    clear_category_bulk_selection,
    clear_item_bulk_selection,
    select_visible_categories,
    select_visible_items,
    set_category_bulk_selection,
    set_item_bulk_selection,
)
from .catalog_document_handler import link_document, unlink_document
from .catalog_domain_event_binder import bind_domain_events
from .catalog_export_handler import export_table, is_items_view
from .catalog_filter_handler import (
    clear_filters,
    set_active_filter,
    set_category_filter,
    set_category_type_filter,
    set_search_text,
    set_usage_filter,
)
from .catalog_mutation_handler import (
    create_category,
    create_item,
    generate_entity_code,
    toggle_category_active,
    toggle_item_active,
    update_category,
    update_item,
)
from .catalog_refresh_service import refresh as _do_refresh
from .catalog_selection_handler import (
    select_category,
    select_item,
    set_active_view,
    set_category_page,
    set_category_page_size,
    set_item_page,
    set_item_page_size,
)
from .catalog_state import default_collection, default_detail, default_overview
from .catalog_state_setters import (
    set_active_options,
    set_available_documents,
    set_business_party_options,
    set_categories,
    set_category_options,
    set_category_type_options,
    set_detail_activity_items,
    set_item_status_options,
    set_items,
    set_overview,
    set_search_text as _set_search_text_setter,
    set_selected_active_filter,
    set_selected_category,
    set_selected_category_filter,
    set_selected_category_id,
    set_selected_category_ids,
    set_selected_category_type_filter,
    set_selected_item,
    set_selected_item_id,
    set_selected_item_ids,
    set_selected_usage_filter,
    set_usage_options,
)
from .catalog_table_models import create_catalog_table_models

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
        self._overview: dict[str, object] = default_overview()
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
        self._categories_table_model, self._items_table_model = (
            create_catalog_table_models(self)
        )
        self._categories: dict[str, object] = default_collection()
        self._selected_category: dict[str, object] = default_detail()
        self._selected_category_id = ""
        self._items: dict[str, object] = default_collection()
        self._selected_item: dict[str, object] = default_detail()
        self._selected_item_id = ""
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
        bind_domain_events(self)
        self.refresh()

    # ── Properties ───────────────────────────────────────────────────

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

    @Property("QVariantList", notify=detailActivityItemsChanged)
    def detailActivityItems(self) -> list[dict[str, object]]:
        return self._detail_activity_items

    # ── Internal view helper ──────────────────────────────────────────

    @property
    def _is_items_view(self) -> bool:
        return is_items_view(self)

    # ── Slots ─────────────────────────────────────────────────────────

    @Slot()
    def refresh(self) -> None:
        _do_refresh(self)

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        set_search_text(self, search_text)

    @Slot(str)
    def setActiveFilter(self, active_filter: str) -> None:
        set_active_filter(self, active_filter)

    @Slot(str)
    def setUsageFilter(self, usage_filter: str) -> None:
        set_usage_filter(self, usage_filter)

    @Slot(str)
    def setCategoryTypeFilter(self, category_type: str) -> None:
        set_category_type_filter(self, category_type)

    @Slot(str)
    def setCategoryFilter(self, category_code: str) -> None:
        set_category_filter(self, category_code)

    @Slot()
    def clearFilters(self) -> None:
        clear_filters(self)

    @Slot(str)
    def selectCategory(self, category_id: str) -> None:
        select_category(self, category_id)

    @Slot(str)
    def selectItem(self, item_id: str) -> None:
        select_item(self, item_id)

    @Slot(str)
    def activateCategory(self, category_id: str) -> None:
        self.selectCategory(category_id)

    @Slot(str)
    def activateItem(self, item_id: str) -> None:
        self.selectItem(item_id)

    @Slot(str)
    def setActiveView(self, view: str) -> None:
        set_active_view(self, view)

    @Slot(int)
    def setItemPage(self, page: int) -> None:
        set_item_page(self, page)

    @Slot(int)
    def setItemPageSize(self, size: int) -> None:
        set_item_page_size(self, size)

    @Slot(int)
    def setCategoryPage(self, page: int) -> None:
        set_category_page(self, page)

    @Slot(int)
    def setCategoryPageSize(self, size: int) -> None:
        set_category_page_size(self, size)

    @Slot(str, bool)
    def setItemBulkSelection(self, row_id: str, selected: bool) -> None:
        set_item_bulk_selection(self, row_id, selected)

    @Slot()
    def clearItemBulkSelection(self) -> None:
        clear_item_bulk_selection(self)

    @Slot()
    def selectVisibleItems(self) -> None:
        select_visible_items(self)

    @Slot(str, bool)
    def setCategoryBulkSelection(self, row_id: str, selected: bool) -> None:
        set_category_bulk_selection(self, row_id, selected)

    @Slot()
    def clearCategoryBulkSelection(self) -> None:
        clear_category_bulk_selection(self)

    @Slot()
    def selectVisibleCategories(self) -> None:
        select_visible_categories(self)

    @Slot("QVariantMap", result="QVariantMap")
    def applyBulkStatus(self, payload: dict[str, object]) -> dict[str, object]:
        return apply_bulk_status(self, dict(payload))

    @Slot(str, "QVariantMap", result=str)
    def generateEntityCode(self, entity_type: str, payload: dict[str, object]) -> str:
        return generate_entity_code(self, entity_type, dict(payload))

    @Slot("QVariantMap", result="QVariantMap")
    def createCategory(self, payload: dict[str, object]) -> dict[str, object]:
        return create_category(self, dict(payload))

    @Slot("QVariantMap", result="QVariantMap")
    def updateCategory(self, payload: dict[str, object]) -> dict[str, object]:
        return update_category(self, dict(payload))

    @Slot(str, int, result="QVariantMap")
    def toggleCategoryActive(
        self, category_id: str, expected_version: int = 0
    ) -> dict[str, object]:
        return toggle_category_active(self, category_id, expected_version)

    @Slot("QVariantMap", result="QVariantMap")
    def createItem(self, payload: dict[str, object]) -> dict[str, object]:
        return create_item(self, dict(payload))

    @Slot("QVariantMap", result="QVariantMap")
    def updateItem(self, payload: dict[str, object]) -> dict[str, object]:
        return update_item(self, dict(payload))

    @Slot(str, int, result="QVariantMap")
    def toggleItemActive(
        self, item_id: str, expected_version: int = 0
    ) -> dict[str, object]:
        return toggle_item_active(self, item_id, expected_version)

    @Slot(str, str, result="QVariantMap")
    def linkDocument(self, item_id: str, document_id: str) -> dict[str, object]:
        return link_document(self, item_id, document_id)

    @Slot(str, str, result="QVariantMap")
    def unlinkDocument(self, item_id: str, document_id: str) -> dict[str, object]:
        return unlink_document(self, item_id, document_id)

    @Slot("QVariantList", str, result="QVariantMap")
    def exportTable(self, columns: list, file_path: str) -> dict[str, object]:
        return export_table(self, columns, file_path)

    @Slot(str, str)
    def loadDetailActivity(self, entity_id: str, entity_type: str) -> None:
        load_detail_activity(self, entity_id, entity_type)

    # ── Private state setters (called by handlers and refresh service) ─

    def _set_overview(self, v: dict[str, object]) -> None:
        set_overview(self, v)

    def _set_active_options(self, v: list[dict[str, str]]) -> None:
        set_active_options(self, v)

    def _set_usage_options(self, v: list[dict[str, str]]) -> None:
        set_usage_options(self, v)

    def _set_category_type_options(self, v: list[dict[str, str]]) -> None:
        set_category_type_options(self, v)

    def _set_category_options(self, v: list[dict[str, str]]) -> None:
        set_category_options(self, v)

    def _set_item_status_options(self, v: list[dict[str, str]]) -> None:
        set_item_status_options(self, v)

    def _set_business_party_options(self, v: list[dict[str, str]]) -> None:
        set_business_party_options(self, v)

    def _set_available_documents(self, v: list[dict[str, object]]) -> None:
        set_available_documents(self, v)

    def _set_selected_active_filter(self, v: str) -> None:
        set_selected_active_filter(self, v)

    def _set_selected_usage_filter(self, v: str) -> None:
        set_selected_usage_filter(self, v)

    def _set_selected_category_type_filter(self, v: str) -> None:
        set_selected_category_type_filter(self, v)

    def _set_selected_category_filter(self, v: str) -> None:
        set_selected_category_filter(self, v)

    def _set_search_text(self, v: str) -> None:
        _set_search_text_setter(self, v)

    def _set_categories(self, v: dict[str, object]) -> None:
        set_categories(self, v)

    def _set_selected_category(self, v: dict[str, object]) -> None:
        set_selected_category(self, v)

    def _set_selected_category_id(self, v: str) -> None:
        set_selected_category_id(self, v)

    def _set_items(self, v: dict[str, object]) -> None:
        set_items(self, v)

    def _set_selected_item(self, v: dict[str, object]) -> None:
        set_selected_item(self, v)

    def _set_selected_item_id(self, v: str) -> None:
        set_selected_item_id(self, v)

    def _set_selected_item_ids(self, v: list[str]) -> None:
        set_selected_item_ids(self, v)

    def _set_selected_category_ids(self, v: list[str]) -> None:
        set_selected_category_ids(self, v)

    def _set_detail_activity_items(self, v: list[dict[str, object]]) -> None:
        set_detail_activity_items(self, v)


__all__ = ["InventoryProcurementCatalogWorkspaceController"]
