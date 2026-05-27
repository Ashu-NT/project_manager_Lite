from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from src.core.modules.inventory_procurement.application.catalog import ItemMasterService
from src.core.modules.inventory_procurement.application.common.reference_service import (
    InventoryReferenceService,
)
from src.core.modules.inventory_procurement.application.inventory import InventoryService
from src.core.modules.inventory_procurement.application.procurement import (
    PurchasingService,
)
from src.core.modules.inventory_procurement.api.desktop._support import (
    clean_text,
    format_amount,
    format_date,
    format_quantity,
)
from src.core.modules.inventory_procurement.api.desktop.pricing.models import (
    InventoryPricingMetricDescriptor,
    InventoryPricingRowDescriptor,
    InventoryPricingSnapshotDescriptor,
)
from src.core.modules.inventory_procurement.api.desktop.shared_options import (
    InventoryBusinessPartyOptionDescriptor,
    InventorySiteOptionDescriptor,
    InventoryStoreroomOptionDescriptor,
    serialize_business_party_option,
    serialize_site_option,
    serialize_storeroom_option,
)
from src.core.modules.inventory_procurement.infrastructure.reporting import (
    InventoryReportingService,
)


class InventoryProcurementPricingDesktopApi:
    def __init__(
        self,
        *,
        reporting_service: InventoryReportingService | None = None,
        reference_service: InventoryReferenceService | None = None,
        inventory_service: InventoryService | None = None,
        purchasing_service: PurchasingService | None = None,
        item_service: ItemMasterService | None = None,
        user_session: object | None = None,
    ) -> None:
        self._reporting_service = reporting_service
        self._reference_service = reference_service
        self._inventory_service = inventory_service
        self._purchasing_service = purchasing_service
        self._item_service = item_service
        self._user_session = user_session

    def list_site_options(
        self,
        *,
        active_only: bool | None = True,
    ) -> tuple[InventorySiteOptionDescriptor, ...]:
        if self._reference_service is None:
            return ()
        sites = sorted(
            self._reference_service.list_sites(active_only=active_only),
            key=lambda row: str(getattr(row, "site_code", "") or "").casefold(),
        )
        return tuple(serialize_site_option(row) for row in sites)

    def list_supplier_options(
        self,
        *,
        active_only: bool | None = True,
    ) -> tuple[InventoryBusinessPartyOptionDescriptor, ...]:
        if self._reference_service is None:
            return ()
        parties = sorted(
            self._reference_service.list_business_parties(active_only=active_only),
            key=lambda row: str(getattr(row, "party_code", "") or "").casefold(),
        )
        return tuple(serialize_business_party_option(row) for row in parties)

    def list_storeroom_options(
        self,
        *,
        active_only: bool | None = True,
        site_id: str | None = None,
    ) -> tuple[InventoryStoreroomOptionDescriptor, ...]:
        if self._inventory_service is None:
            return ()
        site_lookup = {
            row.value: row.label for row in self.list_site_options(active_only=None)
        }
        storerooms = self._inventory_service.list_storerooms(
            active_only=active_only,
            site_id=site_id,
        )
        ordered = sorted(
            storerooms,
            key=lambda row: str(getattr(row, "storeroom_code", "") or "").casefold(),
        )
        return tuple(
            serialize_storeroom_option(row, site_lookup=site_lookup)
            for row in ordered
        )

    def can_export_reports(self) -> bool:
        session = self._user_session
        if session is None or not hasattr(session, "has_permission"):
            return False
        try:
            return bool(session.has_permission("report.export"))
        except Exception:  # pragma: no cover - defensive permission fallback
            return False

    def build_empty_snapshot(self) -> InventoryPricingSnapshotDescriptor:
        return InventoryPricingSnapshotDescriptor(
            title="Pricing",
            subtitle=(
                "Supplier pricing analysis and inventory report exports appear here "
                "once the inventory pricing desktop API is connected."
            ),
            context_label="All sites | All storerooms | All suppliers | Limit 200",
            can_export=self.can_export_reports(),
            metrics=(
                InventoryPricingMetricDescriptor(
                    "Stock Rows",
                    "0",
                    "Filtered stock positions in scope",
                ),
                InventoryPricingMetricDescriptor(
                    "Reorder Alerts",
                    "0",
                    "Balances needing replenishment",
                ),
                InventoryPricingMetricDescriptor(
                    "On Order Qty",
                    "0.000",
                    "Inbound quantity in scope",
                ),
                InventoryPricingMetricDescriptor(
                    "Purchase Orders",
                    "0",
                    "Supplier commitments in scope",
                ),
                InventoryPricingMetricDescriptor(
                    "Receipts",
                    "0",
                    "Receiving records in scope",
                ),
                InventoryPricingMetricDescriptor(
                    "Open Qty",
                    "0.000",
                    "Outstanding purchase quantity",
                ),
                InventoryPricingMetricDescriptor(
                    "Suppliers",
                    "0",
                    "Suppliers represented in scope",
                ),
                InventoryPricingMetricDescriptor(
                    "Price Lines",
                    "0",
                    "Purchase-order lines with unit prices",
                ),
            ),
            empty_state="Inventory pricing desktop API is not connected in this preview.",
        )

    def build_snapshot(
        self,
        *,
        site_id: str | None = None,
        storeroom_id: str | None = None,
        supplier_party_id: str | None = None,
        limit: int = 200,
    ) -> InventoryPricingSnapshotDescriptor:
        if not all(
            (
                self._reporting_service,
                self._reference_service,
                self._inventory_service,
                self._purchasing_service,
                self._item_service,
            )
        ):
            return self.build_empty_snapshot()

        stock_report = self._reporting_service.build_stock_status_report(
            site_id=site_id,
            storeroom_id=storeroom_id,
        )
        procurement_report = self._reporting_service.build_procurement_overview_report(
            site_id=site_id,
            storeroom_id=storeroom_id,
            supplier_party_id=supplier_party_id,
            limit=limit,
        )
        stock_rows = self._build_stock_rows(stock_report)
        supplier_price_rows = self._build_supplier_price_rows(
            site_id=site_id,
            storeroom_id=storeroom_id,
            supplier_party_id=supplier_party_id,
            limit=limit,
        )
        supplier_codes = {
            clean_text(row.supplier_code)
            for row in procurement_report.purchase_orders
            if clean_text(row.supplier_code)
        }
        return InventoryPricingSnapshotDescriptor(
            title="Pricing",
            subtitle=(
                "Review export-ready stock and supplier commitments, then generate "
                "stock and procurement packages without dropping back into the QWidget reports tab."
            ),
            context_label=self._build_context_label(
                site_id=site_id,
                storeroom_id=storeroom_id,
                supplier_party_id=supplier_party_id,
                limit=limit,
            ),
            can_export=self.can_export_reports(),
            metrics=(
                InventoryPricingMetricDescriptor(
                    "Stock Rows",
                    str(len(stock_report.rows)),
                    "Filtered stock positions in scope",
                ),
                InventoryPricingMetricDescriptor(
                    "Reorder Alerts",
                    str(sum(1 for row in stock_report.rows if row.reorder_required)),
                    "Balances needing replenishment",
                ),
                InventoryPricingMetricDescriptor(
                    "On Order Qty",
                    format_quantity(sum(row.on_order_qty for row in stock_report.rows)),
                    "Inbound quantity in scope",
                ),
                InventoryPricingMetricDescriptor(
                    "Purchase Orders",
                    str(len(procurement_report.purchase_orders)),
                    "Supplier commitments in scope",
                ),
                InventoryPricingMetricDescriptor(
                    "Receipts",
                    str(len(procurement_report.receipts)),
                    "Receiving records in scope",
                ),
                InventoryPricingMetricDescriptor(
                    "Open Qty",
                    format_quantity(
                        sum(row.open_qty for row in procurement_report.purchase_orders)
                    ),
                    "Outstanding purchase quantity",
                ),
                InventoryPricingMetricDescriptor(
                    "Suppliers",
                    str(len(supplier_codes)),
                    "Suppliers represented in scope",
                ),
                InventoryPricingMetricDescriptor(
                    "Price Lines",
                    str(len(supplier_price_rows)),
                    "Purchase-order lines with unit prices",
                ),
            ),
            stock_rows=stock_rows,
            supplier_price_rows=supplier_price_rows,
        )

    def export_stock_status_csv(
        self,
        output_path: str,
        *,
        site_id: str | None = None,
        storeroom_id: str | None = None,
    ) -> str:
        artifact = self._require_reporting_service().generate_stock_status_csv(
            self._normalize_output_path(
                output_path,
                suffix=".csv",
                fallback_name="inventory-stock-status.csv",
            ),
            site_id=site_id,
            storeroom_id=storeroom_id,
        )
        return str(artifact.file_path)

    def export_stock_status_excel(
        self,
        output_path: str,
        *,
        site_id: str | None = None,
        storeroom_id: str | None = None,
    ) -> str:
        artifact = self._require_reporting_service().generate_stock_status_excel(
            self._normalize_output_path(
                output_path,
                suffix=".xlsx",
                fallback_name="inventory-stock-status.xlsx",
            ),
            site_id=site_id,
            storeroom_id=storeroom_id,
        )
        return str(artifact.file_path)

    def export_procurement_overview_csv(
        self,
        output_path: str,
        *,
        site_id: str | None = None,
        storeroom_id: str | None = None,
        supplier_party_id: str | None = None,
        limit: int = 200,
    ) -> str:
        artifact = self._require_reporting_service().generate_procurement_overview_csv(
            self._normalize_output_path(
                output_path,
                suffix=".csv",
                fallback_name="inventory-procurement-overview.csv",
            ),
            site_id=site_id,
            storeroom_id=storeroom_id,
            supplier_party_id=supplier_party_id,
            limit=limit,
        )
        return str(artifact.file_path)

    def export_procurement_overview_excel(
        self,
        output_path: str,
        *,
        site_id: str | None = None,
        storeroom_id: str | None = None,
        supplier_party_id: str | None = None,
        limit: int = 200,
    ) -> str:
        artifact = self._require_reporting_service().generate_procurement_overview_excel(
            self._normalize_output_path(
                output_path,
                suffix=".xlsx",
                fallback_name="inventory-procurement-overview.xlsx",
            ),
            site_id=site_id,
            storeroom_id=storeroom_id,
            supplier_party_id=supplier_party_id,
            limit=limit,
        )
        return str(artifact.file_path)

    def _build_context_label(
        self,
        *,
        site_id: str | None,
        storeroom_id: str | None,
        supplier_party_id: str | None,
        limit: int,
    ) -> str:
        return " | ".join(
            (
                self._label_from_site(site_id),
                self._label_from_storeroom(storeroom_id),
                self._label_from_supplier(supplier_party_id),
                f"Limit {max(1, int(limit))}",
            )
        )

    def _build_stock_rows(self, stock_report) -> tuple[InventoryPricingRowDescriptor, ...]:
        interesting_rows = [
            row
            for row in stock_report.rows
            if row.reorder_required or row.on_order_qty > 0 or row.reserved_qty > 0
        ]
        if not interesting_rows:
            interesting_rows = list(stock_report.rows[:12])
        ordered_rows = sorted(
            interesting_rows,
            key=lambda row: (
                not bool(row.reorder_required),
                -float(row.average_cost or 0.0),
                str(row.item_code or "").casefold(),
                str(row.storeroom_code or "").casefold(),
            ),
        )[:12]
        return tuple(
            InventoryPricingRowDescriptor(
                id=f"{row.item_code}:{row.storeroom_code}",
                title=" - ".join(
                    part for part in (row.item_code, row.item_name) if part
                ),
                subtitle=" - ".join(
                    part for part in (row.storeroom_code, row.storeroom_name) if part
                ),
                status_label="Reorder" if row.reorder_required else "Monitored",
                supporting_text=(
                    f"Available {format_quantity(row.available_qty)} {clean_text(row.uom)} | "
                    f"Reserved {format_quantity(row.reserved_qty)} | "
                    f"On order {format_quantity(row.on_order_qty)}"
                ),
                meta_text=(
                    f"Site {row.site_code or '-'} | "
                    f"Avg cost {format_amount(row.average_cost)} | "
                    f"Last receipt {row.last_receipt_at or '-'} | "
                    f"Last issue {row.last_issue_at or '-'}"
                ),
                tone="warning" if row.reorder_required else "default",
            )
            for row in ordered_rows
        )

    def _build_supplier_price_rows(
        self,
        *,
        site_id: str | None,
        storeroom_id: str | None,
        supplier_party_id: str | None,
        limit: int,
    ) -> tuple[InventoryPricingRowDescriptor, ...]:
        assert self._item_service is not None
        assert self._inventory_service is not None
        assert self._purchasing_service is not None
        item_lookup = {
            row.id: " - ".join(
                part
                for part in (
                    clean_text(getattr(row, "item_code", "")),
                    clean_text(getattr(row, "name", "")),
                )
                if part
            )
            for row in self._item_service.list_items(active_only=None)
        }
        storeroom_lookup = {
            row.id: " - ".join(
                part
                for part in (
                    clean_text(getattr(row, "storeroom_code", "")),
                    clean_text(getattr(row, "name", "")),
                )
                if part
            )
            for row in self._inventory_service.list_storerooms(active_only=None)
        }
        supplier_lookup = {
            row.value: row.label for row in self.list_supplier_options(active_only=None)
        }
        purchase_orders = sorted(
            self._purchasing_service.list_purchase_orders(
                site_id=site_id,
                supplier_party_id=supplier_party_id,
                limit=limit,
            ),
            key=lambda row: (
                str(getattr(row, "order_date", "") or ""),
                str(getattr(row, "po_number", "") or ""),
            ),
            reverse=True,
        )
        rows: list[InventoryPricingRowDescriptor] = []
        for purchase_order in purchase_orders:
            purchase_order_lines = self._purchasing_service.list_purchase_order_lines(
                purchase_order.id
            )
            for line in sorted(
                purchase_order_lines,
                key=lambda row: int(getattr(row, "line_number", 0) or 0),
            ):
                if storeroom_id and line.destination_storeroom_id != storeroom_id:
                    continue
                outstanding = max(
                    0.0,
                    float(line.quantity_ordered or 0.0)
                    - float(line.quantity_received or 0.0)
                    - float(line.quantity_rejected or 0.0),
                )
                rows.append(
                    InventoryPricingRowDescriptor(
                        id=line.id,
                        title=item_lookup.get(line.stock_item_id, line.stock_item_id),
                        subtitle=" | ".join(
                            part
                            for part in (
                                supplier_lookup.get(
                                    clean_text(
                                        getattr(purchase_order, "supplier_party_id", "")
                                    )
                                ),
                                clean_text(getattr(purchase_order, "po_number", "")),
                            )
                            if part
                        ),
                        status_label=format_amount(
                            getattr(line, "unit_price", 0.0),
                            currency=clean_text(
                                getattr(purchase_order, "currency_code", ""),
                                default="",
                            ),
                        ),
                        supporting_text=(
                            f"Ordered {format_quantity(line.quantity_ordered)} {clean_text(getattr(line, 'uom', ''))} | "
                            f"Received {format_quantity(line.quantity_received)} | "
                            f"Open {format_quantity(outstanding)}"
                        ),
                        meta_text=(
                            f"Status {clean_text(getattr(getattr(purchase_order, 'status', None), 'value', getattr(purchase_order, 'status', '')))} | "
                            f"Storeroom {storeroom_lookup.get(line.destination_storeroom_id, '-')} | "
                            f"Expected {format_date(getattr(line, 'expected_delivery_date', None) or getattr(purchase_order, 'expected_delivery_date', None))}"
                        ),
                        tone="accent" if outstanding > 0 else "success",
                    )
                )
                if len(rows) >= 12:
                    return tuple(rows)
        return tuple(rows)

    def _label_from_site(self, site_id: str | None) -> str:
        normalized = clean_text(site_id)
        if not normalized:
            return "All sites"
        lookup = {row.value: row.label for row in self.list_site_options(active_only=None)}
        return lookup.get(normalized, normalized)

    def _label_from_storeroom(self, storeroom_id: str | None) -> str:
        normalized = clean_text(storeroom_id)
        if not normalized:
            return "All storerooms"
        lookup = {
            row.value: row.label for row in self.list_storeroom_options(active_only=None)
        }
        return lookup.get(normalized, normalized)

    def _label_from_supplier(self, supplier_party_id: str | None) -> str:
        normalized = clean_text(supplier_party_id)
        if not normalized:
            return "All suppliers"
        lookup = {
            row.value: row.label for row in self.list_supplier_options(active_only=None)
        }
        return lookup.get(normalized, normalized)

    def _require_reporting_service(self) -> InventoryReportingService:
        if self._reporting_service is None:
            raise RuntimeError("Inventory pricing desktop API is not connected.")
        return self._reporting_service

    @staticmethod
    def _path_from_file_url(source: str) -> Path:
        parsed = urlparse(source)
        path_text = url2pathname(parsed.path)
        if parsed.netloc and parsed.netloc.lower() != "localhost":
            path_text = f"//{parsed.netloc}{path_text}"
        return Path(path_text)

    def _normalize_output_path(
        self,
        candidate: str,
        *,
        suffix: str,
        fallback_name: str,
    ) -> Path:
        raw = (candidate or "").strip()
        if not raw:
            return Path(fallback_name)
        parsed = urlparse(raw)
        if parsed.scheme == "file":
            path = self._path_from_file_url(raw)
        else:
            path = Path(raw)
        if path.suffix.lower() != suffix.lower():
            path = path.with_suffix(suffix)
        return path


def build_inventory_procurement_pricing_desktop_api(
    *,
    reporting_service: InventoryReportingService | None = None,
    reference_service: InventoryReferenceService | None = None,
    inventory_service: InventoryService | None = None,
    purchasing_service: PurchasingService | None = None,
    item_service: ItemMasterService | None = None,
    user_session: object | None = None,
) -> InventoryProcurementPricingDesktopApi:
    return InventoryProcurementPricingDesktopApi(
        reporting_service=reporting_service,
        reference_service=reference_service,
        inventory_service=inventory_service,
        purchasing_service=purchasing_service,
        item_service=item_service,
        user_session=user_session,
    )


__all__ = [
    "InventoryProcurementPricingDesktopApi",
    "build_inventory_procurement_pricing_desktop_api",
]
