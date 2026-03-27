from __future__ import annotations

import pytest

from core.platform.common.exceptions import NotFoundError, ValidationError
from core.platform.party.domain import PartyType
from tests.ui_runtime_helpers import login_as


def test_inventory_manager_can_create_items_with_shared_party_and_document_links(services):
    auth = services["auth_service"]
    supplier = services["party_service"].create_party(
        party_code="SUP-100",
        party_name="North Supply",
        party_type=PartyType.SUPPLIER,
    )
    document = services["document_service"].create_document(
        document_code="DOC-INV-100",
        title="Bearing Manual",
        document_type="MANUAL",
        storage_kind="REFERENCE",
        storage_uri="vault://manuals/bearing",
    )
    auth.register_user("inventory-item-user", "StrongPass123", role_names=["inventory_manager"])

    login_as(services, "inventory-item-user", "StrongPass123")

    item_service = services["inventory_item_service"]
    item = item_service.create_item(
        item_code="BRG-100",
        name="Bearing 100",
        status="ACTIVE",
        stock_uom="EA",
        preferred_party_id=supplier.id,
        reorder_point=4,
        reorder_qty=10,
        max_qty=20,
    )
    link = item_service.link_document(item.id, document_id=document.id, link_role="manual")
    linked_documents = item_service.list_linked_documents(item.id, active_only=True)

    assert item.is_active is True
    assert item.preferred_party_id == supplier.id
    assert item_service.find_item_by_code("BRG-100").id == item.id
    assert link.document_id == document.id
    assert [row.id for row in linked_documents] == [document.id]


def test_inventory_item_document_library_can_list_and_unlink_shared_documents(services):
    auth = services["auth_service"]
    auth.register_user("inventory-item-doc-user", "StrongPass123", role_names=["inventory_manager"])
    first_document = services["document_service"].create_document(
        document_code="DOC-INV-201",
        title="Pump Manual",
        document_type="MANUAL",
        storage_kind="REFERENCE",
        storage_uri="vault://manuals/pump-manual",
    )
    second_document = services["document_service"].create_document(
        document_code="DOC-INV-202",
        title="Pump Datasheet",
        document_type="DATASHEET",
        storage_kind="REFERENCE",
        storage_uri="vault://manuals/pump-datasheet",
    )

    login_as(services, "inventory-item-doc-user", "StrongPass123")

    item_service = services["inventory_item_service"]
    item = item_service.create_item(
        item_code="PUMP-201",
        name="Pump 201",
        status="ACTIVE",
        stock_uom="EA",
    )
    available_before = item_service.list_available_documents(active_only=True)
    item_service.link_document(item.id, document_id=first_document.id, link_role="manual")
    linked_documents = item_service.list_linked_documents(item.id, active_only=True)
    item_service.unlink_document(item.id, document_id=first_document.id, link_role="manual")
    available_after = item_service.list_available_documents(active_only=True)

    assert {row.id for row in available_before} == {first_document.id, second_document.id}
    assert [row.id for row in linked_documents] == [first_document.id]
    assert item_service.list_linked_documents(item.id, active_only=True) == []
    assert {row.id for row in available_after} == {first_document.id, second_document.id}


def test_inventory_manager_can_create_storerooms_under_shared_sites(services):
    auth = services["auth_service"]
    site = services["site_service"].create_site(
        site_code="HAM",
        name="Hamburg Warehouse",
        city="Hamburg",
        currency_code="EUR",
    )
    contractor = services["party_service"].create_party(
        party_code="CTR-001",
        party_name="Managed Stores GmbH",
        party_type=PartyType.CONTRACTOR,
    )
    auth.register_user("inventory-store-user", "StrongPass123", role_names=["inventory_manager"])

    login_as(services, "inventory-store-user", "StrongPass123")

    inventory_service = services["inventory_service"]
    storeroom = inventory_service.create_storeroom(
        storeroom_code="HAM-MAIN",
        name="Hamburg Main Storeroom",
        site_id=site.id,
        status="ACTIVE",
        storeroom_type="MAIN",
        manager_party_id=contractor.id,
    )

    assert storeroom.is_active is True
    assert storeroom.default_currency_code == "EUR"
    assert inventory_service.find_storeroom_by_code("HAM-MAIN").id == storeroom.id
    assert [row.id for row in inventory_service.search_storerooms(search_text="main")] == [storeroom.id]


def test_inventory_foundation_rejects_out_of_scope_shared_references(services):
    auth = services["auth_service"]
    organization_service = services["organization_service"]
    default_org = organization_service.get_active_organization()
    other_org = organization_service.create_organization(
        organization_code="INV-OPS",
        display_name="Inventory Operations",
        timezone_name="Europe/Berlin",
        base_currency="EUR",
        is_active=False,
    )

    organization_service.set_active_organization(other_org.id)
    foreign_site = services["site_service"].create_site(site_code="EXT", name="External Site")
    foreign_party = services["party_service"].create_party(
        party_code="SUP-EXT",
        party_name="External Supply",
        party_type=PartyType.SUPPLIER,
    )
    organization_service.set_active_organization(default_org.id)

    auth.register_user("inventory-scope-user", "StrongPass123", role_names=["inventory_manager"])
    login_as(services, "inventory-scope-user", "StrongPass123")

    with pytest.raises(NotFoundError, match="Site not found"):
        services["inventory_service"].create_storeroom(
            storeroom_code="BAD-SITE",
            name="Bad Site Storeroom",
            site_id=foreign_site.id,
        )
    with pytest.raises(NotFoundError, match="Party not found"):
        services["inventory_item_service"].create_item(
            item_code="BAD-PARTY",
            name="Bad Party Item",
            stock_uom="EA",
            preferred_party_id=foreign_party.id,
        )


def test_inventory_item_service_enforces_status_and_reorder_rules(services):
    item_service = services["inventory_item_service"]
    item = item_service.create_item(
        item_code="VALVE-001",
        name="Control Valve",
        stock_uom="EA",
        max_qty=15,
        reorder_point=5,
    )

    activated = item_service.update_item(item.id, status="ACTIVE", expected_version=item.version)
    assert activated.status == "ACTIVE"
    assert activated.is_active is True

    deactivated = item_service.update_item(activated.id, is_active=False, expected_version=activated.version)
    assert deactivated.status == "INACTIVE"
    assert deactivated.is_active is False

    with pytest.raises(ValidationError, match="Maximum quantity cannot be less than minimum quantity"):
        item_service.create_item(
            item_code="VALVE-002",
            name="Control Valve 2",
            stock_uom="EA",
            min_qty=10,
            max_qty=2,
        )


def test_inventory_item_service_requires_conversion_factors_for_alternate_uoms(services):
    item_service = services["inventory_item_service"]

    with pytest.raises(ValidationError, match="Order UOM factor"):
        item_service.create_item(
            item_code="VALVE-ALT",
            name="Alternate Valve",
            stock_uom="EA",
            order_uom="BOX",
        )
