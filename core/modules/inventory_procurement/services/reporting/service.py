from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from core.modules.inventory_procurement.reporting import (
    ProcurementOverviewReport,
    PurchaseOrderOverviewRow,
    ReceiptOverviewRow,
    ReportMetric,
    RequisitionOverviewRow,
    StockStatusReport,
    StockStatusRow,
    register_inventory_procurement_report_definitions,
)
from core.modules.inventory_procurement.reporting.excel import InventoryExcelReportRenderer
from core.modules.inventory_procurement.services.inventory import InventoryService
from core.modules.inventory_procurement.services.item_master import ItemMasterService
from core.modules.inventory_procurement.services.procurement import ProcurementService, PurchasingService
from core.modules.inventory_procurement.services.reference_service import InventoryReferenceService
from core.modules.inventory_procurement.services.stock_control import StockControlService
from core.platform.common.exceptions import ValidationError
from core.platform.exporting import ensure_output_path, finalize_artifact
from core.platform.report_runtime import ReportDefinitionRegistry, ReportRuntime


def _isoformat(value: object) -> str:
    if hasattr(value, "isoformat") and value is not None:
        return str(value.isoformat())
    return ""


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value) or "")


@dataclass(frozen=True)
class InventoryReportRequest:
    output_path: Path
    site_id: str | None = None
    storeroom_id: str | None = None
    supplier_party_id: str | None = None
    purchase_order_id: str | None = None
    limit: int = 200


