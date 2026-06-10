from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryCatalogWorkspaceViewModel,
    InventoryDocumentOptionViewModel,
    InventorySelectorOptionViewModel,
)

from .category_mapper import to_category_record_view_model
from .detail_builder import build_category_detail, build_item_detail
from .filtering import (
    matches_active,
    matches_category_search,
    matches_category_type,
    matches_item_category,
    matches_item_search,
    matches_item_usage,
    matches_usage,
    normalize_active_filter,
    normalize_option_filter,
    normalize_usage_filter,
)
from .item_mapper import to_item_record_view_model
from .overview_builder import build_overview
from .selection import resolve_selected_id


def build_workspace_state(
    desktop_api,
    *,
    search_text: str = "",
    active_filter: str = "all",
    usage_filter: str = "all",
    category_type_filter: str = "all",
    category_filter: str = "all",
    selected_category_id: str | None = None,
    selected_item_id: str | None = None,
) -> InventoryCatalogWorkspaceViewModel:
    all_categories = desktop_api.list_categories(active_only=None)
    all_items = desktop_api.list_items(active_only=None)
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
            InventorySelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_category_types()
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
        for option in desktop_api.list_item_statuses()
    )
    business_party_options = (
        InventorySelectorOptionViewModel(value="", label="No preferred party"),
        *(
            InventorySelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_business_parties(active_only=None)
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
        for option in desktop_api.list_available_documents(active_only=True)
    )
    normalized_search = (search_text or "").strip()
    normalized_active_filter = normalize_active_filter(active_filter)
    normalized_usage_filter = normalize_usage_filter(usage_filter)
    normalized_category_type_filter = normalize_option_filter(
        category_type_filter,
        category_type_options,
    )
    normalized_category_filter = normalize_option_filter(
        category_filter,
        category_options,
    )
    categories_by_code = {
        category.category_code: category for category in all_categories
    }
    filtered_categories = tuple(
        category
        for category in all_categories
        if matches_active(category.is_active, normalized_active_filter)
        and matches_category_type(category, normalized_category_type_filter)
        and matches_usage(category, normalized_usage_filter)
        and matches_category_search(category, normalized_search)
    )
    filtered_items = tuple(
        item
        for item in all_items
        if matches_active(item.is_active, normalized_active_filter)
        and matches_item_category(item, normalized_category_filter)
        and matches_item_usage(item, normalized_usage_filter, categories_by_code)
        and matches_item_search(item, normalized_search)
    )
    resolved_selected_category_id = resolve_selected_id(
        selected_category_id,
        filtered_categories,
    )
    resolved_selected_item_id = resolve_selected_id(selected_item_id, filtered_items)
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
        overview=build_overview(
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
            to_category_record_view_model(category) for category in filtered_categories
        ),
        selected_category_id=resolved_selected_category_id,
        selected_category_detail=build_category_detail(selected_category),
        items=tuple(to_item_record_view_model(item) for item in filtered_items),
        selected_item_id=resolved_selected_item_id,
        selected_item_detail=build_item_detail(selected_item, desktop_api),
        empty_state=build_workspace_empty_state(
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


def build_workspace_empty_state(
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
