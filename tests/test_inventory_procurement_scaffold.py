from __future__ import annotations

from core.platform.party.domain import PartyType
from tests.ui_runtime_helpers import login_as


def test_inventory_manager_can_consume_shared_sites_and_business_parties(services):
    auth = services["auth_service"]
    site = services["site_service"].create_site(site_code="HAM", name="Hamburg Warehouse", city="Hamburg")
    supplier = services["party_service"].create_party(
        party_code="SUP-001",
        party_name="North Supply",
        party_type=PartyType.SUPPLIER,
        city="Hamburg",
    )
    services["party_service"].create_party(
        party_code="GEN-001",
        party_name="General Directory Entry",
        party_type=PartyType.GENERAL,
        city="Berlin",
    )
    auth.register_user("inventory-manager", "StrongPass123", role_names=["inventory_manager"])

    login_as(services, "inventory-manager", "StrongPass123")

    inventory_refs = services["inventory_reference_service"]
    sites = inventory_refs.search_sites(search_text="warehouse")
    parties = inventory_refs.search_business_parties(search_text="north")

    assert [row.id for row in sites] == [site.id]
    assert [row.id for row in parties] == [supplier.id]
    assert inventory_refs.get_site(site.id).name == "Hamburg Warehouse"
    assert inventory_refs.get_party(supplier.id).party_type == PartyType.SUPPLIER


def test_inventory_manager_role_exposes_inventory_shared_reference_permissions(services):
    auth = services["auth_service"]
    user = auth.register_user("inventory-role-check", "StrongPass123", role_names=["inventory_manager"])

    permissions = auth.get_user_permissions(user.id)

    assert "inventory.read" in permissions
    assert "inventory.manage" in permissions
    assert "site.read" in permissions
    assert "party.read" in permissions
    assert "approval.request" in permissions
    assert "settings.manage" not in permissions
