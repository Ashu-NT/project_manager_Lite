from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventorySelectorOptionViewModel,
)
from src.ui_qml.modules.inventory_procurement.view_models.inventory import (
    InventoryInventoryWorkspaceViewModel,
)

from .balance_mapper import to_balance_record_view_model
from .detail_builder import build_balance_detail, build_storeroom_detail
from .filtering import (
    matches_active,
    matches_item,
    matches_search,
    matches_site,
    matches_storeroom_filter,
    matches_transaction_type,
    normalize_active_filter,
    normalize_filter,
)
from .foundation_builder import build_foundation
from .overview_builder import build_overview
from .selection import resolve_selected_id
from .storeroom_mapper import to_storeroom_record_view_model
from .transaction_mapper import to_transaction_record_view_model


def build_workspace_state(
    desktop_api,
    *,
    search_text: str = "",
    site_filter: str = "all",
    active_filter: str = "all",
    storeroom_filter: str = "all",
    item_filter: str = "all",
    transaction_type_filter: str = "all",
    selected_storeroom_id: str | None = None,
    selected_balance_id: str | None = None,
) -> InventoryInventoryWorkspaceViewModel:
    all_sites = desktop_api.list_sites(active_only=None)
    all_storerooms = desktop_api.list_storerooms(active_only=None)
    all_items = desktop_api.list_items(active_only=None)
    all_balances = desktop_api.list_balances()
    all_transactions = desktop_api.list_transactions(limit=200)

    site_options = (
        InventorySelectorOptionViewModel(value="all", label="All sites"),
        *(
            InventorySelectorOptionViewModel(value=option.value, label=option.label)
            for option in all_sites
        ),
    )
    active_options = (
        InventorySelectorOptionViewModel(value="all", label="All storerooms"),
        InventorySelectorOptionViewModel(value="active", label="Active only"),
        InventorySelectorOptionViewModel(value="inactive", label="Inactive only"),
    )
    storeroom_status_options = tuple(
        InventorySelectorOptionViewModel(value=option.value, label=option.label)
        for option in desktop_api.list_storeroom_statuses()
    )
    transaction_type_options = (
        InventorySelectorOptionViewModel(value="all", label="All movements"),
        *(
            InventorySelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_transaction_types()
        ),
    )
    storeroom_options = (
        InventorySelectorOptionViewModel(value="all", label="All storerooms"),
        *(
            InventorySelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_storeroom_options(active_only=None)
        ),
    )
    item_options = (
        InventorySelectorOptionViewModel(value="all", label="All items"),
        *(
            InventorySelectorOptionViewModel(value=option.value, label=option.label)
            for option in all_items
        ),
    )
    manager_party_options = (
        InventorySelectorOptionViewModel(value="", label="No manager party"),
        *(
            InventorySelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_business_parties(active_only=None)
        ),
    )

    normalized_search = (search_text or "").strip()
    normalized_site_filter = normalize_filter(site_filter, site_options)
    normalized_active_filter = normalize_active_filter(active_filter)
    normalized_storeroom_filter = normalize_filter(storeroom_filter, storeroom_options)
    normalized_item_filter = normalize_filter(item_filter, item_options)
    normalized_transaction_type_filter = normalize_filter(
        transaction_type_filter, transaction_type_options
    )

    filtered_storerooms = tuple(
        storeroom
        for storeroom in all_storerooms
        if matches_active(storeroom.is_active, normalized_active_filter)
        and matches_site(storeroom.site_id, normalized_site_filter)
        and matches_storeroom_filter(storeroom.id, normalized_storeroom_filter)
        and matches_search(
            normalized_search,
            storeroom.storeroom_code,
            storeroom.name,
            storeroom.site_label,
            storeroom.manager_party_label,
            storeroom.notes,
            storeroom.description,
            storeroom.status_label,
        )
    )
    allowed_storeroom_ids = {storeroom.id for storeroom in filtered_storerooms}
    filtered_balances = tuple(
        balance
        for balance in all_balances
        if balance.storeroom_id in allowed_storeroom_ids
        and matches_item(balance.stock_item_id, normalized_item_filter)
        and matches_search(
            normalized_search,
            balance.stock_item_label,
            balance.storeroom_label,
            balance.uom,
        )
    )
    filtered_transactions = tuple(
        transaction
        for transaction in all_transactions
        if transaction.storeroom_id in allowed_storeroom_ids
        and matches_item(transaction.stock_item_id, normalized_item_filter)
        and matches_transaction_type(
            transaction.transaction_type,
            normalized_transaction_type_filter,
        )
        and matches_search(
            normalized_search,
            transaction.transaction_number,
            transaction.stock_item_label,
            transaction.storeroom_label,
            transaction.reference_type,
            transaction.reference_id,
            transaction.performed_by_username,
            transaction.notes,
            transaction.transaction_type_label,
        )
    )

    resolved_selected_storeroom_id = resolve_selected_id(
        selected_storeroom_id, filtered_storerooms
    )
    resolved_selected_balance_id = resolve_selected_id(
        selected_balance_id, filtered_balances
    )
    selected_storeroom = next(
        (
            s for s in filtered_storerooms
            if s.id == resolved_selected_storeroom_id
        ),
        None,
    )
    selected_balance = next(
        (b for b in filtered_balances if b.id == resolved_selected_balance_id),
        None,
    )
    foundation_storeroom_scope = (
        resolved_selected_storeroom_id
        or (normalized_storeroom_filter if normalized_storeroom_filter != "all" else "")
    )

    return InventoryInventoryWorkspaceViewModel(
        overview=build_overview(
            all_storerooms=all_storerooms,
            all_balances=all_balances,
            filtered_storerooms=filtered_storerooms,
            filtered_balances=filtered_balances,
            filtered_transactions=filtered_transactions,
        ),
        site_options=site_options,
        active_options=active_options,
        storeroom_status_options=storeroom_status_options,
        transaction_type_options=transaction_type_options,
        storeroom_options=storeroom_options,
        item_options=item_options,
        manager_party_options=manager_party_options,
        selected_site_filter=normalized_site_filter,
        selected_active_filter=normalized_active_filter,
        selected_storeroom_filter=normalized_storeroom_filter,
        selected_item_filter=normalized_item_filter,
        selected_transaction_type_filter=normalized_transaction_type_filter,
        search_text=normalized_search,
        storerooms=tuple(
            to_storeroom_record_view_model(row) for row in filtered_storerooms
        ),
        selected_storeroom_id=resolved_selected_storeroom_id,
        selected_storeroom_detail=build_storeroom_detail(selected_storeroom),
        balances=tuple(to_balance_record_view_model(row) for row in filtered_balances),
        selected_balance_id=resolved_selected_balance_id,
        selected_balance_detail=build_balance_detail(selected_balance),
        transactions=tuple(
            to_transaction_record_view_model(row) for row in filtered_transactions
        ),
        foundation=build_foundation(
            desktop_api,
            site_filter=normalized_site_filter,
            storeroom_scope=foundation_storeroom_scope or None,
            item_filter=normalized_item_filter,
        ),
        empty_state=build_empty_state(
            all_storerooms=all_storerooms,
            all_balances=all_balances,
            search_text=normalized_search,
            active_filter=normalized_active_filter,
            site_filter=normalized_site_filter,
            storeroom_filter=normalized_storeroom_filter,
            item_filter=normalized_item_filter,
            transaction_type_filter=normalized_transaction_type_filter,
        ),
    )


def build_empty_state(
    *,
    all_storerooms,
    all_balances,
    search_text: str,
    active_filter: str,
    site_filter: str,
    storeroom_filter: str,
    item_filter: str,
    transaction_type_filter: str,
) -> str:
    if not all_storerooms and not all_balances:
        return "No storerooms or stock balances are available yet. Create a storeroom and post opening balances to start inventory operations."
    if (
        search_text
        or active_filter != "all"
        or site_filter != "all"
        or storeroom_filter != "all"
        or item_filter != "all"
        or transaction_type_filter != "all"
    ):
        return "No inventory records match the current filters."
    return ""
