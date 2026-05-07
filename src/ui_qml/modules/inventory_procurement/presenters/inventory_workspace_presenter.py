from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryAdjustmentCommand,
    InventoryIssueCommand,
    InventoryOpeningBalanceCommand,
    InventoryProcurementInventoryDesktopApi,
    InventoryReturnCommand,
    InventoryStoreroomCreateCommand,
    InventoryStoreroomUpdateCommand,
    InventoryTransferCommand,
    build_inventory_procurement_inventory_desktop_api,
)
from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryCatalogMetricViewModel,
    InventoryCatalogOverviewViewModel,
    InventoryDetailFieldViewModel,
    InventoryDetailViewModel,
    InventoryRecordViewModel,
    InventorySelectorOptionViewModel,
)
from src.ui_qml.modules.inventory_procurement.view_models.inventory import (
    InventoryInventoryWorkspaceViewModel,
)


class InventoryInventoryWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: InventoryProcurementInventoryDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_inventory_procurement_inventory_desktop_api()

    def build_workspace_state(
        self,
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
        all_sites = self._desktop_api.list_sites(active_only=None)
        all_storerooms = self._desktop_api.list_storerooms(active_only=None)
        all_items = self._desktop_api.list_items(active_only=None)
        all_balances = self._desktop_api.list_balances()
        all_transactions = self._desktop_api.list_transactions(limit=200)

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
            for option in self._desktop_api.list_storeroom_statuses()
        )
        transaction_type_options = (
            InventorySelectorOptionViewModel(value="all", label="All movements"),
            *(
                InventorySelectorOptionViewModel(value=option.value, label=option.label)
                for option in self._desktop_api.list_transaction_types()
            ),
        )
        storeroom_options = (
            InventorySelectorOptionViewModel(value="all", label="All storerooms"),
            *(
                InventorySelectorOptionViewModel(value=option.value, label=option.label)
                for option in self._desktop_api.list_storeroom_options(active_only=None)
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
                for option in self._desktop_api.list_business_parties(active_only=None)
            ),
        )

        normalized_search = (search_text or "").strip()
        normalized_site_filter = self._normalize_filter(site_filter, site_options)
        normalized_active_filter = self._normalize_active_filter(active_filter)
        normalized_storeroom_filter = self._normalize_filter(
            storeroom_filter,
            storeroom_options,
        )
        normalized_item_filter = self._normalize_filter(item_filter, item_options)
        normalized_transaction_type_filter = self._normalize_filter(
            transaction_type_filter,
            transaction_type_options,
        )

        filtered_storerooms = tuple(
            storeroom
            for storeroom in all_storerooms
            if self._matches_active(storeroom.is_active, normalized_active_filter)
            and self._matches_site(storeroom.site_id, normalized_site_filter)
            and self._matches_storeroom_filter(storeroom.id, normalized_storeroom_filter)
            and self._matches_search(
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
            and self._matches_item(balance.stock_item_id, normalized_item_filter)
            and self._matches_search(
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
            and self._matches_item(transaction.stock_item_id, normalized_item_filter)
            and self._matches_transaction_type(
                transaction.transaction_type,
                normalized_transaction_type_filter,
            )
            and self._matches_search(
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

        resolved_selected_storeroom_id = self._resolve_selected_id(
            selected_storeroom_id,
            filtered_storerooms,
        )
        resolved_selected_balance_id = self._resolve_selected_id(
            selected_balance_id,
            filtered_balances,
        )
        selected_storeroom = next(
            (
                storeroom
                for storeroom in filtered_storerooms
                if storeroom.id == resolved_selected_storeroom_id
            ),
            None,
        )
        selected_balance = next(
            (balance for balance in filtered_balances if balance.id == resolved_selected_balance_id),
            None,
        )

        return InventoryInventoryWorkspaceViewModel(
            overview=self._build_overview(
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
                self._to_storeroom_record_view_model(row) for row in filtered_storerooms
            ),
            selected_storeroom_id=resolved_selected_storeroom_id,
            selected_storeroom_detail=self._build_storeroom_detail(selected_storeroom),
            balances=tuple(
                self._to_balance_record_view_model(row) for row in filtered_balances
            ),
            selected_balance_id=resolved_selected_balance_id,
            selected_balance_detail=self._build_balance_detail(selected_balance),
            transactions=tuple(
                self._to_transaction_record_view_model(row)
                for row in filtered_transactions
            ),
            empty_state=self._build_empty_state(
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

    def create_storeroom(self, payload: dict[str, Any]) -> None:
        command = InventoryStoreroomCreateCommand(
            storeroom_code=self._require_text(
                payload,
                "storeroomCode",
                "Storeroom code is required.",
            ),
            name=self._require_text(payload, "name", "Storeroom name is required."),
            site_id=self._require_text(payload, "siteId", "Choose a site before saving."),
            description=self._optional_text(payload, "description") or "",
            status=self._require_text(
                payload,
                "status",
                "Choose a storeroom status before saving.",
            ),
            storeroom_type=self._optional_text(payload, "storeroomType") or "",
            is_internal_supplier=self._optional_bool(
                payload,
                "isInternalSupplier",
                default=False,
            ),
            allows_issue=self._optional_bool(payload, "allowsIssue", default=True),
            allows_transfer=self._optional_bool(payload, "allowsTransfer", default=True),
            allows_receiving=self._optional_bool(payload, "allowsReceiving", default=True),
            requires_reservation_for_issue=self._optional_bool(
                payload,
                "requiresReservationForIssue",
                default=False,
            ),
            requires_supplier_reference_for_receipt=self._optional_bool(
                payload,
                "requiresSupplierReferenceForReceipt",
                default=False,
            ),
            default_currency_code=self._optional_text(payload, "defaultCurrencyCode"),
            manager_party_id=self._optional_text(payload, "managerPartyId"),
            notes=self._optional_text(payload, "notes") or "",
        )
        self._desktop_api.create_storeroom(command)

    def update_storeroom(self, payload: dict[str, Any]) -> None:
        command = InventoryStoreroomUpdateCommand(
            storeroom_id=self._require_text(
                payload,
                "storeroomId",
                "Storeroom ID is required for updates.",
            ),
            storeroom_code=self._require_text(
                payload,
                "storeroomCode",
                "Storeroom code is required.",
            ),
            name=self._require_text(payload, "name", "Storeroom name is required."),
            site_id=self._require_text(payload, "siteId", "Choose a site before saving."),
            description=self._optional_text(payload, "description") or "",
            status=self._require_text(
                payload,
                "status",
                "Choose a storeroom status before saving.",
            ),
            storeroom_type=self._optional_text(payload, "storeroomType") or "",
            is_internal_supplier=self._optional_bool(
                payload,
                "isInternalSupplier",
                default=False,
            ),
            allows_issue=self._optional_bool(payload, "allowsIssue", default=True),
            allows_transfer=self._optional_bool(payload, "allowsTransfer", default=True),
            allows_receiving=self._optional_bool(payload, "allowsReceiving", default=True),
            requires_reservation_for_issue=self._optional_bool(
                payload,
                "requiresReservationForIssue",
                default=False,
            ),
            requires_supplier_reference_for_receipt=self._optional_bool(
                payload,
                "requiresSupplierReferenceForReceipt",
                default=False,
            ),
            default_currency_code=self._optional_text(payload, "defaultCurrencyCode"),
            manager_party_id=self._optional_text(payload, "managerPartyId"),
            notes=self._optional_text(payload, "notes") or "",
            expected_version=self._optional_int(payload, "expectedVersion"),
        )
        self._desktop_api.update_storeroom(command)

    def toggle_storeroom_active(
        self,
        storeroom_id: str,
        expected_version: int | None = None,
    ) -> None:
        normalized_id = (storeroom_id or "").strip()
        if not normalized_id:
            raise ValueError("Storeroom ID is required to change active state.")
        self._desktop_api.toggle_storeroom_active(
            normalized_id,
            expected_version=expected_version,
        )

    def post_opening_balance(self, payload: dict[str, Any]) -> None:
        command = InventoryOpeningBalanceCommand(
            stock_item_id=self._require_text(
                payload,
                "stockItemId",
                "Choose an item before posting an opening balance.",
            ),
            storeroom_id=self._require_text(
                payload,
                "storeroomId",
                "Choose a storeroom before posting an opening balance.",
            ),
            quantity=self._require_positive_float(
                payload,
                "quantity",
                "Opening balance quantity must be greater than zero.",
            ),
            uom=self._optional_text(payload, "uom"),
            unit_cost=self._optional_float(payload, "unitCost", default=0.0) or 0.0,
            notes=self._optional_text(payload, "notes") or "",
        )
        self._desktop_api.post_opening_balance(command)

    def post_adjustment(self, payload: dict[str, Any]) -> None:
        command = InventoryAdjustmentCommand(
            stock_item_id=self._require_text(
                payload,
                "stockItemId",
                "Choose an item before posting an adjustment.",
            ),
            storeroom_id=self._require_text(
                payload,
                "storeroomId",
                "Choose a storeroom before posting an adjustment.",
            ),
            quantity=self._require_positive_float(
                payload,
                "quantity",
                "Adjustment quantity must be greater than zero.",
            ),
            direction=self._require_text(
                payload,
                "direction",
                "Choose whether the adjustment increases or decreases stock.",
            ),
            uom=self._optional_text(payload, "uom"),
            unit_cost=self._optional_float(payload, "unitCost", default=0.0) or 0.0,
            reference_type=self._optional_text(payload, "referenceType") or "adjustment",
            reference_id=self._optional_text(payload, "referenceId") or "",
            notes=self._optional_text(payload, "notes") or "",
        )
        self._desktop_api.post_adjustment(command)

    def issue_stock(self, payload: dict[str, Any]) -> None:
        command = InventoryIssueCommand(
            stock_item_id=self._require_text(
                payload,
                "stockItemId",
                "Choose an item before issuing stock.",
            ),
            storeroom_id=self._require_text(
                payload,
                "storeroomId",
                "Choose a storeroom before issuing stock.",
            ),
            quantity=self._require_positive_float(
                payload,
                "quantity",
                "Issue quantity must be greater than zero.",
            ),
            uom=self._optional_text(payload, "uom"),
            unit_cost=self._optional_float(payload, "unitCost"),
            release_reserved_qty=self._optional_float(
                payload,
                "releaseReservedQty",
                default=0.0,
            )
            or 0.0,
            reference_type=self._optional_text(payload, "referenceType") or "issue",
            reference_id=self._optional_text(payload, "referenceId") or "",
            notes=self._optional_text(payload, "notes") or "",
        )
        self._desktop_api.issue_stock(command)

    def return_stock(self, payload: dict[str, Any]) -> None:
        command = InventoryReturnCommand(
            stock_item_id=self._require_text(
                payload,
                "stockItemId",
                "Choose an item before posting a return.",
            ),
            storeroom_id=self._require_text(
                payload,
                "storeroomId",
                "Choose a storeroom before posting a return.",
            ),
            quantity=self._require_positive_float(
                payload,
                "quantity",
                "Return quantity must be greater than zero.",
            ),
            uom=self._optional_text(payload, "uom"),
            unit_cost=self._optional_float(payload, "unitCost"),
            reference_type=self._optional_text(payload, "referenceType") or "return",
            reference_id=self._optional_text(payload, "referenceId") or "",
            notes=self._optional_text(payload, "notes") or "",
        )
        self._desktop_api.return_stock(command)

    def transfer_stock(self, payload: dict[str, Any]) -> None:
        command = InventoryTransferCommand(
            stock_item_id=self._require_text(
                payload,
                "stockItemId",
                "Choose an item before transferring stock.",
            ),
            source_storeroom_id=self._require_text(
                payload,
                "sourceStoreroomId",
                "Choose a source storeroom before transferring stock.",
            ),
            destination_storeroom_id=self._require_text(
                payload,
                "destinationStoreroomId",
                "Choose a destination storeroom before transferring stock.",
            ),
            quantity=self._require_positive_float(
                payload,
                "quantity",
                "Transfer quantity must be greater than zero.",
            ),
            uom=self._optional_text(payload, "uom"),
            notes=self._optional_text(payload, "notes") or "",
        )
        self._desktop_api.transfer_stock(command)

    @staticmethod
    def _build_overview(
        *,
        all_storerooms,
        all_balances,
        filtered_storerooms,
        filtered_balances,
        filtered_transactions,
    ) -> InventoryCatalogOverviewViewModel:
        active_storerooms = sum(1 for row in all_storerooms if row.is_active)
        low_stock_count = sum(1 for row in all_balances if row.reorder_required)
        internal_supplier_count = sum(
            1 for row in all_storerooms if row.is_internal_supplier
        )
        return InventoryCatalogOverviewViewModel(
            title="Inventory",
            subtitle="Storeroom governance, stock position, and movement execution through the module-local inventory desktop API.",
            metrics=(
                InventoryCatalogMetricViewModel(
                    label="Storerooms",
                    value=str(len(all_storerooms)),
                    supporting_text=f"{active_storerooms} active, showing {len(filtered_storerooms)} with current filters.",
                ),
                InventoryCatalogMetricViewModel(
                    label="Internal suppliers",
                    value=str(internal_supplier_count),
                    supporting_text="Storerooms flagged to support internal supply or redistribution workflows.",
                ),
                InventoryCatalogMetricViewModel(
                    label="Stock balances",
                    value=str(len(all_balances)),
                    supporting_text=f"{len(filtered_balances)} balances remain after the current filters.",
                ),
                InventoryCatalogMetricViewModel(
                    label="Reorder watch",
                    value=str(low_stock_count),
                    supporting_text="Balances currently below reorder expectations.",
                ),
                InventoryCatalogMetricViewModel(
                    label="Recent movements",
                    value=str(len(filtered_transactions)),
                    supporting_text="Latest stock transactions visible in the movement feed.",
                ),
            ),
        )

    @staticmethod
    def _to_storeroom_record_view_model(storeroom) -> InventoryRecordViewModel:
        state = InventoryInventoryWorkspacePresenter._build_storeroom_state(storeroom)
        capabilities = ", ".join(
            bit
            for bit in (
                "Issue" if storeroom.allows_issue else "",
                "Transfer" if storeroom.allows_transfer else "",
                "Receiving" if storeroom.allows_receiving else "",
            )
            if bit
        ) or "No operational permissions"
        return InventoryRecordViewModel(
            id=storeroom.id,
            title=f"{storeroom.storeroom_code} - {storeroom.name}",
            status_label=storeroom.status_label,
            subtitle=storeroom.site_label or "No site",
            supporting_text=capabilities,
            meta_text=storeroom.manager_party_label or storeroom.active_label,
            state=state,
        )

    @staticmethod
    def _to_balance_record_view_model(balance) -> InventoryRecordViewModel:
        state = InventoryInventoryWorkspacePresenter._build_balance_state(balance)
        return InventoryRecordViewModel(
            id=balance.id,
            title=balance.stock_item_label or balance.stock_item_id,
            status_label="Reorder" if balance.reorder_required else "Healthy",
            subtitle=balance.storeroom_label or balance.storeroom_id,
            supporting_text=(
                f"On hand {balance.on_hand_qty_label} | Available {balance.available_qty_label} | Reserved {balance.reserved_qty_label}"
            ),
            meta_text=f"Avg cost {balance.average_cost_label} | UOM {balance.uom or '-'}",
            can_tertiary_action=True,
            state=state,
        )

    @staticmethod
    def _to_transaction_record_view_model(transaction) -> InventoryRecordViewModel:
        return InventoryRecordViewModel(
            id=transaction.id,
            title=transaction.transaction_number,
            status_label=transaction.transaction_type_label,
            subtitle=f"{transaction.stock_item_label} @ {transaction.storeroom_label}",
            supporting_text=(
                f"{transaction.quantity_label} {transaction.uom or ''} | {transaction.transaction_at_label}"
            ).strip(),
            meta_text=(
                f"Ref {transaction.reference_type or '-'} / {transaction.reference_id or '-'} | {transaction.performed_by_username or '-'}"
            ),
            can_primary_action=False,
            can_secondary_action=False,
            can_tertiary_action=False,
            state={"transactionId": transaction.id},
        )

    def _build_storeroom_detail(self, storeroom) -> InventoryDetailViewModel:
        if storeroom is None:
            return InventoryDetailViewModel(
                title="No storeroom selected",
                empty_state="Select a storeroom to review governance settings, manager ownership, and operational flags.",
            )
        capabilities = ", ".join(
            bit
            for bit in (
                "Issue" if storeroom.allows_issue else "",
                "Transfer" if storeroom.allows_transfer else "",
                "Receiving" if storeroom.allows_receiving else "",
            )
            if bit
        ) or "No operational permissions"
        policy_bits = ", ".join(
            bit
            for bit in (
                "Reservation required"
                if storeroom.requires_reservation_for_issue
                else "",
                "Supplier reference required"
                if storeroom.requires_supplier_reference_for_receipt
                else "",
            )
            if bit
        ) or "No extra policy flags"
        return InventoryDetailViewModel(
            id=storeroom.id,
            title=f"{storeroom.storeroom_code} - {storeroom.name}",
            status_label=storeroom.status_label,
            subtitle=storeroom.site_label,
            description=storeroom.description or "No storeroom description has been added yet.",
            fields=(
                InventoryDetailFieldViewModel(label="Active", value=storeroom.active_label),
                InventoryDetailFieldViewModel(
                    label="Storeroom type",
                    value=storeroom.storeroom_type or "-",
                ),
                InventoryDetailFieldViewModel(
                    label="Capabilities",
                    value=capabilities,
                    supporting_text=policy_bits,
                ),
                InventoryDetailFieldViewModel(
                    label="Manager party",
                    value=storeroom.manager_party_label or "No manager party",
                ),
                InventoryDetailFieldViewModel(
                    label="Default currency",
                    value=storeroom.default_currency_code or "-",
                ),
                InventoryDetailFieldViewModel(
                    label="Version",
                    value=str(storeroom.version),
                ),
            ),
            state=self._build_storeroom_state(storeroom),
        )

    def _build_balance_detail(self, balance) -> InventoryDetailViewModel:
        if balance is None:
            return InventoryDetailViewModel(
                title="No balance selected",
                empty_state="Select a balance row to inspect stock position or launch movement actions.",
            )
        return InventoryDetailViewModel(
            id=balance.id,
            title=balance.stock_item_label,
            status_label="Reorder" if balance.reorder_required else "Healthy",
            subtitle=balance.storeroom_label,
            description=(
                f"On hand {balance.on_hand_qty_label}, available {balance.available_qty_label}, reserved {balance.reserved_qty_label}."
            ),
            fields=(
                InventoryDetailFieldViewModel(
                    label="On hand",
                    value=balance.on_hand_qty_label,
                    supporting_text=f"Reserved {balance.reserved_qty_label} | Committed {balance.committed_qty_label}",
                ),
                InventoryDetailFieldViewModel(
                    label="Available / On order",
                    value=f"{balance.available_qty_label} available",
                    supporting_text=f"{balance.on_order_qty_label} on order",
                ),
                InventoryDetailFieldViewModel(
                    label="Average cost",
                    value=balance.average_cost_label,
                    supporting_text=f"UOM {balance.uom or '-'}",
                ),
                InventoryDetailFieldViewModel(
                    label="Receipts / Issues",
                    value=f"Last receipt {balance.last_receipt_at_label or '-'}",
                    supporting_text=f"Last issue {balance.last_issue_at_label or '-'}",
                ),
                InventoryDetailFieldViewModel(
                    label="Version",
                    value=str(balance.version),
                ),
            ),
            state=self._build_balance_state(balance),
        )

    @staticmethod
    def _build_storeroom_state(storeroom) -> dict[str, object]:
        return {
            "storeroomId": storeroom.id,
            "storeroomCode": storeroom.storeroom_code,
            "name": storeroom.name,
            "description": storeroom.description,
            "siteId": storeroom.site_id,
            "siteLabel": storeroom.site_label,
            "status": storeroom.status,
            "statusLabel": storeroom.status_label,
            "storeroomType": storeroom.storeroom_type,
            "isActive": storeroom.is_active,
            "activeLabel": storeroom.active_label,
            "isInternalSupplier": storeroom.is_internal_supplier,
            "allowsIssue": storeroom.allows_issue,
            "allowsTransfer": storeroom.allows_transfer,
            "allowsReceiving": storeroom.allows_receiving,
            "requiresReservationForIssue": storeroom.requires_reservation_for_issue,
            "requiresSupplierReferenceForReceipt": storeroom.requires_supplier_reference_for_receipt,
            "defaultCurrencyCode": storeroom.default_currency_code or "",
            "managerPartyId": storeroom.manager_party_id or "",
            "managerPartyLabel": storeroom.manager_party_label or "",
            "notes": storeroom.notes,
            "version": storeroom.version,
        }

    @staticmethod
    def _build_balance_state(balance) -> dict[str, object]:
        return {
            "balanceId": balance.id,
            "stockItemId": balance.stock_item_id,
            "stockItemLabel": balance.stock_item_label,
            "storeroomId": balance.storeroom_id,
            "storeroomLabel": balance.storeroom_label,
            "uom": balance.uom,
            "averageCost": f"{float(balance.average_cost or 0.0):.2f}",
            "averageCostLabel": balance.average_cost_label,
            "onHandQty": balance.on_hand_qty,
            "onHandQtyLabel": balance.on_hand_qty_label,
            "availableQty": balance.available_qty,
            "availableQtyLabel": balance.available_qty_label,
            "reservedQty": balance.reserved_qty,
            "reservedQtyLabel": balance.reserved_qty_label,
            "committedQty": balance.committed_qty,
            "committedQtyLabel": balance.committed_qty_label,
            "version": balance.version,
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
    def _matches_site(site_id: str, site_filter: str) -> bool:
        return site_filter == "all" or site_id == site_filter

    @staticmethod
    def _matches_storeroom_filter(storeroom_id: str, storeroom_filter: str) -> bool:
        return storeroom_filter == "all" or storeroom_id == storeroom_filter

    @staticmethod
    def _matches_item(stock_item_id: str, item_filter: str) -> bool:
        return item_filter == "all" or stock_item_id == item_filter

    @staticmethod
    def _matches_transaction_type(transaction_type: str, filter_value: str) -> bool:
        return filter_value == "all" or transaction_type == filter_value

    @staticmethod
    def _matches_search(search_text: str, *values: str) -> bool:
        if not search_text:
            return True
        normalized = search_text.casefold()
        return any(normalized in str(value or "").casefold() for value in values)

    @staticmethod
    def _resolve_selected_id(selected_id: str | None, rows) -> str:
        normalized_id = (selected_id or "").strip()
        if normalized_id and any(row.id == normalized_id for row in rows):
            return normalized_id
        if rows:
            return rows[0].id
        return ""

    @staticmethod
    def _normalize_filter(filter_value: str, options) -> str:
        normalized_input = (filter_value or "").strip().casefold()
        for option in options:
            if str(option.value or "").casefold() == normalized_input:
                return option.value
        return options[0].value if options else "all"

    @staticmethod
    def _normalize_active_filter(active_filter: str) -> str:
        normalized_value = (active_filter or "all").strip().lower()
        if normalized_value in {"all", "active", "inactive"}:
            return normalized_value
        return "all"

    @staticmethod
    def _build_empty_state(
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

    @staticmethod
    def _require_positive_float(payload: dict[str, Any], key: str, message: str) -> float:
        value = InventoryInventoryWorkspacePresenter._optional_float(
            payload,
            key,
            message,
        )
        if value is None or value <= 0:
            raise ValueError(message)
        return value


__all__ = ["InventoryInventoryWorkspacePresenter"]
