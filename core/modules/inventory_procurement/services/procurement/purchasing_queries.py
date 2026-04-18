from __future__ import annotations

from core.modules.inventory_procurement.domain import PurchaseOrder, PurchaseOrderLine, ReceiptHeader, ReceiptLine
from core.modules.inventory_procurement.support import normalize_optional_text
from src.core.platform.common.exceptions import NotFoundError


class PurchasingQueryMixin:
    def list_purchase_orders(
        self,
        *,
        status: str | None = None,
        site_id: str | None = None,
        supplier_party_id: str | None = None,
        limit: int = 200,
    ) -> list[PurchaseOrder]:
        self._require_read("list purchase orders")
        organization = self._active_organization()
        return self._purchase_order_repo.list_for_organization(
            organization.id,
            status=normalize_optional_text(status).upper() or None,
            site_id=normalize_optional_text(site_id) or None,
            supplier_party_id=normalize_optional_text(supplier_party_id) or None,
            limit=max(1, int(limit or 200)),
        )

    def get_purchase_order(self, purchase_order_id: str) -> PurchaseOrder:
        self._require_read("view purchase order")
        organization = self._active_organization()
        purchase_order = self._purchase_order_repo.get(purchase_order_id)
        if purchase_order is None or purchase_order.organization_id != organization.id:
            raise NotFoundError(
                "Purchase order not found in the active organization.",
                code="INVENTORY_PURCHASE_ORDER_NOT_FOUND",
            )
        return purchase_order

    def find_purchase_order_by_number(self, po_number: str) -> PurchaseOrder | None:
        self._require_read("resolve purchase order")
        organization = self._active_organization()
        normalized_number = normalize_optional_text(po_number)
        if not normalized_number:
            return None
        return self._purchase_order_repo.get_by_number(organization.id, normalized_number)

    def list_purchase_order_lines(self, purchase_order_id: str) -> list[PurchaseOrderLine]:
        purchase_order = self.get_purchase_order(purchase_order_id)
        return self._purchase_order_line_repo.list_for_purchase_order(purchase_order.id)

    def list_receipts(
        self,
        *,
        purchase_order_id: str | None = None,
        limit: int = 200,
    ) -> list[ReceiptHeader]:
        self._require_read("list receipts")
        organization = self._active_organization()
        return self._receipt_header_repo.list_for_organization(
            organization.id,
            purchase_order_id=normalize_optional_text(purchase_order_id) or None,
            limit=max(1, int(limit or 200)),
        )

    def get_receipt(self, receipt_id: str) -> ReceiptHeader:
        self._require_read("view receipt")
        organization = self._active_organization()
        receipt = self._receipt_header_repo.get(receipt_id)
        if receipt is None or receipt.organization_id != organization.id:
            raise NotFoundError("Receipt not found in the active organization.", code="INVENTORY_RECEIPT_NOT_FOUND")
        return receipt

    def find_receipt_by_number(self, receipt_number: str) -> ReceiptHeader | None:
        self._require_read("resolve receipt")
        organization = self._active_organization()
        normalized_number = normalize_optional_text(receipt_number)
        if not normalized_number:
            return None
        return self._receipt_header_repo.get_by_number(organization.id, normalized_number)

    def list_receipt_lines(self, receipt_id: str) -> list[ReceiptLine]:
        receipt = self.get_receipt(receipt_id)
        return self._receipt_line_repo.list_for_receipt(receipt.id)


__all__ = ["PurchasingQueryMixin"]
