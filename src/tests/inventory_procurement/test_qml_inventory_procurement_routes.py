from src.ui_qml.modules.inventory_procurement.routes import (
    build_inventory_procurement_routes,
)
from src.ui_qml.shell.qml_registry import build_qml_route_registry


EXPECTED_INVENTORY_ROUTE_IDS = [
    "inventory_procurement.dashboard",
    "inventory_procurement.catalog",
    "inventory_procurement.inventory",
    "inventory_procurement.reservations",
    "inventory_procurement.procurement",
    "inventory_procurement.pricing",
    "inventory_procurement.movements",
    "inventory_procurement.warehouses",
]


def test_inventory_procurement_qml_routes_point_to_workspace_files() -> None:
    routes = build_inventory_procurement_routes()

    assert [route.route_id for route in routes] == EXPECTED_INVENTORY_ROUTE_IDS
    assert all(route.module_code == "inventory_procurement" for route in routes)
    assert all(route.module_label == "Inventory & Procurement" for route in routes)
    assert all(route.qml_path.exists() for route in routes)


def test_inventory_procurement_qml_routes_are_registered_for_navigation() -> None:
    registry = build_qml_route_registry()
    route_ids = [route.route_id for route in registry.list_navigation_routes()]

    for route_id in EXPECTED_INVENTORY_ROUTE_IDS:
        assert route_id in route_ids