class InventoryReportingService:
    def __init__(
        self,
        *,
        reference_service: InventoryReferenceService,
        item_service: ItemMasterService,
        inventory_service: InventoryService,
        stock_service: StockControlService,
        procurement_service: ProcurementService,
        purchasing_service: PurchasingService,
        user_session=None,
        module_catalog_service=None,
        runtime_execution_service=None,
        report_registry: ReportDefinitionRegistry | None = None,
        report_runtime: ReportRuntime | None = None,
        excel_renderer: InventoryExcelReportRenderer | None = None,
    ) -> None:
        self._reference_service = reference_service
        self._item_service = item_service
        self._inventory_service = inventory_service
        self._stock_service = stock_service
        self._procurement_service = procurement_service
        self._purchasing_service = purchasing_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service
        self._excel_renderer = excel_renderer or InventoryExcelReportRenderer()

        registry = report_registry or ReportDefinitionRegistry()
        register_inventory_procurement_report_definitions(
            registry,
            render_handlers={
                "stock_status_csv": self._render_stock_status_csv,
                "stock_status_excel": self._render_stock_status_excel,
                "procurement_overview_csv": self._render_procurement_overview_csv,
                "procurement_overview_excel": self._render_procurement_overview_excel,
            },
        )
        self._report_runtime = report_runtime or ReportRuntime(
            registry,
            user_session=user_session,
            module_catalog_service=module_catalog_service,
            runtime_execution_service=runtime_execution_service,
        )

    def generate_stock_status_csv(self, output_path: str | Path, *, site_id: str | None = None, storeroom_id: str | None = None):
        return self._render("stock_status_csv", output_path=output_path, site_id=site_id, storeroom_id=storeroom_id)

    def generate_stock_status_excel(self, output_path: str | Path, *, site_id: str | None = None, storeroom_id: str | None = None):
        return self._render("stock_status_excel", output_path=output_path, site_id=site_id, storeroom_id=storeroom_id)

    def generate_procurement_overview_csv(
        self,
        output_path: str | Path,
        *,
        site_id: str | None = None,
        storeroom_id: str | None = None,
        supplier_party_id: str | None = None,
        purchase_order_id: str | None = None,
        limit: int = 200,
    ):
        return self._render(
            "procurement_overview_csv",
            output_path=output_path,
            site_id=site_id,
            storeroom_id=storeroom_id,
            supplier_party_id=supplier_party_id,
            purchase_order_id=purchase_order_id,
            limit=limit,
        )

    def generate_procurement_overview_excel(
        self,
        output_path: str | Path,
        *,
        site_id: str | None = None,
        storeroom_id: str | None = None,
        supplier_party_id: str | None = None,
        purchase_order_id: str | None = None,
        limit: int = 200,
    ):
        return self._render(
            "procurement_overview_excel",
            output_path=output_path,
            site_id=site_id,
            storeroom_id=storeroom_id,
            supplier_party_id=supplier_party_id,
            purchase_order_id=purchase_order_id,
            limit=limit,
        )

    def _render(
        self,
        report_key: str,
        *,
        output_path: str | Path,
        site_id: str | None = None,
        storeroom_id: str | None = None,
        supplier_party_id: str | None = None,
        purchase_order_id: str | None = None,
        limit: int = 200,
    ):
        return self._report_runtime.render(
            report_key,
            InventoryReportRequest(
                output_path=Path(output_path),
                site_id=site_id,
                storeroom_id=storeroom_id,
                supplier_party_id=supplier_party_id,
                purchase_order_id=purchase_order_id,
                limit=limit,
            ),
            user_session=self._user_session,
            module_catalog_service=self._module_catalog_service,
        )

    def _render_stock_status_csv(self, request: object):
        assert isinstance(request, InventoryReportRequest)
        report = self._build_stock_status_report(request)
        output_path = ensure_output_path(request.output_path)
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow([report.title])
            writer.writerow([])
            writer.writerow(["Filters"])
            writer.writerow(["Metric", "Value"])
            for metric in report.filters:
                writer.writerow([metric.label, metric.value])
            writer.writerow([])
            writer.writerow(["Summary"])
            writer.writerow(["Metric", "Value"])
            for metric in report.summary:
                writer.writerow([metric.label, metric.value])
            writer.writerow([])
            writer.writerow(
                [
                    "Item Code",
                    "Item Name",
                    "Storeroom",
                    "Storeroom Name",
                    "Site",
                    "UOM",
                    "On Hand",
                    "Reserved",
                    "Available",
                    "On Order",
                    "Average Cost",
                    "Reorder Required",
                    "Last Receipt",
                    "Last Issue",
                ]
            )
            for row in report.rows:
                writer.writerow(
                    [
                        row.item_code,
                        row.item_name,
                        row.storeroom_code,
                        row.storeroom_name,
                        row.site_code,
                        row.uom,
                        row.on_hand_qty,
                        row.reserved_qty,
                        row.available_qty,
                        row.on_order_qty,
                        row.average_cost,
                        "Yes" if row.reorder_required else "No",
                        row.last_receipt_at,
                        row.last_issue_at,
                    ]
                )
        return finalize_artifact(output_path, media_type="text/csv")

    def _render_stock_status_excel(self, request: object):
        assert isinstance(request, InventoryReportRequest)
        report = self._build_stock_status_report(request)
        output_path = ensure_output_path(request.output_path)
        rendered = self._excel_renderer.render_stock_status(report, output_path)
        return finalize_artifact(
            rendered,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def _render_procurement_overview_csv(self, request: object):
        assert isinstance(request, InventoryReportRequest)
        report = self._build_procurement_overview_report(request)
        output_path = ensure_output_path(request.output_path)
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow([report.title])
            writer.writerow([])
            writer.writerow(["Filters"])
            writer.writerow(["Metric", "Value"])
            for metric in report.filters:
                writer.writerow([metric.label, metric.value])
            writer.writerow([])
            writer.writerow(["Summary"])
            writer.writerow(["Metric", "Value"])
            for metric in report.summary:
                writer.writerow([metric.label, metric.value])
            writer.writerow([])
            writer.writerow(["Requisitions"])
            writer.writerow(["Requisition", "Status", "Site", "Storeroom", "Requester", "Needed By", "Priority", "Lines", "Requested Qty", "Sourced Qty", "Purpose"])
            for row in report.requisitions:
                writer.writerow([row.requisition_number, row.status, row.site_code, row.storeroom_code, row.requester_username, row.needed_by_date, row.priority, row.line_count, row.requested_qty, row.sourced_qty, row.purpose])
            writer.writerow([])
            writer.writerow(["Purchase Orders"])
            writer.writerow(["PO Number", "Status", "Site", "Supplier", "Order Date", "Expected Delivery", "Lines", "Ordered Qty", "Received Qty", "Rejected Qty", "Open Qty", "Currency"])
            for row in report.purchase_orders:
                writer.writerow([row.po_number, row.status, row.site_code, row.supplier_code, row.order_date, row.expected_delivery_date, row.line_count, row.ordered_qty, row.received_qty, row.rejected_qty, row.open_qty, row.currency_code])
            writer.writerow([])
            writer.writerow(["Receipts"])
            writer.writerow(["Receipt", "PO Number", "Status", "Site", "Supplier", "Receipt Date", "Lines", "Accepted Qty", "Rejected Qty", "Received By"])
            for row in report.receipts:
                writer.writerow([row.receipt_number, row.purchase_order_number, row.status, row.site_code, row.supplier_code, row.receipt_date, row.line_count, row.accepted_qty, row.rejected_qty, row.received_by_username])
        return finalize_artifact(output_path, media_type="text/csv")

    def _render_procurement_overview_excel(self, request: object):
        assert isinstance(request, InventoryReportRequest)
        report = self._build_procurement_overview_report(request)
        output_path = ensure_output_path(request.output_path)
        rendered = self._excel_renderer.render_procurement_overview(report, output_path)
        return finalize_artifact(
            rendered,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def _build_stock_status_report(self, request: InventoryReportRequest) -> StockStatusReport:
        site_code = ""
        storeroom_code = ""
        allowed_storeroom_ids: set[str] | None = None
        if request.site_id:
            site = self._reference_service.get_site(request.site_id)
            site_code = site.site_code
            allowed_storeroom_ids = {
                storeroom.id
                for storeroom in self._inventory_service.list_storerooms(active_only=None, site_id=request.site_id)
            }
        if request.storeroom_id:
            storeroom = self._inventory_service.get_storeroom(request.storeroom_id)
            storeroom_code = storeroom.storeroom_code
            if request.site_id and storeroom.site_id != request.site_id:
                raise ValidationError(
                    "Selected storeroom does not belong to the selected site.",
                    code="INVENTORY_REPORT_SCOPE_MISMATCH",
                )
            allowed_storeroom_ids = {storeroom.id}
            if not site_code:
                site_code = self._reference_service.get_site(storeroom.site_id).site_code

        balances = self._stock_service.list_balances(storeroom_id=request.storeroom_id)
        if allowed_storeroom_ids is not None:
            balances = [row for row in balances if row.storeroom_id in allowed_storeroom_ids]

        items_by_id = {item.id: item for item in self._item_service.list_items(active_only=None)}
        storerooms_by_id = {
            storeroom.id: storeroom
            for storeroom in self._inventory_service.list_storerooms(active_only=None)
        }
        site_codes_by_id = {site.id: site.site_code for site in self._reference_service.list_sites(active_only=None)}
        rows = tuple(
            sorted(
                (
                    StockStatusRow(
                        item_code=items_by_id.get(balance.stock_item_id).item_code if balance.stock_item_id in items_by_id else "",
                        item_name=items_by_id.get(balance.stock_item_id).name if balance.stock_item_id in items_by_id else "",
                        storeroom_code=storerooms_by_id.get(balance.storeroom_id).storeroom_code if balance.storeroom_id in storerooms_by_id else "",
                        storeroom_name=storerooms_by_id.get(balance.storeroom_id).name if balance.storeroom_id in storerooms_by_id else "",
                        site_code=site_codes_by_id.get(storerooms_by_id.get(balance.storeroom_id).site_id, "") if balance.storeroom_id in storerooms_by_id else "",
                        uom=balance.uom,
                        on_hand_qty=float(balance.on_hand_qty or 0.0),
                        reserved_qty=float(balance.reserved_qty or 0.0),
                        available_qty=float(balance.available_qty or 0.0),
                        on_order_qty=float(balance.on_order_qty or 0.0),
                        average_cost=float(balance.average_cost or 0.0),
                        reorder_required=bool(balance.reorder_required),
                        last_receipt_at=_isoformat(balance.last_receipt_at),
                        last_issue_at=_isoformat(balance.last_issue_at),
                    )
                    for balance in balances
                ),
                key=lambda row: (row.item_code, row.storeroom_code),
            )
        )
        return StockStatusReport(
            title="Inventory Stock Status",
            filters=(
                ReportMetric("Site", site_code or "All sites"),
                ReportMetric("Storeroom", storeroom_code or "All storerooms"),
            ),
            summary=(
                ReportMetric("Balance rows", len(rows)),
                ReportMetric("Unique items", len({row.item_code for row in rows if row.item_code})),
                ReportMetric("Unique storerooms", len({row.storeroom_code for row in rows if row.storeroom_code})),
                ReportMetric("Total on hand", round(sum(row.on_hand_qty for row in rows), 2)),
                ReportMetric("Total reserved", round(sum(row.reserved_qty for row in rows), 2)),
                ReportMetric("Total available", round(sum(row.available_qty for row in rows), 2)),
                ReportMetric("Total on order", round(sum(row.on_order_qty for row in rows), 2)),
                ReportMetric("Reorder alerts", sum(1 for row in rows if row.reorder_required)),
            ),
            rows=rows,
        )

    def _build_procurement_overview_report(self, request: InventoryReportRequest) -> ProcurementOverviewReport:
        site_code = "All sites"
        if request.site_id:
            site_code = self._reference_service.get_site(request.site_id).site_code
        supplier_code = "All suppliers"
        if request.supplier_party_id:
            supplier_code = self._reference_service.get_party(request.supplier_party_id).party_code

        requisitions = self._procurement_service.list_requisitions(
            site_id=request.site_id,
            storeroom_id=request.storeroom_id,
            limit=request.limit,
        )
        purchase_orders = self._purchasing_service.list_purchase_orders(
            site_id=request.site_id,
            supplier_party_id=request.supplier_party_id,
            limit=request.limit,
        )
        receipts = self._purchasing_service.list_receipts(
            purchase_order_id=request.purchase_order_id,
            limit=request.limit,
        )
        site_codes_by_id = {site.id: site.site_code for site in self._reference_service.list_sites(active_only=None)}
        storerooms_by_id = {
            storeroom.id: storeroom.storeroom_code
            for storeroom in self._inventory_service.list_storerooms(active_only=None)
        }
        suppliers_by_id = {
            party.id: party.party_code
            for party in self._reference_service.list_business_parties(active_only=None)
        }
        purchase_orders_by_id = {purchase_order.id: purchase_order for purchase_order in purchase_orders}

        requisition_rows = []
        for requisition in requisitions:
            lines = self._procurement_service.list_requisition_lines(requisition.id)
            requisition_rows.append(
                RequisitionOverviewRow(
                    requisition_number=requisition.requisition_number,
                    status=_enum_value(requisition.status),
                    site_code=site_codes_by_id.get(requisition.requesting_site_id, ""),
                    storeroom_code=storerooms_by_id.get(requisition.requesting_storeroom_id, ""),
                    requester_username=requisition.requester_username,
                    needed_by_date=_isoformat(requisition.needed_by_date),
                    priority=requisition.priority,
                    line_count=len(lines),
                    requested_qty=round(sum(float(line.quantity_requested or 0.0) for line in lines), 2),
                    sourced_qty=round(sum(float(line.quantity_sourced or 0.0) for line in lines), 2),
                    purpose=requisition.purpose,
                )
            )

        purchase_order_rows = []
        for purchase_order in purchase_orders:
            lines = self._purchasing_service.list_purchase_order_lines(purchase_order.id)
            purchase_order_rows.append(
                PurchaseOrderOverviewRow(
                    po_number=purchase_order.po_number,
                    status=_enum_value(purchase_order.status),
                    site_code=site_codes_by_id.get(purchase_order.site_id, ""),
                    supplier_code=suppliers_by_id.get(purchase_order.supplier_party_id, ""),
                    order_date=_isoformat(purchase_order.order_date),
                    expected_delivery_date=_isoformat(purchase_order.expected_delivery_date),
                    line_count=len(lines),
                    ordered_qty=round(sum(float(line.quantity_ordered or 0.0) for line in lines), 2),
                    received_qty=round(sum(float(line.quantity_received or 0.0) for line in lines), 2),
                    rejected_qty=round(sum(float(line.quantity_rejected or 0.0) for line in lines), 2),
                    open_qty=round(sum(max(0.0, float(line.quantity_ordered or 0.0) - float(line.quantity_received or 0.0) - float(line.quantity_rejected or 0.0)) for line in lines), 2),
                    currency_code=purchase_order.currency_code,
                )
            )

        receipt_rows = []
        for receipt in receipts:
            lines = self._purchasing_service.list_receipt_lines(receipt.id)
            purchase_order = purchase_orders_by_id.get(receipt.purchase_order_id) or self._purchasing_service.get_purchase_order(receipt.purchase_order_id)
            receipt_rows.append(
                ReceiptOverviewRow(
                    receipt_number=receipt.receipt_number,
                    purchase_order_number=purchase_order.po_number,
                    status=_enum_value(receipt.status),
                    site_code=site_codes_by_id.get(receipt.received_site_id, ""),
                    supplier_code=suppliers_by_id.get(receipt.supplier_party_id, ""),
                    receipt_date=_isoformat(receipt.receipt_date),
                    line_count=len(lines),
                    accepted_qty=round(sum(float(line.quantity_accepted or 0.0) for line in lines), 2),
                    rejected_qty=round(sum(float(line.quantity_rejected or 0.0) for line in lines), 2),
                    received_by_username=receipt.received_by_username,
                )
            )

        requisition_rows_tuple = tuple(sorted(requisition_rows, key=lambda row: row.requisition_number))
        purchase_order_rows_tuple = tuple(sorted(purchase_order_rows, key=lambda row: row.po_number))
        receipt_rows_tuple = tuple(sorted(receipt_rows, key=lambda row: row.receipt_number))
        return ProcurementOverviewReport(
            title="Inventory Procurement Overview",
            filters=(
                ReportMetric("Site", site_code),
                ReportMetric("Supplier", supplier_code),
                ReportMetric("Limit", int(request.limit or 200)),
            ),
            summary=(
                ReportMetric("Requisitions", len(requisition_rows_tuple)),
                ReportMetric("Purchase orders", len(purchase_order_rows_tuple)),
                ReportMetric("Receipts", len(receipt_rows_tuple)),
                ReportMetric("Requested quantity", round(sum(row.requested_qty for row in requisition_rows_tuple), 2)),
                ReportMetric("Sourced quantity", round(sum(row.sourced_qty for row in requisition_rows_tuple), 2)),
                ReportMetric("Ordered quantity", round(sum(row.ordered_qty for row in purchase_order_rows_tuple), 2)),
                ReportMetric("Received quantity", round(sum(row.received_qty for row in purchase_order_rows_tuple), 2)),
                ReportMetric("Open purchase quantity", round(sum(row.open_qty for row in purchase_order_rows_tuple), 2)),
                ReportMetric("Accepted receipt quantity", round(sum(row.accepted_qty for row in receipt_rows_tuple), 2)),
            ),
            requisitions=requisition_rows_tuple,
            purchase_orders=purchase_order_rows_tuple,
            receipts=receipt_rows_tuple,
        )


__all__ = ["InventoryReportRequest", "InventoryReportingService"]
