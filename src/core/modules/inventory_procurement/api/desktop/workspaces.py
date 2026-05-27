from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InventoryProcurementWorkspaceDescriptor:
    key: str
    title: str
    summary: str


_WORKSPACE_DESCRIPTORS: tuple[InventoryProcurementWorkspaceDescriptor, ...] = (
    InventoryProcurementWorkspaceDescriptor(
        key="dashboard",
        title="Dashboard",
        summary="Inventory KPIs, low-stock watchlists, procurement queues, and receiving pressure.",
    ),
    InventoryProcurementWorkspaceDescriptor(
        key="catalog",
        title="Catalog",
        summary="Item categories, stocked items, preferred suppliers, and linked-document workflows.",
    ),
    InventoryProcurementWorkspaceDescriptor(
        key="inventory",
        title="Inventory",
        summary="Storerooms, stock balances, adjustments, issues, returns, and transfer movements.",
    ),
    InventoryProcurementWorkspaceDescriptor(
        key="reservations",
        title="Reservations",
        summary="Reservation holds, issuing, release flows, and source-reference stock demand.",
    ),
    InventoryProcurementWorkspaceDescriptor(
        key="procurement",
        title="Procurement",
        summary="Requisitions, purchase orders, receiving, and supplier-facing fulfillment workflows.",
    ),
    InventoryProcurementWorkspaceDescriptor(
        key="pricing",
        title="Pricing",
        summary="Supplier pricing analysis plus stock and procurement report exports.",
    ),
    InventoryProcurementWorkspaceDescriptor(
        key="movements",
        title="Stock Movements",
        summary="Full audit trail of opening balances, adjustments, issues, returns, and transfers.",
    ),
    InventoryProcurementWorkspaceDescriptor(
        key="warehouses",
        title="Warehouses & Locations",
        summary="Storerooms, storage zones, bins, and sub-locations across all sites.",
    ),
)


class InventoryProcurementWorkspaceDesktopApi:
    def __init__(
        self,
        descriptors: tuple[
            InventoryProcurementWorkspaceDescriptor, ...
        ] = _WORKSPACE_DESCRIPTORS,
    ) -> None:
        self._descriptors = descriptors
        self._descriptor_by_route_id = {
            f"inventory_procurement.{descriptor.key}": descriptor
            for descriptor in descriptors
        }

    def list_workspaces(self) -> list[InventoryProcurementWorkspaceDescriptor]:
        return list(self._descriptors)

    def get_workspace(
        self,
        route_id: str,
    ) -> InventoryProcurementWorkspaceDescriptor | None:
        return self._descriptor_by_route_id.get(route_id)


def build_inventory_procurement_workspace_desktop_api() -> (
    InventoryProcurementWorkspaceDesktopApi
):
    return InventoryProcurementWorkspaceDesktopApi()


__all__ = [
    "InventoryProcurementWorkspaceDescriptor",
    "InventoryProcurementWorkspaceDesktopApi",
    "build_inventory_procurement_workspace_desktop_api",
]
