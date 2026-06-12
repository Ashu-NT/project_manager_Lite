from __future__ import annotations


def set_overview(ctrl, overview: dict[str, object]) -> None:
    if overview == ctrl._overview:
        return
    ctrl._overview = overview
    ctrl.overviewChanged.emit()


def set_site_options(ctrl, site_options: list[dict[str, str]]) -> None:
    if site_options == ctrl._site_options:
        return
    ctrl._site_options = site_options
    ctrl.siteOptionsChanged.emit()


def set_active_options(ctrl, active_options: list[dict[str, str]]) -> None:
    if active_options == ctrl._active_options:
        return
    ctrl._active_options = active_options
    ctrl.activeOptionsChanged.emit()


def set_storeroom_status_options(
    ctrl, storeroom_status_options: list[dict[str, str]]
) -> None:
    if storeroom_status_options == ctrl._storeroom_status_options:
        return
    ctrl._storeroom_status_options = storeroom_status_options
    ctrl.storeroomStatusOptionsChanged.emit()


def set_transaction_type_options(
    ctrl, transaction_type_options: list[dict[str, str]]
) -> None:
    if transaction_type_options == ctrl._transaction_type_options:
        return
    ctrl._transaction_type_options = transaction_type_options
    ctrl.transactionTypeOptionsChanged.emit()


def set_storeroom_options(ctrl, storeroom_options: list[dict[str, str]]) -> None:
    if storeroom_options == ctrl._storeroom_options:
        return
    ctrl._storeroom_options = storeroom_options
    ctrl.storeroomOptionsChanged.emit()


def set_item_options(ctrl, item_options: list[dict[str, str]]) -> None:
    if item_options == ctrl._item_options:
        return
    ctrl._item_options = item_options
    ctrl.itemOptionsChanged.emit()


def set_manager_party_options(
    ctrl, manager_party_options: list[dict[str, str]]
) -> None:
    if manager_party_options == ctrl._manager_party_options:
        return
    ctrl._manager_party_options = manager_party_options
    ctrl.managerPartyOptionsChanged.emit()


def set_selected_site_filter(ctrl, selected_site_filter: str) -> None:
    if selected_site_filter == ctrl._selected_site_filter:
        return
    ctrl._selected_site_filter = selected_site_filter
    ctrl.selectedSiteFilterChanged.emit()


def set_selected_active_filter(ctrl, selected_active_filter: str) -> None:
    if selected_active_filter == ctrl._selected_active_filter:
        return
    ctrl._selected_active_filter = selected_active_filter
    ctrl.selectedActiveFilterChanged.emit()


def set_selected_storeroom_filter(ctrl, selected_storeroom_filter: str) -> None:
    if selected_storeroom_filter == ctrl._selected_storeroom_filter:
        return
    ctrl._selected_storeroom_filter = selected_storeroom_filter
    ctrl.selectedStoreroomFilterChanged.emit()


def set_selected_item_filter(ctrl, selected_item_filter: str) -> None:
    if selected_item_filter == ctrl._selected_item_filter:
        return
    ctrl._selected_item_filter = selected_item_filter
    ctrl.selectedItemFilterChanged.emit()


def set_selected_transaction_type_filter(
    ctrl, selected_transaction_type_filter: str
) -> None:
    if selected_transaction_type_filter == ctrl._selected_transaction_type_filter:
        return
    ctrl._selected_transaction_type_filter = selected_transaction_type_filter
    ctrl.selectedTransactionTypeFilterChanged.emit()


def set_search_text(ctrl, search_text: str) -> None:
    if search_text == ctrl._search_text:
        return
    ctrl._search_text = search_text
    ctrl.searchTextChanged.emit()


def set_storerooms(ctrl, storerooms: dict[str, object]) -> None:
    if storerooms == ctrl._storerooms:
        return
    ctrl._storerooms = storerooms
    ctrl._storerooms_table_model.set_rows(storerooms.get("items", []))
    ctrl.storeroomsChanged.emit()


def set_selected_storeroom(ctrl, selected_storeroom: dict[str, object]) -> None:
    if selected_storeroom == ctrl._selected_storeroom:
        return
    ctrl._selected_storeroom = selected_storeroom
    ctrl.selectedStoreroomChanged.emit()


def set_selected_storeroom_id(ctrl, selected_storeroom_id: str) -> None:
    if selected_storeroom_id == ctrl._selected_storeroom_id:
        return
    ctrl._selected_storeroom_id = selected_storeroom_id
    ctrl.selectedStoreroomIdChanged.emit()


def set_balances(ctrl, balances: dict[str, object]) -> None:
    if balances == ctrl._balances:
        return
    ctrl._balances = balances
    ctrl._balances_table_model.set_rows(balances.get("items", []))
    ctrl.balancesChanged.emit()


def set_selected_balance(ctrl, selected_balance: dict[str, object]) -> None:
    if selected_balance == ctrl._selected_balance:
        return
    ctrl._selected_balance = selected_balance
    ctrl.selectedBalanceChanged.emit()


def set_selected_balance_id(ctrl, selected_balance_id: str) -> None:
    if selected_balance_id == ctrl._selected_balance_id:
        return
    ctrl._selected_balance_id = selected_balance_id
    ctrl.selectedBalanceIdChanged.emit()


def set_selected_location_id(ctrl, selected_location_id: str) -> None:
    if selected_location_id == ctrl._selected_location_id:
        return
    ctrl._selected_location_id = selected_location_id
    ctrl.selectedLocationIdChanged.emit()


def set_transactions(ctrl, transactions: dict[str, object]) -> None:
    if transactions == ctrl._transactions:
        return
    ctrl._transactions = transactions
    ctrl._transactions_table_model.set_rows(transactions.get("items", []))
    ctrl.transactionsChanged.emit()


def set_foundation(ctrl, foundation: dict[str, object]) -> None:
    if foundation == ctrl._foundation:
        return
    ctrl._foundation = foundation
    ctrl._foundation_table_model.set_rows(foundation.get("locations", []))
    ctrl.foundationChanged.emit()


def set_selected_balance_ids(ctrl, ids: list[str]) -> None:
    if ids == ctrl._selected_balance_ids:
        return
    ctrl._selected_balance_ids = ids
    ctrl.selectedBalanceIdsChanged.emit()


def set_selected_storeroom_ids(ctrl, ids: list[str]) -> None:
    if ids == ctrl._selected_storeroom_ids:
        return
    ctrl._selected_storeroom_ids = ids
    ctrl.selectedStoreroomIdsChanged.emit()


def set_detail_activity_items(ctrl, items: list[dict[str, object]]) -> None:
    if items == ctrl._detail_activity_items:
        return
    ctrl._detail_activity_items = items
    ctrl.detailActivityItemsChanged.emit()
