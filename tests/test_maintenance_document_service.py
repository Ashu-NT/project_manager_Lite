from __future__ import annotations


def _create_document_context(services):
    site = services["site_service"].create_site(
        site_code="MDOC",
        name="Maintenance Documents Site",
        currency_code="EUR",
    )
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="loc-doc",
        name="Document Area",
    )
    system = services["maintenance_system_service"].create_system(
        site_id=site.id,
        location_id=location.id,
        system_code="sys-doc",
        name="Document System",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        system_id=system.id,
        asset_code="asset-doc",
        name="Document Asset",
    )
    request = services["maintenance_work_request_service"].create_work_request(
        site_id=site.id,
        work_request_code="wr-doc",
        source_type="manual",
        request_type="inspection",
        asset_id=asset.id,
        location_id=location.id,
        system_id=system.id,
        title="Document-linked request",
    )
    work_order = services["maintenance_work_order_service"].create_work_order(
        site_id=site.id,
        work_order_code="wo-doc",
        work_order_type="inspection",
        source_type="work_request",
        source_id=request.id,
    )
    document = services["document_service"].create_document(
        document_code="DOC-MNT-001",
        title="Pump Inspection Manual",
        document_type="MANUAL",
        storage_kind="FILE_PATH",
        storage_uri="C:/docs/pump-inspection-manual.pdf",
    )
    return site, asset, request, work_order, document


def test_maintenance_document_service_links_and_lists_documents(services):
    site, asset, _request, work_order, document = _create_document_context(services)
    service = services["maintenance_document_service"]

    asset_link = service.link_existing_document(
        entity_type="asset",
        entity_id=asset.id,
        document_id=document.id,
        link_role="reference",
    )
    service.link_existing_document(
        entity_type="work_order",
        entity_id=work_order.id,
        document_id=document.id,
        link_role="attachment",
    )

    rows = service.list_document_records(site_id=site.id)
    assert len(rows) == 2
    assert {row.entity_type for row in rows} == {"asset", "work_order"}
    assert any("ASSET-DOC - Document Asset" == row.entity_label for row in rows)
    assert any("WO-DOC" in row.entity_label for row in rows)
    assert {row.document.document_code for row in rows} == {"DOC-MNT-001"}

    linked_docs = service.list_documents_for_entity(entity_type="asset", entity_id=asset.id)
    assert [row.document_code for row in linked_docs] == ["DOC-MNT-001"]

    links = service.list_links_for_document(document.id)
    assert len(links) == 2
    assert {row.id for row in links} >= {asset_link.id}


def test_maintenance_document_service_lists_entity_choices(services):
    site, asset, request, work_order, _document = _create_document_context(services)
    service = services["maintenance_document_service"]

    asset_choices = service.list_entity_choices(entity_type="asset", site_id=site.id)
    request_choices = service.list_entity_choices(entity_type="work_request", site_id=site.id)
    work_order_choices = service.list_entity_choices(entity_type="work_order", site_id=site.id)

    assert (asset.id, "ASSET-DOC - Document Asset") in asset_choices
    assert any(choice_id == request.id and "WR-DOC" in label for choice_id, label in request_choices)
    assert any(choice_id == work_order.id and "WO-DOC" in label for choice_id, label in work_order_choices)
