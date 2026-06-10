from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.controllers.common import (
    serialize_catalog_detail_view_model,
    serialize_catalog_overview_view_model,
    serialize_document_option_view_models,
    serialize_record_view_models,
    serialize_selector_options,
    serialize_workspace_view_model,
)


def refresh(ctrl) -> None:
    ctrl._set_is_loading(True)
    try:
        ctrl._set_error_message("")
        ctrl._set_feedback_message("")
        ctrl._set_workspace(
            serialize_workspace_view_model(
                ctrl._workspace_presenter.build_view_model()
            )
        )
        workspace_state = ctrl._catalog_workspace_presenter.build_workspace_state(
            search_text=ctrl._search_text,
            active_filter=ctrl._selected_active_filter,
            usage_filter=ctrl._selected_usage_filter,
            category_type_filter=ctrl._selected_category_type_filter,
            category_filter=ctrl._selected_category_filter,
            selected_category_id=ctrl._selected_category_id or None,
            selected_item_id=ctrl._selected_item_id or None,
        )
        ctrl._set_overview(
            serialize_catalog_overview_view_model(workspace_state.overview)
        )
        ctrl._set_active_options(
            serialize_selector_options(workspace_state.active_options)
        )
        ctrl._set_usage_options(
            serialize_selector_options(workspace_state.usage_options)
        )
        ctrl._set_category_type_options(
            serialize_selector_options(workspace_state.category_type_options)
        )
        ctrl._set_category_options(
            serialize_selector_options(workspace_state.category_options)
        )
        ctrl._set_item_status_options(
            serialize_selector_options(workspace_state.item_status_options)
        )
        ctrl._set_business_party_options(
            serialize_selector_options(workspace_state.business_party_options)
        )
        ctrl._set_available_documents(
            serialize_document_option_view_models(
                workspace_state.available_documents
            )
        )
        ctrl._set_selected_active_filter(workspace_state.selected_active_filter)
        ctrl._set_selected_usage_filter(workspace_state.selected_usage_filter)
        ctrl._set_selected_category_type_filter(
            workspace_state.selected_category_type_filter
        )
        ctrl._set_selected_category_filter(workspace_state.selected_category_filter)
        ctrl._set_search_text(workspace_state.search_text)
        ctrl._set_categories(
            {
                "title": "Category Catalog",
                "subtitle": "Govern category types, usage flags, and equipment grouping.",
                "emptyState": workspace_state.empty_state,
                "items": serialize_record_view_models(workspace_state.categories),
            }
        )
        ctrl._set_selected_category_id(workspace_state.selected_category_id)
        ctrl._set_selected_category(
            serialize_catalog_detail_view_model(
                workspace_state.selected_category_detail
            )
        )
        ctrl._set_items(
            {
                "title": "Item Catalog",
                "subtitle": "Manage reusable stock items, supplier context, and linked documents.",
                "emptyState": workspace_state.empty_state,
                "items": serialize_record_view_models(workspace_state.items),
            }
        )
        ctrl._set_selected_item_id(workspace_state.selected_item_id)
        ctrl._set_selected_item(
            serialize_catalog_detail_view_model(
                workspace_state.selected_item_detail
            )
        )
        ctrl._set_empty_state(workspace_state.empty_state)
    except Exception as exc:  # pragma: no cover - defensive fallback
        ctrl._set_error_message(str(exc))
    finally:
        ctrl._set_is_loading(False)
