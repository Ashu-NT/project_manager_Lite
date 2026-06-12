from __future__ import annotations


def set_overview(ctrl, overview: dict[str, object]) -> None:
    if overview == ctrl._overview:
        return
    ctrl._overview = overview
    ctrl.overviewChanged.emit()


def set_active_options(ctrl, active_options: list[dict[str, str]]) -> None:
    if active_options == ctrl._active_options:
        return
    ctrl._active_options = active_options
    ctrl.activeOptionsChanged.emit()


def set_usage_options(ctrl, usage_options: list[dict[str, str]]) -> None:
    if usage_options == ctrl._usage_options:
        return
    ctrl._usage_options = usage_options
    ctrl.usageOptionsChanged.emit()


def set_category_type_options(
    ctrl, category_type_options: list[dict[str, str]]
) -> None:
    if category_type_options == ctrl._category_type_options:
        return
    ctrl._category_type_options = category_type_options
    ctrl.categoryTypeOptionsChanged.emit()


def set_category_options(ctrl, category_options: list[dict[str, str]]) -> None:
    if category_options == ctrl._category_options:
        return
    ctrl._category_options = category_options
    ctrl.categoryOptionsChanged.emit()


def set_item_status_options(ctrl, item_status_options: list[dict[str, str]]) -> None:
    if item_status_options == ctrl._item_status_options:
        return
    ctrl._item_status_options = item_status_options
    ctrl.itemStatusOptionsChanged.emit()


def set_business_party_options(
    ctrl, business_party_options: list[dict[str, str]]
) -> None:
    if business_party_options == ctrl._business_party_options:
        return
    ctrl._business_party_options = business_party_options
    ctrl.businessPartyOptionsChanged.emit()


def set_available_documents(
    ctrl, available_documents: list[dict[str, object]]
) -> None:
    if available_documents == ctrl._available_documents:
        return
    ctrl._available_documents = available_documents
    ctrl.availableDocumentsChanged.emit()


def set_selected_active_filter(ctrl, selected_active_filter: str) -> None:
    if selected_active_filter == ctrl._selected_active_filter:
        return
    ctrl._selected_active_filter = selected_active_filter
    ctrl.selectedActiveFilterChanged.emit()


def set_selected_usage_filter(ctrl, selected_usage_filter: str) -> None:
    if selected_usage_filter == ctrl._selected_usage_filter:
        return
    ctrl._selected_usage_filter = selected_usage_filter
    ctrl.selectedUsageFilterChanged.emit()


def set_selected_category_type_filter(
    ctrl, selected_category_type_filter: str
) -> None:
    if selected_category_type_filter == ctrl._selected_category_type_filter:
        return
    ctrl._selected_category_type_filter = selected_category_type_filter
    ctrl.selectedCategoryTypeFilterChanged.emit()


def set_selected_category_filter(ctrl, selected_category_filter: str) -> None:
    if selected_category_filter == ctrl._selected_category_filter:
        return
    ctrl._selected_category_filter = selected_category_filter
    ctrl.selectedCategoryFilterChanged.emit()


def set_search_text(ctrl, search_text: str) -> None:
    if search_text == ctrl._search_text:
        return
    ctrl._search_text = search_text
    ctrl.searchTextChanged.emit()


def set_categories(ctrl, categories: dict[str, object]) -> None:
    if categories == ctrl._categories:
        return
    ctrl._categories = categories
    ctrl._categories_table_model.set_rows(categories.get("items", []))
    ctrl.categoriesChanged.emit()


def set_selected_category(ctrl, selected_category: dict[str, object]) -> None:
    if selected_category == ctrl._selected_category:
        return
    ctrl._selected_category = selected_category
    ctrl.selectedCategoryChanged.emit()


def set_selected_category_id(ctrl, selected_category_id: str) -> None:
    if selected_category_id == ctrl._selected_category_id:
        return
    ctrl._selected_category_id = selected_category_id
    ctrl.selectedCategoryIdChanged.emit()


def set_items(ctrl, items: dict[str, object]) -> None:
    if items == ctrl._items:
        return
    ctrl._items = items
    ctrl._items_table_model.set_rows(items.get("items", []))
    ctrl.itemsChanged.emit()


def set_selected_item(ctrl, selected_item: dict[str, object]) -> None:
    if selected_item == ctrl._selected_item:
        return
    ctrl._selected_item = selected_item
    ctrl.selectedItemChanged.emit()


def set_selected_item_id(ctrl, selected_item_id: str) -> None:
    if selected_item_id == ctrl._selected_item_id:
        return
    ctrl._selected_item_id = selected_item_id
    ctrl.selectedItemIdChanged.emit()


def set_selected_item_ids(ctrl, ids: list[str]) -> None:
    if ids == ctrl._selected_item_ids:
        return
    ctrl._selected_item_ids = ids
    ctrl.selectedItemIdsChanged.emit()


def set_selected_category_ids(ctrl, ids: list[str]) -> None:
    if ids == ctrl._selected_category_ids:
        return
    ctrl._selected_category_ids = ids
    ctrl.selectedCategoryIdsChanged.emit()


def set_detail_activity_items(
    ctrl, items: list[dict[str, object]]
) -> None:
    if items == ctrl._detail_activity_items:
        return
    ctrl._detail_activity_items = items
    ctrl.detailActivityItemsChanged.emit()
